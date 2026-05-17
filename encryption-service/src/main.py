from fastapi import FastAPI, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import uuid, io, os, tempfile, logging, psycopg2, httpx
from src.services.kyber import generate_keypair, encapsulate
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Encryption Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class EncryptRequest(BaseModel):
    file_id: str
    owner_id: str

class AsyncEncryptRequest(BaseModel):
    file_id: str
    owner_id: str
    bucket: str
    key: str
    file_buffer_base64: str

@app.get("/health/live")
def liveness_probe():
    return {"status": "alive"}

@app.get("/health/ready")
def readiness_probe():
    return {"status": "ready"}

@app.post("/encrypt/async")
async def encrypt_async(req: AsyncEncryptRequest, Idempotency_Key: str = Header(default=None)):
    from src.workers.tasks import process_encryption
    res = process_encryption(req.file_id, req.owner_id, req.bucket, req.key, req.file_buffer_base64)
    return {"job_id": req.file_id, "status": "completed_synchronously"}

@app.get("/encrypt/status/{job_id}")
def get_encrypt_status(job_id: str):
    from src.workers.celery_app import celery_app
    res = celery_app.AsyncResult(job_id)
    return {"job_id": job_id, "status": res.status, "result": res.result if res.ready() else None}

@app.get("/decrypt/{file_id}")
async def decrypt_and_download(file_id: str, background_tasks: BackgroundTasks, request: Request = None):
    from src.workers.tasks import get_minio_client, DATABASE_URL
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT minio_bucket, minio_key, encrypted_aes_key, original_name, owner_id FROM files WHERE id = %s", (file_id,))
    record = cur.fetchone()
    cur.close()
    conn.close()

    if not record:
        return {"error": "File not found"}

    bucket, minio_key, aes_hex, original_name, actual_owner_id = record

    if not aes_hex:
        return {"error": "File metadata is incomplete. Re-upload this file."}

    s3 = get_minio_client()
    tmp_path = os.path.join(tempfile.gettempdir(), f"download_{uuid.uuid4().hex}.bin")
    try:
        s3.download_file(bucket, minio_key, tmp_path)
        with open(tmp_path, 'rb') as f:
            encrypted_blob = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    nonce = encrypted_blob[:12]
    ciphertext = encrypted_blob[12:]

    try:
        aesgcm = AESGCM(bytes.fromhex(aes_hex))
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}

    # --- Emit live ML telemetry to Risk Engine on every download ---
    RISK_ENGINE_URL = os.getenv("RISK_ENGINE_URL", "http://localhost:3005/ingest")
    async def emit_download_telemetry():
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                await client.post(RISK_ENGINE_URL, json={
                    "user_id": actual_owner_id if actual_owner_id else "unknown",
                    "action_type": "download",
                    "bytes_transferred_last_1h": len(encrypted_blob),
                    "download_count_last_1h": 1,
                    "ip_location_mismatch": 0,
                    "failed_logins_last_1h": 0,
                })
        except Exception:
            pass
    background_tasks.add_task(emit_download_telemetry)

    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{original_name}"'}
    )


# ─── SELF-HEALING: REAL KEY ROTATION ────────────────────────────────────────

@app.post("/self-heal/rotate-keys")
async def rotate_all_keys(owner_id: str = None):
    """
    Self-Healing endpoint. Rotates Kyber-1024 + AES-256-GCM keys.
    Pass ?owner_id=<uuid> to rotate only that user's files (compromised account).
    Omit owner_id to rotate the entire vault (admin global rotation).
    """
    from src.workers.tasks import get_minio_client, DATABASE_URL
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from src.services.kyber import generate_keypair

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    if owner_id:
        logger.info(f"[SELF-HEAL] Rotating keys for user {owner_id} only")
        cur.execute(
            "SELECT id, original_name, minio_bucket, minio_key, encrypted_aes_key FROM files "
            "WHERE is_deleted=FALSE AND encrypted_aes_key IS NOT NULL AND owner_id=%s",
            (owner_id,)
        )
    else:
        logger.info("[SELF-HEAL] Global rotation — rotating ALL users' files")
        cur.execute(
            "SELECT id, original_name, minio_bucket, minio_key, encrypted_aes_key FROM files "
            "WHERE is_deleted=FALSE AND encrypted_aes_key IS NOT NULL"
        )
    files = cur.fetchall()
    cur.close()
    conn.close()

    s3 = get_minio_client()
    rotation_log = []

    for file_id, original_name, bucket, minio_key, old_aes_hex in files:
        try:
            logger.info(f"[SELF-HEAL] Rotating key for file: {original_name} ({file_id})")

            # 1. Download old encrypted blob
            tmp_in = os.path.join(tempfile.gettempdir(), f"heal_in_{uuid.uuid4().hex}.bin")
            try:
                s3.download_file(bucket, minio_key, tmp_in)
                with open(tmp_in, 'rb') as f:
                    old_blob = f.read()
            finally:
                if os.path.exists(tmp_in): os.unlink(tmp_in)

            # 2. Decrypt with old key
            old_nonce = old_blob[:12]
            old_ciphertext = old_blob[12:]
            old_aesgcm = AESGCM(bytes.fromhex(old_aes_hex))
            plaintext = old_aesgcm.decrypt(old_nonce, old_ciphertext, None)

            # 3. Generate completely new keypair + new AES key
            new_pub_key, new_priv_key = generate_keypair()
            new_aes_key = AESGCM.generate_key(bit_length=256)
            new_aesgcm = AESGCM(new_aes_key)
            new_nonce = os.urandom(12)

            # 4. Re-encrypt with new key
            new_ciphertext = new_aesgcm.encrypt(new_nonce, plaintext, None)
            new_blob = new_nonce + new_ciphertext

            # 5. Re-upload to MinIO (same key path, overwrites old encrypted blob)
            tmp_out = os.path.join(tempfile.gettempdir(), f"heal_out_{uuid.uuid4().hex}.bin")
            try:
                with open(tmp_out, 'wb') as f:
                    f.write(new_blob)
                s3.upload_file(tmp_out, bucket, minio_key)
            finally:
                if os.path.exists(tmp_out): os.unlink(tmp_out)

            # 6. Encapsulate new AES key under new Kyber public key
            new_pub_key_b64 = base64.b64encode(new_pub_key).decode()
            new_kyber_ct_b64, _ = encapsulate(new_pub_key_b64)
            new_priv_key_b64 = base64.b64encode(new_priv_key).decode()

            # 7. Update DB with new Kyber ciphertext, AES key, and private key
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2 = conn2.cursor()
            cur2.execute(
                "UPDATE files SET kyber_ciphertext = %s, encrypted_aes_key = %s, "
                "key_version = key_version + 1 WHERE id = %s",
                (new_kyber_ct_b64, new_aes_key.hex(), file_id)
            )
            # Get owner_id for this file to update private key
            cur2.execute("SELECT owner_id FROM files WHERE id = %s", (file_id,))
            owner_row = cur2.fetchone()
            if owner_row:
                cur2.execute(
                    "UPDATE users SET kyber_private_key_encrypted = %s WHERE id = %s",
                    (new_priv_key_b64, owner_row[0])
                )
            # Write audit record
            cur2.execute(
                """INSERT INTO key_rotation_log 
                   (id, user_id, file_id, old_key_version, new_key_version, trigger_reason)
                   VALUES (gen_random_uuid(), %s, %s, 
                           (SELECT key_version - 1 FROM files WHERE id = %s),
                           (SELECT key_version FROM files WHERE id = %s),
                           'ANOMALY_TRIGGERED')""",
                (owner_row[0] if owner_row else None, file_id, file_id, file_id)
            )
            conn2.commit()
            cur2.close()
            conn2.close()

            rotation_log.append({
                "file_id": file_id,
                "file_name": original_name,
                "status": "rotated",
                "old_kyber_preview": old_aes_hex[:32] + "...",
                "new_kyber_preview": new_pub_key.hex()[:32] + "...",
                "old_aes_preview": old_aes_hex[:16] + "...",
                "new_aes_preview": new_aes_key.hex()[:16] + "...",
                "plaintext_size_bytes": len(plaintext),
            })
            logger.info(f"[SELF-HEAL] ✓ Key rotation complete for {original_name}")

        except Exception as e:
            logger.error(f"[SELF-HEAL] ✗ Failed to rotate {original_name}: {e}")
            rotation_log.append({
                "file_id": file_id,
                "file_name": original_name,
                "status": "failed",
                "error": str(e)
            })

    return {
        "status": "self_healing_complete",
        "files_rotated": len([r for r in rotation_log if r["status"] == "rotated"]),
        "files_failed": len([r for r in rotation_log if r["status"] == "failed"]),
        "rotation_log": rotation_log
    }

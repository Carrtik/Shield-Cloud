from fastapi import FastAPI, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import uuid, io, os, tempfile, logging, psycopg2, httpx
from src.services.kyber import generate_keypair, encapsulate_to_aes_key, decapsulate_to_aes_key
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

    # ── Fetch file record ────────────────────────────────────────────────────
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute(
        "SELECT minio_bucket, minio_key, kyber_ciphertext, original_name, owner_id "
        "FROM files WHERE id = %s",
        (file_id,)
    )
    record = cur.fetchone()
    cur.close()
    conn.close()

    if not record:
        return {"error": "File not found"}

    bucket, minio_key, kyber_ciphertext_b64, original_name, actual_owner_id = record

    if not kyber_ciphertext_b64:
        return {"error": "File metadata is incomplete. Re-upload this file."}

    # ── Fetch private key from users table ───────────────────────────────────
    conn2 = psycopg2.connect(DATABASE_URL)
    cur2  = conn2.cursor()
    cur2.execute(
        "SELECT kyber_private_key_encrypted FROM users WHERE id = %s",
        (actual_owner_id,)
    )
    key_row = cur2.fetchone()
    cur2.close()
    conn2.close()

    if not key_row or not key_row[0]:
        return {"error": "Private key not found. Re-upload this file."}

    priv_key = base64.b64decode(key_row[0])

    # ── Recover AES key via Kyber decapsulation — key never read from DB ─────
    try:
        aes_key = decapsulate_to_aes_key(priv_key, kyber_ciphertext_b64)
    except Exception as e:
        return {"error": f"Kyber decapsulation failed: {str(e)}"}

    # ── Download encrypted blob from MinIO ───────────────────────────────────
    s3 = get_minio_client()
    tmp_path = os.path.join(tempfile.gettempdir(), f"download_{uuid.uuid4().hex}.bin")
    try:
        s3.download_file(bucket, minio_key, tmp_path)
        with open(tmp_path, 'rb') as f:
            encrypted_blob = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # ── Decrypt with Kyber-derived AES key ───────────────────────────────────
    nonce      = encrypted_blob[:12]
    ciphertext = encrypted_blob[12:]
    try:
        aesgcm         = AESGCM(aes_key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}

    # ── Emit live ML telemetry to Risk Engine on every download ──────────────
    RISK_ENGINE_URL = os.getenv("RISK_ENGINE_URL", "http://localhost:3005/ingest")
    async def emit_download_telemetry():
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                await client.post(RISK_ENGINE_URL, json={
                    "user_id":                  actual_owner_id if actual_owner_id else "unknown",
                    "action_type":              "download",
                    "bytes_transferred_last_1h": len(encrypted_blob),
                    "download_count_last_1h":   1,
                    "ip_location_mismatch":     0,
                    "failed_logins_last_1h":    0,
                })
        except Exception:
            pass
    background_tasks.add_task(emit_download_telemetry)

    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{original_name}"'}
    )


# ─── SELF-HEALING: REAL KEY ROTATION ─────────────────────────────────────────

@app.post("/self-heal/rotate-keys")
async def rotate_all_keys(owner_id: str = None):
    """
    Self-Healing endpoint. Rotates Kyber-1024 + AES-256-GCM keys.
    The AES key is derived from the new Kyber shared secret and is
    never written to the database at any point.
    Pass ?owner_id=<uuid> to rotate only that user's files.
    Omit owner_id for admin global rotation.
    """
    from src.workers.tasks import get_minio_client, DATABASE_URL
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    if owner_id:
        logger.info(f"[SELF-HEAL] Rotating keys for user {owner_id} only")
        cur.execute(
            "SELECT f.id, f.original_name, f.minio_bucket, f.minio_key, "
            "f.kyber_ciphertext, f.owner_id "
            "FROM files f "
            "WHERE f.is_deleted=FALSE AND f.kyber_ciphertext IS NOT NULL "
            "AND f.owner_id=%s",
            (owner_id,)
        )
    else:
        logger.info("[SELF-HEAL] Global rotation — rotating ALL users' files")
        cur.execute(
            "SELECT f.id, f.original_name, f.minio_bucket, f.minio_key, "
            "f.kyber_ciphertext, f.owner_id "
            "FROM files f "
            "WHERE f.is_deleted=FALSE AND f.kyber_ciphertext IS NOT NULL"
        )

    files = cur.fetchall()
    cur.close()
    conn.close()

    s3           = get_minio_client()
    rotation_log = []

    for file_id, original_name, bucket, minio_key, old_kyber_ct_b64, file_owner_id in files:
        try:
            logger.info(f"[SELF-HEAL] Rotating key for file: {original_name} ({file_id})")

            # ── Fetch old private key from users table ───────────────────────
            conn_k  = psycopg2.connect(DATABASE_URL)
            cur_k   = conn_k.cursor()
            cur_k.execute(
                "SELECT kyber_private_key_encrypted FROM users WHERE id = %s",
                (file_owner_id,)
            )
            old_key_row = cur_k.fetchone()
            cur_k.close()
            conn_k.close()

            if not old_key_row or not old_key_row[0]:
                raise ValueError("Old private key not found in users table")

            old_priv_key = base64.b64decode(old_key_row[0])

            # 1. Download old encrypted blob from MinIO
            tmp_in = os.path.join(tempfile.gettempdir(), f"heal_in_{uuid.uuid4().hex}.bin")
            try:
                s3.download_file(bucket, minio_key, tmp_in)
                with open(tmp_in, 'rb') as f:
                    old_blob = f.read()
            finally:
                if os.path.exists(tmp_in): os.unlink(tmp_in)

            # 2. Recover old AES key via Kyber decapsulation — never from DB
            old_aes_key = decapsulate_to_aes_key(old_priv_key, old_kyber_ct_b64)

            # 3. Decrypt plaintext with old AES key
            old_nonce      = old_blob[:12]
            old_ciphertext = old_blob[12:]
            old_aesgcm     = AESGCM(old_aes_key)
            plaintext      = old_aesgcm.decrypt(old_nonce, old_ciphertext, None)

            # 4. Generate new Kyber keypair
            new_pub_key, new_priv_key = generate_keypair()

            # 5. New AES key IS the new Kyber shared secret — never stored
            new_kyber_ct_b64, new_aes_key = encapsulate_to_aes_key(new_pub_key)

            # 6. Re-encrypt plaintext with new AES key
            new_aesgcm  = AESGCM(new_aes_key)
            new_nonce   = os.urandom(12)
            new_ct      = new_aesgcm.encrypt(new_nonce, plaintext, None)
            new_blob    = new_nonce + new_ct

            # 7. Re-upload to MinIO — overwrites old encrypted blob
            tmp_out = os.path.join(tempfile.gettempdir(), f"heal_out_{uuid.uuid4().hex}.bin")
            try:
                with open(tmp_out, 'wb') as f:
                    f.write(new_blob)
                s3.upload_file(tmp_out, bucket, minio_key)
            finally:
                if os.path.exists(tmp_out): os.unlink(tmp_out)

            # 8. Update DB — only Kyber ciphertext and private key written
            #    encrypted_aes_key is never touched
            new_priv_key_b64 = base64.b64encode(new_priv_key).decode()
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2  = conn2.cursor()
            cur2.execute(
                "UPDATE files SET kyber_ciphertext = %s, "
                "key_version = key_version + 1 WHERE id = %s",
                (new_kyber_ct_b64, file_id)
            )
            cur2.execute(
                "UPDATE users SET kyber_private_key_encrypted = %s WHERE id = %s",
                (new_priv_key_b64, file_owner_id)
            )
            # 9. Write structured audit record
            cur2.execute(
                """INSERT INTO key_rotation_log
                   (id, user_id, file_id, old_key_version, new_key_version, trigger_reason)
                   VALUES (gen_random_uuid(), %s, %s,
                           (SELECT key_version - 1 FROM files WHERE id = %s),
                           (SELECT key_version     FROM files WHERE id = %s),
                           'ANOMALY_TRIGGERED')""",
                (file_owner_id, file_id, file_id, file_id)
            )
            conn2.commit()
            cur2.close()
            conn2.close()

            rotation_log.append({
                "file_id":             file_id,
                "file_name":           original_name,
                "status":              "rotated",
                "old_kyber_preview":   old_kyber_ct_b64[:32] + "...",
                "new_kyber_preview":   new_kyber_ct_b64[:32] + "...",
                "plaintext_size_bytes": len(plaintext),
                "aes_key_in_db":       False,
            })
            logger.info(f"[SELF-HEAL] ✓ Key rotation complete for {original_name}")

        except Exception as e:
            logger.error(f"[SELF-HEAL] ✗ Failed to rotate {original_name}: {e}")
            rotation_log.append({
                "file_id":   file_id,
                "file_name": original_name,
                "status":    "failed",
                "error":     str(e)
            })

    return {
        "status":        "self_healing_complete",
        "files_rotated": len([r for r in rotation_log if r["status"] == "rotated"]),
        "files_failed":  len([r for r in rotation_log if r["status"] == "failed"]),
        "rotation_log":  rotation_log
    }

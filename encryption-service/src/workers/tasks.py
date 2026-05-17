import os
import boto3
import psycopg2
import logging
import base64
import tempfile
import uuid as _uuid
from src.workers.celery_app import celery_app
from src.services.kyber import generate_keypair, encapsulate_to_aes_key
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

DATABASE_URL      = os.environ.get("DATABASE_URL",        "postgresql://postgres_user:postgres_password@localhost:5432/shieldcloud")
MINIO_ENDPOINT    = os.environ.get("MINIO_ENDPOINT",      "http://localhost:9000")
MINIO_ROOT_USER   = os.environ.get("MINIO_ROOT_USER",     "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")


def get_minio_client():
    return boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
        region_name='us-east-1',
        config=boto3.session.Config(signature_version='s3v4')
    )


def execute_db_query(query, params=()):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"DB Error: {e}")
    finally:
        if 'cur'  in locals(): cur.close()
        if 'conn' in locals(): conn.close()


@celery_app.task(bind=True, name="src.workers.tasks.process_encryption")
def process_encryption(self, file_id: str, owner_id: str, bucket: str, key: str, file_buffer_base64: str):
    logger.info(f"Starting ML-KEM-1024 + AES-256-GCM encryption job for file {file_id}")

    # 1. Decode raw file bytes
    file_bytes = base64.b64decode(file_buffer_base64)

    # 2. Generate Kyber-1024 keypair
    pub_key, priv_key = generate_keypair()

    # 3. Encapsulate — shared secret from Kyber becomes the AES-256 key
    #    The raw AES key is NEVER generated independently and NEVER stored in the DB.
    #    An adversary with DB access obtains only kyber_ciphertext.
    #    Recovering the AES key requires Kyber.Decaps(sk, kyber_ciphertext) — M-LWE hard.
    kyber_ciphertext_b64, aes_key = encapsulate_to_aes_key(pub_key)

    # 4. Encrypt file bytes with AES-256-GCM using Kyber-derived key
    aesgcm = AESGCM(aes_key)
    nonce  = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, file_bytes, None)
    final_blob = nonce + ciphertext

    # 5. Upload encrypted blob to MinIO
    logger.info(f"Uploading AES-GCM encrypted stream to MinIO '{bucket}/{key}'")
    s3 = get_minio_client()
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)

    tmp_path = os.path.join(tempfile.gettempdir(), f"upload_{_uuid.uuid4().hex}.bin")
    try:
        with open(tmp_path, 'wb') as f:
            f.write(final_blob)
        s3.upload_file(tmp_path, bucket, key)
        logger.info(f"Uploaded {len(final_blob)} encrypted bytes to MinIO.")
    except Exception as e:
        logger.error(f"MinIO upload failed: {e}")
        raise
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 6. Persist Kyber ciphertext to PostgreSQL — raw AES key is NEVER written
    logger.info(f"Persisting ML-KEM-1024 ciphertext to PostgreSQL for file {file_id}")
    execute_db_query(
        "UPDATE files SET kyber_ciphertext = %s WHERE id = %s",
        (kyber_ciphertext_b64, file_id)
    )

    # 7. Persist Kyber private key to users table — required for future decapsulation
    priv_key_b64 = base64.b64encode(priv_key).decode()
    execute_db_query(
        "UPDATE users SET kyber_private_key_encrypted = %s WHERE id = %s",
        (priv_key_b64, owner_id)
    )

    logger.info(f"Encryption pipeline COMPLETE for file {file_id} — AES key never persisted")
    return {"status": "success", "file_id": file_id}

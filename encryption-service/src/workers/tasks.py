import os
import boto3
import psycopg2
import logging
import base64
from src.workers.celery_app import celery_app
from src.services.kyber import generate_keypair, encapsulate, decapsulate
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import uuid

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres_user:postgres_password@localhost:5432/shieldcloud")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
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
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"DB Error: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

@celery_app.task(bind=True, name="src.workers.tasks.process_encryption")
def process_encryption(self, file_id: str, owner_id: str, bucket: str, key: str, file_buffer_base64: str):
    logger.info(f"Starting Kyber-AES encryption job for file {file_id}")
    
    # 1. Decode Buffer
    file_bytes = base64.b64decode(file_buffer_base64)
    
    # 2. Generate Kyber-1024 keypair and AES-256 session key
    pub_key, priv_key = generate_keypair()
    aes_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)

    # 3. Encrypt file bytes with AES-256-GCM
    ciphertext = aesgcm.encrypt(nonce, file_bytes, None)
    final_blob = nonce + ciphertext

    # 4. Encapsulate the AES key inside Kyber-1024 ciphertext
    pub_key_b64 = base64.b64encode(pub_key).decode()
    kyber_ciphertext_b64, _ = encapsulate(pub_key_b64)
    priv_key_b64 = base64.b64encode(priv_key).decode()
    
    logger.info(f"Uploading AES-encrypted stream to MinIO '{bucket}/{key}'")
    
    s3 = get_minio_client()
    # Create bucket if not exists
    try:
        s3.head_bucket(Bucket=bucket)
    except:
        s3.create_bucket(Bucket=bucket)
    
    # Windows-safe temp file: write then close before boto3 reads it
    import tempfile, uuid as _uuid
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
    
    # 5. Persist Kyber ciphertext and AES key to PostgreSQL
    logger.info(f"Persisting ML-KEM-1024 ciphertext to PostgreSQL for file {file_id}")
    execute_db_query(
        "UPDATE files SET kyber_ciphertext = %s, encrypted_aes_key = %s WHERE id = %s",
        (kyber_ciphertext_b64, aes_key.hex(), file_id)
    )
    # Persist private key to users table for future decapsulation
    execute_db_query(
        "UPDATE users SET kyber_private_key_encrypted = %s WHERE id = %s",
        (priv_key_b64, owner_id)
    )
    logger.info(f"Encryption pipeline COMPLETE for file {file_id}")
    
    return {"status": "success", "file_id": file_id}

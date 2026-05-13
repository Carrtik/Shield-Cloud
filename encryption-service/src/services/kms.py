import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres_user:postgres_password@localhost:5432/shieldcloud")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_user_kyber_keys(user_id: str):
    """Fetch user's public and encrypted private Kyber keys from DB."""
    db = SessionLocal()
    try:
        query = text("SELECT kyber_public_key, kyber_private_key_encrypted FROM users WHERE id = :uid")
        result = db.execute(query, {"uid": user_id}).fetchone()
        if result:
            return {"public_key": result[0], "private_key_encrypted": result[1]}
        return None
    finally:
        db.close()

def store_file_keys(file_id: str, owner_id: str, original_name: str, stored_name: str, minio_bucket: str, minio_key: str, size_bytes: int, encrypted_aes: str, kyber_cipher: str):
    """Store encrypted keys into the files table."""
    db = SessionLocal()
    try:
        query = text("""
            INSERT INTO files (id, owner_id, original_name, stored_name, minio_bucket, minio_key, size_bytes, encrypted_aes_key, kyber_ciphertext)
            VALUES (:id, :owner_id, :orig, :stored, :bucket, :mkey, :size, :enc_aes, :kyber_cipher)
        """)
        db.execute(query, {
            "id": file_id,
            "owner_id": owner_id,
            "orig": original_name,
            "stored": stored_name,
            "bucket": minio_bucket,
            "mkey": minio_key,
            "size": size_bytes,
            "enc_aes": encrypted_aes,
            "kyber_cipher": kyber_cipher
        })
        db.commit()
    finally:
        db.close()

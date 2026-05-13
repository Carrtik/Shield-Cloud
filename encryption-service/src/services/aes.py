import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def derive_key(shared_secret: bytes, salt: bytes = None) -> tuple[bytes, bytes]:
    """Derives a 32-byte AES key from a Kyber shared secret using HKDF-SHA256."""
    if not salt:
        salt = os.urandom(16)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b'file_encryption'
    )
    key = hkdf.derive(shared_secret)
    return key, salt

def encrypt(data: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Encrypts plaintext using AES-256-GCM. Returns (nonce, ciphertext)."""
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce, ciphertext

def decrypt(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """Decrypts ciphertext using AES-256-GCM."""
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    if len(nonce) != 12:
        raise ValueError("Nonce must be 12 bytes for AES-GCM")
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

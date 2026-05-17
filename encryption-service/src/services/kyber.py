import base64
import os

try:
    import oqs
except ImportError:
    raise RuntimeError(
        "liboqs is not installed. ML-KEM-1024 is mandatory for Shield Cloud. "
        "Install it with: pip install liboqs-python"
    )

# ML-KEM is the NIST standardized name (FIPS 203).
# liboqs references the same construction via its pre-standardization identifier 'Kyber1024'.
KEM_ALGORITHM = 'Kyber1024'


def generate_keypair():
    """
    Generates a Kyber-1024 public/private keypair using liboqs.
    Returns (public_key_bytes, private_key_bytes).
    """
    kem = oqs.KeyEncapsulation(KEM_ALGORITHM)
    public_key  = kem.generate_keypair()
    private_key = kem.export_secret_key()
    kem.free()
    return public_key, private_key


def encapsulate_to_aes_key(public_key: bytes):
    """
    Performs ML-KEM-1024 encapsulation against the provided public key.

    The Kyber shared secret (32 bytes / 256 bits) is returned directly
    as the AES-256 session key. The raw AES key is therefore NEVER stored
    in the database — an adversary who obtains the DB acquires only the
    Kyber ciphertext, whose decapsulation requires the private key and
    reduces to the M-LWE hardness assumption.

    Returns:
        kyber_ciphertext_b64 : str   — base64-encoded Kyber ciphertext for DB storage
        aes_key              : bytes — 32-byte AES-256 key derived from shared secret
    """
    kem = oqs.KeyEncapsulation(KEM_ALGORITHM)
    ciphertext, shared_secret = kem.encap_secret(public_key)
    kem.free()
    # shared_secret from Kyber1024 is exactly 32 bytes — valid AES-256 key
    return base64.b64encode(ciphertext).decode('utf-8'), shared_secret


def decapsulate_to_aes_key(private_key: bytes, ciphertext_b64: str) -> bytes:
    """
    Performs ML-KEM-1024 decapsulation to recover the AES-256 session key.

    The recovered shared secret is identical to the one produced during
    encapsulation — this IS the AES key. No AES key is ever read from
    the database; it is reconstructed on demand from the Kyber ciphertext.

    Returns:
        aes_key : bytes — 32-byte AES-256 key recovered via M-LWE decapsulation
    """
    kem = oqs.KeyEncapsulation(KEM_ALGORITHM)
    kem.secret_key = private_key
    ciphertext     = base64.b64decode(ciphertext_b64)
    shared_secret  = kem.decap_secret(ciphertext)
    kem.free()
    return shared_secret


def encapsulate(public_key_b64: str):
    """
    Legacy encapsulation interface retained for compatibility.
    Prefer encapsulate_to_aes_key() for all new call sites.
    """
    kem        = oqs.KeyEncapsulation(KEM_ALGORITHM)
    public_key = base64.b64decode(public_key_b64)
    ciphertext, shared_secret = kem.encap_secret(public_key)
    kem.free()
    return base64.b64encode(ciphertext).decode('utf-8'), shared_secret


def decapsulate(private_key_b64: str, ciphertext_b64: str) -> bytes:
    """
    Legacy decapsulation interface retained for compatibility.
    Prefer decapsulate_to_aes_key() for all new call sites.
    """
    kem         = oqs.KeyEncapsulation(KEM_ALGORITHM)
    private_key = base64.b64decode(private_key_b64)
    kem.secret_key = private_key
    ciphertext  = base64.b64decode(ciphertext_b64)
    shared_secret = kem.decap_secret(ciphertext)
    kem.free()
    return shared_secret

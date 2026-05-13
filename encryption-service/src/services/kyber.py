import base64
import os

try:
    import oqs
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False
    print("WARNING: oqs not found, using Mock Kyber1024 for E2E fast testing.")

# Note: ML-KEM is the standardized name; liboqs might still use its internal names like 'Kyber1024' or 'ML-KEM-1024'
KEM_ALGORITHM = 'Kyber1024'

def generate_keypair():
    """Generates a Kyber-1024 public/private keypair."""
    if not OQS_AVAILABLE:
        # Generate mock 1184-byte public key and 3168-byte private key for Kyber-1024 simulation
        pub = os.urandom(1184)
        priv = os.urandom(3168)
        return pub, priv

    kem = oqs.KeyEncapsulation(KEM_ALGORITHM)
    public_key = kem.generate_keypair()
    private_key = kem.export_secret_key()
    kem.free()
    return public_key, private_key

def encapsulate(public_key_b64: str):
    """Encapsulates a shared secret using the provided public key."""
    kem = oqs.KeyEncapsulation(KEM_ALGORITHM)
    public_key = base64.b64decode(public_key_b64)
    ciphertext, shared_secret = kem.encap_secret(public_key)
    kem.free()
    return base64.b64encode(ciphertext).decode('utf-8'), shared_secret

def decapsulate(private_key_b64: str, ciphertext_b64: str) -> bytes:
    """Decapsulates the shared secret using the private key and ciphertext."""
    kem = oqs.KeyEncapsulation(KEM_ALGORITHM)
    private_key = base64.b64decode(private_key_b64)
    kem.secret_key = private_key
    ciphertext = base64.b64decode(ciphertext_b64)
    shared_secret = kem.decap_secret(ciphertext)
    kem.free()
    return shared_secret

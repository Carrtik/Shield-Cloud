import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Simulate upload
original = b"Hello world 1234. This is a text file!"
aes_key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(aes_key)
nonce = os.urandom(12)
ciphertext = aesgcm.encrypt(nonce, original, None)
final_blob = nonce + ciphertext

# write to fake minio
with open("fake_minio.bin", "wb") as f:
    f.write(final_blob)

# Simulate download
with open("fake_minio.bin", "rb") as f:
    blob = f.read()

d_nonce = blob[:12]
d_cipher = blob[12:]
d_aesgcm = AESGCM(aes_key)
plaintext = d_aesgcm.decrypt(d_nonce, d_cipher, None)

print("Decrypted:", plaintext)

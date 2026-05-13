import requests, time, subprocess

content = b'Hello ShieldCloud! This is a real file encrypted with Kyber-1024 AES-256-GCM. If you can read this, the full PQC pipeline is working correctly!'
files = {'file': ('capstone_demo.txt', content, 'text/plain')}

print('1. Uploading file to storage service...')
r = requests.post('http://localhost:3003/storage/upload', files=files)
print(f'   Status: {r.status_code}')
data = r.json()
file_id = data.get('file_id')
print(f'   File ID: {file_id}')

if not file_id:
    print('FAIL: No file_id returned')
    exit(1)

time.sleep(2)

print('2. Verifying DB record has Kyber key...')
result = subprocess.run(
    ['docker', 'exec', '-i', 'infra-postgres-1', 'psql', '-U', 'postgres_user', '-d', 'shieldcloud', '-c',
    f"SELECT original_name, length(kyber_ciphertext) as kyber_len, length(encrypted_aes_key) as aes_len FROM files WHERE id='{file_id}';"],
    capture_output=True, text=True
)
print(result.stdout)

print('3. Testing decryption and download...')
resp = requests.get(f'http://127.0.0.1:3002/decrypt/{file_id}')
print(f'   Status: {resp.status_code}')
if resp.status_code == 200:
    decoded = resp.content
    print(f'   Downloaded: {len(decoded)} bytes')
    print(f'   Checksum match (original == decrypted): {decoded == content}')
    print(f'   Content: {decoded.decode()}')
else:
    print(f'   Error body: {resp.text}')

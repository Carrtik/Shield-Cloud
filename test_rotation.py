import requests

print("Testing /self-heal/rotate-keys endpoint...")
r = requests.post("http://127.0.0.1:3002/self-heal/rotate-keys")
print("Status:", r.status_code)
data = r.json()
print("Files rotated:", data.get("files_rotated"))
print("Files failed:", data.get("files_failed"))
for entry in data.get("rotation_log", []):
    print()
    print("  File:", entry["file_name"])
    print("  Status:", entry["status"])
    if entry["status"] == "rotated":
        print("  OLD Kyber:", entry["old_kyber_preview"])
        print("  NEW Kyber:", entry["new_kyber_preview"])
        print("  OLD AES:  ", entry["old_aes_preview"])
        print("  NEW AES:  ", entry["new_aes_preview"])
        print("  Keys actually changed:", entry["old_kyber_preview"] != entry["new_kyber_preview"])

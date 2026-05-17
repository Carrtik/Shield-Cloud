import requests
import time

print("Testing /self-heal/rotate-keys endpoint...")

rotation_start = time.time()
r = requests.post("http://127.0.0.1:3002/self-heal/rotate-keys")
rotation_elapsed = time.time() - rotation_start

print("Status:", r.status_code)
print(f"Total rotation time: {rotation_elapsed:.2f} seconds")
assert rotation_elapsed < 90, f"SLA BREACH: rotation took {rotation_elapsed:.2f}s — exceeds 90s bound"
print("SLA Check: PASSED — rotation completed within 90-second bound")

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
        print("  Keys actually changed:", entry["old_kyber_preview"] != entry["new_kyber_preview"])

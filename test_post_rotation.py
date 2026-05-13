import requests

r = requests.get("http://localhost:3003/storage/files")
files = r.json()["files"]
print("Verifying all files still accessible after key rotation:")
for f in files:
    dl = requests.get("http://127.0.0.1:3002/decrypt/" + f["id"])
    ok = "OK" if dl.status_code == 200 else "FAIL"
    size = len(dl.content) if dl.status_code == 200 else 0
    print(f"  {ok} | {f['original_name']} | {size} bytes downloaded")

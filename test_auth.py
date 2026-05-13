import requests, json

BASE = "http://localhost:3001/auth"

print("=== Testing AUTH SERVICE ===")
print()

# 1. Register
print("1. Register new user...")
r = requests.post(f"{BASE}/register", json={"email": "demo@shieldcloud.local", "name": "Demo User", "password": "secure123"})
print(f"   Status: {r.status_code}")
if r.status_code in (200, 201):
    data = r.json()
    token = data["token"]
    user = data["user"]
    print(f"   User: {user['email']} (id: {user['id'][:8]}...)")
    print(f"   JWT: {token[:40]}...")
elif r.status_code == 400 and "already" in r.text:
    print("   Already registered, trying login...")
    token = None
else:
    print(f"   ERROR: {r.text}")
    exit(1)

# 2. Login
print("\n2. Login...")
r2 = requests.post(f"{BASE}/login", json={"email": "demo@shieldcloud.local", "password": "secure123"})
print(f"   Status: {r2.status_code}")
if r2.status_code in (200, 201):
    data2 = r2.json()
    token = data2["token"]
    print(f"   Token received: {token[:40]}...")
else:
    print(f"   ERROR: {r2.text}")
    exit(1)

# 3. /me
print("\n3. Get /me with token...")
r3 = requests.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
print(f"   Status: {r3.status_code}")
print(f"   User: {r3.json()}")

print("\n=== AUTH PIPELINE WORKING ===")

# ShieldCloud — Post-Quantum AI Self-Healing Cloud Storage
## Complete Project Documentation

---

## 1. What This Project Does (30-Second Pitch)

ShieldCloud is a cloud storage system that protects files against **both today's hackers AND future quantum computers**. It uses:
- **Hybrid quantum-resistant encryption** (AES-256-GCM + CRYSTALS-Kyber ML-KEM-1024) so that even if someone steals encrypted files today, they can never decrypt them — even with a quantum computer.
- **An AI watchdog** (XGBoost ML model trained on 10,000 threat scenarios) that watches every upload and download in real-time. The moment it detects a breach pattern, it acts autonomously.
- **Autonomous self-healing** — the system literally heals itself. It re-encrypts every file with fresh quantum keys, logs out the attacker, and emails the real user — all within seconds, with zero human intervention.

---

## 2. The Threat It Solves: Harvest-Now-Decrypt-Later (HNDL)

A nation-state attacker today downloads your encrypted cloud storage backup. It is encrypted with RSA-2048. They cannot decrypt it **today**. But in 5-10 years, a cryptographically-relevant quantum computer running **Shor's Algorithm** decrypts every file in hours.

**ShieldCloud's answer:** Even if an attacker harvests the ciphertext today, `CRYSTALS-Kyber` is based on the **Module Learning With Errors (MLWE) lattice problem** — a mathematical problem that quantum computers cannot solve faster than classical ones. NIST standardized Kyber (as ML-KEM) in August 2024 specifically to defend against this attack.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER DEVICES                             │
│   Browser / Phone / Tablet  →  Vercel (React Frontend)         │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│               API GATEWAY  (Express.js :8080)                   │
│           Exposed publicly via Cloudflare Tunnel                │
├──────────┬────────────┬──────────┬───────────┬──────────────────┤
│  /auth   │  /storage  │ /decrypt │  /ingest  │   /socket.io     │
▼          ▼            ▼          ▼           ▼
┌────────┐ ┌──────────┐ ┌────────────────────┐ ┌────────────────────┐
│  Auth  │ │ Storage  │ │ Encryption Service │ │   Risk Engine      │
│NestJS  │ │ NestJS   │ │    FastAPI         │ │  FastAPI+SocketIO  │
│ :3001  │ │  :3003   │ │    :3002           │ │     :3005          │
└────┬───┘ └────┬─────┘ └────────┬───────────┘ └────────┬───────────┘
     │          │                │                       │
     ▼          ▼                ▼                       ▼
┌───────────────────────────────────────────────────────────────┐
│             INFRASTRUCTURE  (Docker Compose)                  │
│   PostgreSQL :5432  │  MinIO :9000  │  Redis :6379           │
│   RabbitMQ :5672    │  (S3-compat)  │  (counters)            │
└───────────────────────────────────────────────────────────────┘
                              │ RabbitMQ queues
              ┌───────────────┼────────────────┐
              ▼                               ▼
┌─────────────────────┐         ┌───────────────────────────┐
│  Self-Healing Worker│         │  Notification Service     │
│  Python consumer    │         │  Node.js + nodemailer     │
│  Rotates Kyber keys │         │  Sends HTML security email│
└─────────────────────┘         └───────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  Anomaly ML Service :3004    │
│  FastAPI + XGBoost           │
│  Trained on 10,000 samples   │
│  20 threat features          │
└──────────────────────────────┘
```

---

## 4. The 10 Services

| # | Service | Technology | Port | Purpose |
|---|---------|-----------|------|---------|
| 1 | **Auth Service** | NestJS + JWT + bcrypt | 3001 | User registration, login, JWT issuance |
| 2 | **Storage Service** | NestJS + PostgreSQL | 3003 | File metadata, upload orchestration |
| 3 | **Encryption Service** | FastAPI + Kyber + AES | 3002 | Encrypt/decrypt files, key rotation |
| 4 | **Anomaly ML Service** | FastAPI + XGBoost | 3004 | Classify requests as normal/attack |
| 5 | **Risk Engine** | FastAPI + Socket.IO | 3005 | Composite risk scoring, broadcast alerts |
| 6 | **Self-Healing Worker** | Python + pika | — | Consume RabbitMQ, trigger key rotation |
| 7 | **Notification Service** | Node.js + nodemailer | — | Send HTML security emails on breach |
| 8 | **API Gateway** | Express.js | 8080 | Single entry point, proxy all services |
| 9 | **Frontend** | React + Vite + Recharts | 5173 | Dashboard, file vault, live ML chart |
| 10 | **Infrastructure** | Docker Compose | Various | PostgreSQL, MinIO, Redis, RabbitMQ |

---

## 5. Encryption Deep-Dive: How Files Are Protected

### Step-by-Step Upload Flow

```
User selects file.png (10 MB)
         │
         ▼
Storage Service receives the raw bytes via multipart/form-data
         │
         ▼
Encryption Service — Process:
  1. Generate a random AES-256 key  (32 bytes of /dev/urandom)
  2. Generate a Kyber-1024 keypair   (1568-byte public key, 3168-byte private key)
  3. Encrypt the AES key using the Kyber public key  → kyber_ciphertext (1568 bytes)
  4. Generate a random 12-byte nonce
  5. Encrypt file bytes with AESGCM(aes_key, nonce)  → encrypted_blob
  6. Store: nonce + encrypted_blob  →  MinIO object store
  7. Store: kyber_ciphertext, encrypted_aes_key  →  PostgreSQL
         │
         ▼
User's file is now in two protected layers:
  Layer 1: Content is AES-256-GCM encrypted (quantum-safe for symmetric keys)
  Layer 2: The AES key itself is Kyber-encapsulated (post-quantum asymmetric)
```

### Step-by-Step Download Flow

```
User clicks Download
         │
         ▼
GET /decrypt/{file_id}  →  Encryption Service
  1. Fetch kyber_ciphertext + encrypted_aes_key from PostgreSQL
  2. Decapsulate the Kyber ciphertext  →  recover the raw AES key
  3. Fetch nonce+ciphertext blob from MinIO
  4. Split first 12 bytes as nonce
  5. AES-GCM decrypt(nonce, ciphertext, aes_key)  →  original bytes
  6. StreamingResponse with Content-Disposition filename header
  7. ALSO: emit download telemetry to Risk Engine (bytes, count)
         │
         ▼
Browser receives the exact original file.
```

---

## 6. AI Self-Healing Flow (The "Wow" Part)

### What Triggers It

Every download fires a telemetry event to the Risk Engine. Redis accumulates:
- `dl_count:{user_id}` — rolling 1-hour download count
- `dl_bytes:{user_id}` — rolling 1-hour bytes transferred

When downloads spike (e.g., someone rapidly downloading all files), the XGBoost model processes a 20-feature vector:

| Feature | Normal Value | Attack Value |
|---------|-------------|-------------|
| `download_count_last_1h` | 1-5 | 50-200 |
| `bytes_transferred_last_1h` | ~1 MB | ~5 GB |
| `geo_velocity_kmh` | 0 | 12,000 |
| `vpn_detected` | 0 | 1 |
| `ip_location_mismatch` | 0 | 1 |
| `is_bulk_download` | 0 | 1 |

### What Happens When Score > 0.90

```
ML returns anomaly_score=0.97, is_anomaly=True
         │
         ▼
Risk Engine composite score > 0.85 → risk_level="CRITICAL"
         │
     ┌───┴───────────────────────────────┐
     ▼                                   ▼
Socket.IO emits                    RabbitMQ publishes
"account_isolated"                 to "risk.high" queue
to ALL browsers                          │
     │                            ┌──────┴──────┐
     ▼                            ▼             ▼
Dashboard shows             Self-Healing    Notification
QUARANTINE MODAL            Worker fires    Service sends
Countdown 8s                rotate-keys     HTML email
Then clears token                │          with preview URL
Redirects to /login              ▼
                         For EVERY file in vault:
                           1. Download ciphertext from MinIO
                           2. AES-GCM decrypt with OLD key
                           3. Generate NEW Kyber-1024 keypair
                           4. Generate NEW AES-256 key
                           5. Re-encrypt plaintext
                           6. Upload to MinIO (overwrite)
                           7. Update PostgreSQL with new keys
                         → Attacker's stolen ciphertext is NOW INVALID
```

---

## 7. Demo Script (For Judges)

### Setup (done once)
```powershell
.\start.ps1
```

### Live Demo Steps

**Step 1 — Show the Login**
- Open `http://localhost:5173`
- Register a new account, then log in
- *"This is JWT-based authentication with bcrypt password hashing"*

**Step 2 — Upload a File**
- Click "Upload Secure File", pick any photo or PDF
- *"Watch the Secure File Vault. The file appears within 2 seconds"*
- Click the purple `</>` button to reveal live keys from PostgreSQL
- *"Those iridescent hex strings are the CRYSTALS-Kyber public key encapsulation. The blue string below is the AES-256 symmetric key, protected inside the Kyber lattice."*

**Step 3 — Show the Database**
```powershell
docker exec -it infra-postgres-1 psql -U postgres_user -d shieldcloud
```
Then in psql:
```sql
\i demo_queries.sql   -- loads all demo queries
-- Run Query #10 for system summary
-- Run Query #2 to see live quantum keys
```

**Step 4 — Trigger the Self-Healing Attack (Organically)**
- Rapidly click Download on every file in your vault (5+ times total)
- Watch the LIVE ML chart on the left spike upward
- At ~5 downloads the XGBoost outputs 0.97 anomaly score
- *"The ML model detected a Harvest-Now-Decrypt-Later pattern — mass download in a short window"*
- The dashboard turns RED → CRITICAL ANOMALY banner
- After ~10 seconds: "Self-Healing Complete" modal appears showing OLD vs NEW keys

**Step 5 — Show the Attacker Getting Kicked Out**
- Open the site in a private/incognito browser tab (simulating the attacker)
- In the attacker's tab: a red QUARANTINE MODAL appears with a countdown
- After 8 seconds the attacker is forcibly redirected to /login
- Their JWT is deleted. The ciphertext they downloaded is garbage.

**Step 6 — Show the Security Email**
- Look in the Notification job's terminal output
- Find the line `PREVIEW: https://ethereal.email/message/...`
- Open it in a browser → shows the full professional HTML security alert email

---

## 8. Deployment: Vercel + Cloudflare Tunnel

### One-Time Setup

```powershell
# Install Cloudflare tunnel (no account needed)
winget install Cloudflare.cloudflared

# From a second terminal WHILE start.ps1 is running:
cloudflared tunnel --url http://localhost:8080
# → Prints: https://abc123def.trycloudflare.com
```

### Vercel Frontend Deployment

```bash
cd frontend
npx vercel  # or: vercel --prod

# When prompted for environment variables, add:
# VITE_GATEWAY_URL = https://abc123def.trycloudflare.com
```

The Vercel URL (e.g., `https://shieldcloud.vercel.app`) then works from **any device, anywhere in the world**, routing API calls through the cloudflare tunnel to your laptop's AI engine.

---

## 9. Security Credentials (for demo/dev only)

| Service | Username | Password | URL |
|---------|----------|----------|-----|
| PostgreSQL | `postgres_user` | `postgres_password` | localhost:5432 |
| MinIO | `minioadmin` | `minioadmin` | http://localhost:9001 |
| RabbitMQ | `guest` | `guest` | http://localhost:15672 |

---

## 10. Tech Stack Summary

| Layer | Technology | Why |
|-------|-----------|-----|
| Post-Quantum Crypto | CRYSTALS-Kyber ML-KEM-1024 via `liboqs` | NIST PQC Standard 2024 |
| Symmetric Crypto | AES-256-GCM via Python `cryptography` | Authenticated encryption |
| ML Model | XGBoost + SMOTE balancing | High recall on imbalanced threat data |
| Message Queue | RabbitMQ | Decoupled self-healing trigger |
| Object Storage | MinIO (S3-compatible) | Self-hosted, GDPR-friendly |
| Database | PostgreSQL | ACID-compliant key storage |
| Cache/Counters | Redis | 1-hour rolling download counters |
| Backend APIs | FastAPI (Python), NestJS (TypeScript) | Type-safe, async, fast |
| Frontend | React 18 + Vite + Recharts | Real-time WebSocket dashboard |
| Hosting | Vercel + Cloudflare Tunnel | Global CDN + secure tunnel |

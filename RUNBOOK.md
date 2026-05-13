# 🚀 ShieldCloud Complete Demonstration / Execution Guide

This guide walks you step-by-step through running the project and accessing it from any device.

---

## 🛠️ Phase 1: One-Command Startup

1. **Open PowerShell** in the project root: `C:\Users\sahis\Desktop\Final_proj_8th_sem`
2. **Run the startup script:**
   ```powershell
   .\start.ps1
   ```
   Wait ~25 seconds for all 11 `[OK]` messages to appear.

3. **What starts automatically:**
   | # | Service | Port |
   |---|---------|------|
   | 1 | Docker (PostgreSQL, MinIO, Redis, RabbitMQ) | internal |
   | 2 | Auth Service (NestJS) | :3001 |
   | 3 | Storage Service (NestJS) | :3003 |
   | 4 | Encryption Service (FastAPI + Kyber) | :3002 |
   | 5 | Anomaly ML Service (FastAPI + XGBoost) | :3004 |
   | 6 | Risk Engine (FastAPI + Socket.IO) | :3005 |
   | 7 | Self-Healing Consumer (Python + RabbitMQ) | — |
   | 8 | **Notification Service (Socket.IO + Email)** | :3006 |
   | 9 | API Gateway (Express proxy) | :8080 |
   | 10 | Frontend (Vite + React) | :5173 |
   | 11 | **Cloudflare Tunnel (Internet access)** | auto |

---

## 🌐 Phase 2: Cross-Device Access (Internet)

After startup, the console will print:

```
INTERNET ACCESS (any device, anywhere):
https://xxxx-xxxx-xxxx.trycloudflare.com
```

**Open that URL on any device — phone, tablet, laptop — logged in to your account.**
- No VPN required
- No password popups
- Works globally over the internet
- Cloudflared is auto-downloaded if not installed

**LAN access** (same WiFi only):
```
http://<your-ip>:5173
```

---

## 🖥️ Phase 3: Feature Demonstration

### Step 1: Register / Login
- Go to the dashboard URL, click **Create Account** or **Sign In**
- **Each account is isolated** — files uploaded by one user are not visible to others

### Step 2: Upload a Quantum-Safe File
1. Click **Upload File** → pick any `.txt` or `.png`
2. File is AES-256-GCM encrypted; key is encapsulated with Kyber-1024
3. Click the `</>` icon on any file tile to inspect live DB crypto keys

### Step 3: Navigate All Pages
- **Files** — Full vault with search, download, delete per file
- **Security Center** — 48-hour anomaly timeline + threat event log
- **Admin Panel** — User list (admin accounts), global key rotation
- **Settings** — Change password, notification preferences

### Step 4: Trigger the ML Self-Healing Demo
1. Click **Inject Harvesting Attack** (Dashboard or Security Center)
2. Watch the chart spike to **~0.98 CRITICAL**
3. **In-app toast fires instantly** (from Notification Service via Socket.IO)
4. Self-Healing worker picks up `risk.high` from RabbitMQ
5. Keys rotate: new Kyber-1024 keypair + new AES-256-GCM key generated
6. Rotation audit modal pops up — shows OLD vs NEW keys side-by-side
7. Console prints an **Ethereal email preview URL** — click it to see the full HTML security alert
8. Chart resets to LOW

### Step 5: Real-Time Notification Architecture
- Risk Engine → emits `risk.high` to **RabbitMQ**
- Notification Service consumes it → emits `security_alert` via **Socket.IO on :3006**
- Frontend **Layout.tsx** listens on `/notifications` namespace → fires `addNotification()`
- Bell icon in sidebar shows unread count badge

---

## 🛑 Shutdown
Press `Ctrl+C` in the PowerShell window running `start.ps1`. All 11 services stop cleanly.

---

## 🔑 Default Credentials
| System | URL | Credentials |
|--------|-----|-------------|
| App Dashboard | http://localhost:5173 | Register any email/password |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| RabbitMQ UI | http://localhost:15672 | guest / guest |

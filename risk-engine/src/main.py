from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
import uvicorn
import socketio
import requests
import redis
import pika
import json
import time
import os
from datetime import datetime

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI(title="Risk Engine Service", version="2.0.0")
sio_app = socketio.ASGIApp(sio, app)

ANOMALY_SERVICE_URL    = os.getenv("ANOMALY_SERVICE_URL",    "http://localhost:3004/analyze")
ENCRYPTION_SERVICE_URL = os.getenv("ENCRYPTION_SERVICE_URL", "http://localhost:3002/self-heal/rotate-keys")
RABBITMQ_URL           = os.getenv("RABBITMQ_URL",           "amqp://guest:guest@localhost:5672")
REDIS_URL              = os.getenv("REDIS_URL",              "redis://localhost:6379")

try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("[Risk Engine] Redis connected.")
except Exception as e:
    print(f"[Risk Engine] Redis unavailable: {e}. Counters will degrade gracefully.")
    r = None


def redis_incr_window(key: str, window_secs: int = 3600) -> int:
    if not r:
        return 0
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, window_secs)
        return count
    except Exception:
        return 0


def redis_add_bytes(key: str, amount: int, window_secs: int = 3600) -> int:
    if not r:
        return amount
    try:
        total = r.incrby(key, amount)
        if int(total) == amount:
            r.expire(key, window_secs)
        return int(total)
    except Exception:
        return amount


def publish_to_rabbitmq(payload: dict, queue: str = "risk.high"):
    """Push a critical alert to RabbitMQ so the self-healing worker and notification service pick it up."""
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        params.socket_timeout = 3
        conn = pika.BlockingConnection(params)
        ch   = conn.channel()
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange='',
            routing_key=queue,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        conn.close()
        print(f"[Risk Engine] Published CRITICAL alert to RabbitMQ queue '{queue}'")
    except Exception as e:
        print(f"[Risk Engine] RabbitMQ publish failed: {e}")


# ── Full 24-feature ingest model ──────────────────────────────────────────────
class IngestEvent(BaseModel):
    # Core identity
    user_id:                   str
    action_type:               str

    # Temporal — auto-derived from server time if not supplied
    hour_of_day:               int   = -1
    is_weekend:                int   = -1

    # Location / identity
    ip_location_mismatch:      int   = 0
    geo_velocity_kmh:          float = 0.0
    unique_ips_last_24h:       int   = 1

    # Activity volume
    download_count_last_1h:    int   = 0
    upload_count_last_1h:      int   = 0
    bytes_transferred_last_1h: int   = 0

    # Auth signals
    failed_logins_last_1h:     int   = 0
    failed_logins_last_24h:    int   = 0

    # Session
    session_duration_min:      float = 1.0
    time_since_last_login_h:   float = 1.0

    # File
    file_size_bytes:           int   = 0
    file_type_risk_score:      float = 0.0

    # Network
    request_rate_per_min:      float = 1.0
    tor_exit_node:             int   = 0
    vpn_detected:              int   = 0
    user_agent_anomaly:        int   = 0

    # Legacy bulk-download flag
    is_bulk_download:          int   = 0


class AttackRequest(BaseModel):
    user_id: str = "attacker-sim-001"


@sio.event
async def connect(sid, environ):
    print("[Risk Engine] Dashboard connected via SocketIO:", sid)

@sio.event
async def disconnect(sid):
    print("[Risk Engine] Dashboard disconnected:", sid)


def compute_risk(score: float, geo: int, login_fail: int, api_spike: int) -> tuple[float, str]:
    """Composite risk scoring — weights match paper Section IV.C formula."""
    composite = score * 0.7 + geo * 0.15 + min(login_fail / 5.0, 1.0) * 0.1 + api_spike * 0.05
    composite  = min(composite, 1.0)
    if composite >= 0.85:
        level = "CRITICAL"
    elif composite >= 0.6:
        level = "HIGH"
    elif composite >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"
    return round(composite, 4), level


def do_self_heal_and_notify(user_id: str, anomaly_score: float, payload: dict):
    """Fire self-healing and push RabbitMQ alert (runs in background thread)."""
    alert = {
        "user_id":             user_id,
        "anomaly_score":       anomaly_score,
        "timestamp":           time.time(),
        "action":              payload.get("action_type", "unknown"),
        "geo_velocity_kmh":    payload.get("geo_velocity_kmh", 0),
        "ip_location_mismatch": payload.get("ip_location_mismatch", 0),
        "bytes_transferred":   payload.get("bytes_transferred_last_1h", 0),
        "risk_level":          "CRITICAL",
    }
    # Publish to risk.high → notification service (email + Socket.IO toast)
    publish_to_rabbitmq(alert, queue="risk.high")
    # Publish to risk.heal → self-healing worker (targeted key rotation)
    publish_to_rabbitmq(alert, queue="risk.heal")


@app.post("/ingest")
async def ingest_event(event: IngestEvent, background_tasks: BackgroundTasks):
    uid = event.user_id

    # ── Accumulate live Redis counters (1-hour rolling window) ───────────────
    live_dl    = redis_incr_window(f"dl_count:{uid}",   3600)
    live_ul    = redis_incr_window(f"ul_count:{uid}",   3600)
    live_bytes = redis_add_bytes(f"dl_bytes:{uid}", event.bytes_transferred_last_1h, 3600)

    # ── Auto-derive temporal features if caller did not supply them ───────────
    now     = datetime.now()
    hour    = event.hour_of_day if event.hour_of_day >= 0 else now.hour
    weekend = event.is_weekend  if event.is_weekend  >= 0 else (1 if now.weekday() >= 5 else 0)

    # ── Build full 24-feature payload for XGBoost anomaly service ────────────
    ml_payload = {
        # Identity
        "user_id":                  uid,
        "action_type":              event.action_type,
        # Temporal
        "hour_of_day":              hour,
        "is_weekend":               weekend,
        # Location
        "ip_location_mismatch":     event.ip_location_mismatch,
        "geo_velocity_kmh":         event.geo_velocity_kmh,
        "unique_ips_last_24h":      event.unique_ips_last_24h,
        # Volume — use live Redis counters for download/upload/bytes
        "download_count_last_1h":   live_dl,
        "upload_count_last_1h":     live_ul,
        "bytes_transferred_last_1h": live_bytes,
        # Auth
        "failed_logins_last_1h":    event.failed_logins_last_1h,
        "failed_logins_last_24h":   event.failed_logins_last_24h,
        # Session
        "session_duration_min":     event.session_duration_min,
        "time_since_last_login_h":  event.time_since_last_login_h,
        # File
        "file_size_bytes":          event.file_size_bytes,
        "file_type_risk_score":     event.file_type_risk_score,
        # Network
        "request_rate_per_min":     event.request_rate_per_min,
        "tor_exit_node":            event.tor_exit_node,
        "vpn_detected":             event.vpn_detected,
        "user_agent_anomaly":       event.user_agent_anomaly,
        # Bulk-download flag
        "is_bulk_download":         1 if live_dl >= 5 else event.is_bulk_download,
    }

    # ── Call XGBoost Anomaly ML Service ───────────────────────────────────────
    is_anomaly    = False
    anomaly_score = 0.05
    try:
        resp = requests.post(ANOMALY_SERVICE_URL, json=ml_payload, timeout=5)
        if resp.status_code == 200:
            ml_data       = resp.json()
            is_anomaly    = ml_data.get("is_anomaly",    False)
            anomaly_score = ml_data.get("anomaly_score", 0.05)
    except Exception as e:
        print(f"[Risk Engine] Anomaly service unreachable: {e}")

    # ── Composite Risk Evaluation ─────────────────────────────────────────────
    api_spike              = 1 if live_dl >= 5 else 0
    final_score, risk_level = compute_risk(
        score      = anomaly_score,
        geo        = event.ip_location_mismatch,
        login_fail = event.failed_logins_last_1h,
        api_spike  = api_spike,
    )

    result = {
        "user_id":              uid,
        "action":               event.action_type,
        "ml_anomaly_score":     anomaly_score,
        "is_anomaly":           is_anomaly,
        "final_composite_score": final_score,
        "risk_level":           risk_level,
        "live_download_count":  live_dl,
        "live_bytes_transferred": live_bytes,
    }

    # ── Broadcast to all connected dashboards ─────────────────────────────────
    await sio.emit('risk_update', result)

    # ── Trigger self-healing if CRITICAL anomaly confirmed ────────────────────
    if risk_level == "CRITICAL" and is_anomaly:
        await sio.emit('account_isolated', {
            "user_id":       uid,
            "reason":        "Harvest-Now-Decrypt-Later attack detected by XGBoost model",
            "anomaly_score": anomaly_score,
            "timestamp":     time.time(),
        })
        background_tasks.add_task(
            do_self_heal_and_notify,
            user_id       = uid,
            anomaly_score = anomaly_score,
            payload       = event.dict()
        )

    return result


@app.post("/inject-attack")
async def inject_attack(req: AttackRequest = None):
    """Frontend 'Inject Harvesting Attack' button — always fires CRITICAL + self-heal."""
    uid = (req.user_id if req else None) or "attacker-sim-001"
    alert = {
        "user_id":             uid,
        "anomaly_score":       0.98,
        "timestamp":           time.time(),
        "action":              "mass_download",
        "geo_velocity_kmh":    12000.0,
        "ip_location_mismatch": 1,
        "bytes_transferred":   5_500_000_000,
        "risk_level":          "CRITICAL",
    }
    await sio.emit('account_isolated', {
        "user_id":       uid,
        "reason":        "Harvest-Now-Decrypt-Later attack detected by XGBoost model",
        "anomaly_score": 0.98,
        "timestamp":     time.time(),
    })
    publish_to_rabbitmq(alert, queue="risk.high")
    publish_to_rabbitmq(alert, queue="risk.heal")
    return {"status": "attack_injected", "risk_level": "CRITICAL", "anomaly_score": 0.98, "user_id": uid}


@app.get("/health/live")
def liveness_probe():
    return {"status": "alive"}

@app.get("/health/ready")
def readiness_probe():
    return {"status": "ready"}

if __name__ == "__main__":
    uvicorn.run("src.main:sio_app", host="0.0.0.0", port=3005, reload=True)

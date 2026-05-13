"""
anomaly-service/src/main.py
============================
FastAPI service that:
  1. Loads the trained XGBoost model (xgb_anomaly_model.pkl) at startup
  2. Exposes POST /analyze  — accepts a rich event payload, runs ML inference,
     returns { anomaly_score, is_anomaly, attack_type_guess, confidence }
  3. Exposes GET  /health/live + /health/ready
  4. Exposes GET  /model/info — useful during demo / presentation

The feature vector built here MUST match exactly what train_model.py used.
We load model_meta.json to get the canonical feature list at runtime.
"""

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn, joblib, json, os, math, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("anomaly-service")

app = FastAPI(title="Anomaly Detection Service — ML Engine", version="2.0.0")

# ── Load model + feature metadata at startup ──────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "xgb_anomaly_model.pkl")
META_PATH  = os.path.join(BASE_DIR, "model_meta.json")

model      = None
model_meta = {}

try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        logger.info("✓ XGBoost model loaded successfully.")
    else:
        logger.warning("⚠  Model file not found — running in HEURISTIC fallback mode.")

    if os.path.exists(META_PATH):
        with open(META_PATH) as f:
            model_meta = json.load(f)
        logger.info(f"✓ Feature list loaded — {len(model_meta.get('feature_cols', []))} features.")
except Exception as e:
    logger.error(f"Error loading model: {e}")

# ── Request Schema ─────────────────────────────────────────────────────────────
class EventPayload(BaseModel):
    # Core Identity
    user_id:                   str
    action_type:               str   = "download"   # login|upload|download|list|delete|share

    # Temporal context
    hour_of_day:               int   = -1            # -1 = auto-derive from server time
    is_weekend:                int   = -1            # -1 = auto-derive

    # Location signals
    ip_location_mismatch:      int   = 0
    geo_velocity_kmh:          float = 0.0

    # Activity volume (last 1 hour)
    download_count_last_1h:    int   = 0
    upload_count_last_1h:      int   = 0
    bytes_transferred_last_1h: int   = 0

    # Auth signals
    failed_logins_last_1h:     int   = 0
    failed_logins_last_24h:    int   = 0

    # Session
    unique_ips_last_24h:       int   = 1
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


def _build_feature_df(event: EventPayload) -> pd.DataFrame:
    """Convert an EventPayload into the DataFrame the model expects."""
    import time as _time
    from datetime import datetime as _dt

    # Auto-derive temporal fields if caller didn't supply them
    now = _dt.now()
    hour    = event.hour_of_day if event.hour_of_day >= 0 else now.hour
    weekend = event.is_weekend  if event.is_weekend  >= 0 else (1 if now.weekday() >= 5 else 0)

    # Log-transform large byte features (must match training)
    log_bytes = math.log1p(event.bytes_transferred_last_1h)
    log_fsize = math.log1p(event.file_size_bytes)

    # One-hot encode action_type
    valid_actions = ['login', 'upload', 'download', 'list', 'delete', 'share']
    act = event.action_type.lower() if event.action_type.lower() in valid_actions else 'list'
    action_ohe = {f"act_{a}": (1 if a == act else 0) for a in valid_actions}

    row = {
        # Temporal
        "hour_of_day":               hour,
        "is_weekend":                weekend,
        # Location
        "ip_location_mismatch":      event.ip_location_mismatch,
        "geo_velocity_kmh":          event.geo_velocity_kmh,
        "unique_ips_last_24h":       event.unique_ips_last_24h,
        # Volume
        "download_count_last_1h":    event.download_count_last_1h,
        "upload_count_last_1h":      event.upload_count_last_1h,
        "log_bytes":                 log_bytes,
        "log_fsize":                 log_fsize,
        # Auth
        "failed_logins_last_1h":     event.failed_logins_last_1h,
        "failed_logins_last_24h":    event.failed_logins_last_24h,
        # Session
        "session_duration_min":      event.session_duration_min,
        "time_since_last_login_h":   event.time_since_last_login_h,
        # File risk
        "file_type_risk_score":      event.file_type_risk_score,
        # Network
        "request_rate_per_min":      event.request_rate_per_min,
        "tor_exit_node":             event.tor_exit_node,
        "vpn_detected":              event.vpn_detected,
        "user_agent_anomaly":        event.user_agent_anomaly,
        # One-hot action
        **action_ohe,
    }

    # Use canonical column order from model_meta (if loaded)
    feature_cols = model_meta.get("feature_cols", list(row.keys()))
    df = pd.DataFrame([row])[feature_cols]
    return df


def _heuristic_score(event: EventPayload) -> dict:
    """
    Simple rule-based fallback used when the ML model is not available.
    Useful in dev when the model hasn't been trained yet.
    """
    score = 0.0
    reasons = []

    if event.download_count_last_1h > 50:
        score += 0.4; reasons.append("bulk_download")
    if event.bytes_transferred_last_1h > 100_000_000:
        score += 0.3; reasons.append("large_transfer")
    if event.ip_location_mismatch:
        score += 0.15; reasons.append("ip_mismatch")
    if event.failed_logins_last_1h > 5:
        score += 0.25; reasons.append("brute_force")
    if event.tor_exit_node:
        score += 0.2;  reasons.append("tor_exit")
    if event.geo_velocity_kmh > 5000:
        score += 0.3;  reasons.append("impossible_travel")

    score = min(1.0, score)
    return {
        "anomaly_score":    round(score, 3),
        "is_anomaly":       score > 0.5,
        "attack_type_guess": reasons[0].upper() if reasons else "NORMAL",
        "confidence":       round(score, 3),
        "model_used":       "heuristic_fallback",
    }


def _guess_attack_type(event: EventPayload, proba: float) -> str:
    """Map feature patterns to a human-readable attack type label."""
    if proba < 0.5:
        return "NORMAL"
    if event.download_count_last_1h > 50 and event.bytes_transferred_last_1h > 50_000_000:
        return "HNDL"  # Harvest-Now-Decrypt-Later
    if event.failed_logins_last_1h > 5:
        return "BRUTE_FORCE"
    if event.failed_logins_last_24h > 20 and event.user_agent_anomaly:
        return "CRED_STUFFING"
    if event.bytes_transferred_last_1h > 50_000_000 and event.action_type in ('download', 'share'):
        return "EXFILTRATION"
    if event.tor_exit_node or event.geo_velocity_kmh > 5000:
        return "SUSPICIOUS_ORIGIN"
    return "ANOMALY"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health/live")
def liveness():
    return {"status": "alive"}

@app.get("/health/ready")
def readiness():
    return {"status": "ready", "model_loaded": model is not None}

@app.get("/model/info")
def model_info():
    """Expose model metadata — great for the demo presentation."""
    return {
        "model_type":  "XGBoost Binary Classifier",
        "version":     model_meta.get("version", "unknown"),
        "roc_auc":     model_meta.get("roc_auc", "N/A"),
        "features":    model_meta.get("feature_cols", []),
        "num_features": len(model_meta.get("feature_cols", [])),
        "attack_types_detected": [
            "HNDL (Harvest-Now-Decrypt-Later)",
            "BRUTE_FORCE",
            "CRED_STUFFING",
            "EXFILTRATION",
            "SUSPICIOUS_ORIGIN",
        ],
        "status": "loaded" if model else "heuristic_fallback",
    }

@app.post("/analyze")
def analyze_event(event: EventPayload):
    """
    Core ML inference endpoint.

    Returns:
      anomaly_score    : float  0.0 → 1.0  (higher = more suspicious)
      is_anomaly       : bool
      attack_type_guess: str    NORMAL | HNDL | BRUTE_FORCE | ...
      confidence       : float  model confidence in its prediction
      model_used       : str    xgboost | heuristic_fallback
    """
    if not model:
        return _heuristic_score(event)

    try:
        df    = _build_feature_df(event)
        proba = float(model.predict_proba(df)[0][1])   # probability of class=1 (attack)

        # Threshold at 0.5  (can tune lower to catch more FNs at cost of FPs)
        is_anomaly = proba >= 0.50

        attack_type = _guess_attack_type(event, proba)

        logger.info(
            f"[ML] user={event.user_id[:8]}… "
            f"action={event.action_type} "
            f"score={proba:.3f} "
            f"anomaly={is_anomaly} "
            f"type={attack_type}"
        )

        return {
            "anomaly_score":     round(proba, 4),
            "is_anomaly":        is_anomaly,
            "attack_type_guess": attack_type,
            "confidence":        round(max(proba, 1 - proba), 4),
            "model_used":        "xgboost",
        }

    except Exception as e:
        logger.error(f"Inference error: {e}")
        return _heuristic_score(event)


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=3004, reload=True)

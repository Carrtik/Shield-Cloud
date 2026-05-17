import os
import pika
import json
import time
import math
import threading
import logging
import numpy as np
import joblib
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Load XGBoost model at startup ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "xgb_anomaly_model.pkl")
META_PATH  = os.path.join(BASE_DIR, "model_meta.json")

xgb_model = joblib.load(MODEL_PATH)
with open(META_PATH) as f:
    model_meta = json.load(f)
FEATURE_COLS = model_meta["feature_cols"]
logger.info(f"✓ XGBoost model loaded in worker — {len(FEATURE_COLS)} features.")

# ── Queue config ──────────────────────────────────────────────────────────────
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
BATCH_SIZE   = int(os.environ.get("ANOMALY_BATCH_SIZE", 50))
WINDOW_MS    = int(os.environ.get("ANOMALY_BATCH_WINDOW_MS", 200)) / 1000.0

event_buffer = []
buffer_lock  = threading.Lock()


def build_feature_vector(event: dict) -> dict:
    """Convert a raw queue event into the 24-feature vector the model expects."""
    now = datetime.now()
    action = event.get("action", "list").lower()
    valid_actions = ['login', 'upload', 'download', 'list', 'delete', 'share']
    if action not in valid_actions:
        action = 'list'
    action_ohe = {f"act_{a}": (1 if a == action else 0) for a in valid_actions}
    bytes_val = event.get("bytes_transferred_last_1h", 0)
    fsize_val = event.get("file_size_bytes", 0)
    return {
        "hour_of_day":             event.get("hour_of_day", now.hour),
        "is_weekend":              event.get("is_weekend", 1 if now.weekday() >= 5 else 0),
        "ip_location_mismatch":    event.get("ip_location_mismatch", 0),
        "geo_velocity_kmh":        event.get("geo_velocity_kmh", 0.0),
        "unique_ips_last_24h":     event.get("unique_ips_last_24h", 1),
        "download_count_last_1h":  event.get("download_count_last_1h", 0),
        "upload_count_last_1h":    event.get("upload_count_last_1h", 0),
        "log_bytes":               math.log1p(bytes_val),
        "log_fsize":               math.log1p(fsize_val),
        "failed_logins_last_1h":   event.get("failed_logins_last_1h", 0),
        "failed_logins_last_24h":  event.get("failed_logins_last_24h", 0),
        "session_duration_min":    event.get("session_duration_min", 1.0),
        "time_since_last_login_h": event.get("time_since_last_login_h", 1.0),
        "file_type_risk_score":    event.get("file_type_risk_score", 0.0),
        "request_rate_per_min":    event.get("request_rate_per_min", 1.0),
        "tor_exit_node":           event.get("tor_exit_node", 0),
        "vpn_detected":            event.get("vpn_detected", 0),
        "user_agent_anomaly":      event.get("user_agent_anomaly", 0),
        **action_ohe,
    }


def process_batch(batch):
    """Run XGBoost inference on a batch of events from the queue."""
    logger.info(f"Processing batch of {len(batch)} events with XGBoost model")
    if not batch:
        return
    try:
        rows = [build_feature_vector(e) for e in batch]
        df   = pd.DataFrame(rows)[FEATURE_COLS]
        scores = xgb_model.predict_proba(df)[:, 1]
        logger.info(f"Batch scored — min={scores.min():.3f} max={scores.max():.3f}")
    except Exception as e:
        logger.error(f"XGBoost inference failed: {e}")
        scores = np.zeros(len(batch))
    publish_scores(batch, scores)


def flush_buffer():
    global event_buffer
    with buffer_lock:
        if len(event_buffer) > 0:
            batch        = event_buffer[:]
            event_buffer = []
            threading.Thread(target=process_batch, args=(batch,)).start()


def buffer_manager():
    """Background loop that flushes buffer on WINDOW_MS cadence."""
    while True:
        time.sleep(WINDOW_MS)
        flush_buffer()


def publish_scores(events, scores):
    """Publish XGBoost anomaly scores back to the anomaly.score queue."""
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel    = connection.channel()
        channel.queue_declare(queue='anomaly.score', durable=True)
        for event, score in zip(events, scores):
            payload = {
                "user":          event.get("user"),
                "action":        event.get("action"),
                "anomaly_score": float(score),
                "timestamp":     event.get("timestamp"),
            }
            channel.basic_publish(
                exchange='',
                routing_key='anomaly.score',
                body=json.dumps(payload),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish scores to RabbitMQ: {e}")


def start_consumer():
    """Start the batch buffer flusher and begin consuming user.activity events."""
    threading.Thread(target=buffer_manager, daemon=True).start()

    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        except Exception:
            logger.warning("Waiting for RabbitMQ...")
            time.sleep(2)

    channel = connection.channel()
    channel.queue_declare(queue='user.activity', durable=True)

    def callback(ch, method, properties, body):
        global event_buffer
        event = json.loads(body)
        with buffer_lock:
            event_buffer.append(event)
            if len(event_buffer) >= BATCH_SIZE:
                batch        = event_buffer[:]
                event_buffer = []
                threading.Thread(target=process_batch, args=(batch,)).start()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=BATCH_SIZE)
    channel.basic_consume(queue='user.activity', on_message_callback=callback)
    logger.info("✓ Anomaly worker ready — consuming user.activity queue.")
    channel.start_consuming()


if __name__ == "__main__":
    start_consumer()

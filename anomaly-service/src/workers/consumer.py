import os
import pika
import json
import time
import threading
import logging
import numpy as np

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
BATCH_SIZE = int(os.environ.get("ANOMALY_BATCH_SIZE", 50))
WINDOW_MS = int(os.environ.get("ANOMALY_BATCH_WINDOW_MS", 200)) / 1000.0

event_buffer = []
buffer_lock = threading.Lock()

def process_batch(batch):
    """Run LSTM inference on coalesced batch"""
    logger.info(f"Processing batch of {len(batch)} events")
    if not batch: return
    
    # Example logic: extract features and run model
    # For now, generate a random score to simulate inference
    scores = np.random.uniform(0.1, 0.9, len(batch))
    
    # Now publish anomaly scores to risk-engine
    publish_scores(batch, scores)

def flush_buffer():
    global event_buffer
    with buffer_lock:
        if len(event_buffer) > 0:
            batch = event_buffer[:]
            event_buffer = []
            # We process using a separate thread or asyncio if heavily async
            # Here we just process synchronously for the mock
            threading.Thread(target=process_batch, args=(batch,)).start()

def buffer_manager():
    """Background loop that flushes buffer if WINDOW_MS is reached"""
    while True:
        time.sleep(WINDOW_MS)
        flush_buffer()

def publish_scores(events, scores):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='anomaly.score', durable=True)
    
    for event, score in zip(events, scores):
        payload = {
            "user": event.get("user"),
            "action": event.get("action"),
            "anomaly_score": float(score),
            "timestamp": event.get("timestamp")
        }
        channel.basic_publish(
            exchange='',
            routing_key='anomaly.score',
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )
    connection.close()
    
def start_consumer():
    # Start the time-based flusher
    threading.Thread(target=buffer_manager, daemon=True).start()
    
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='user.activity', durable=True)

    def callback(ch, method, properties, body):
        global event_buffer
        event = json.loads(body)
        with buffer_lock:
            event_buffer.append(event)
            if len(event_buffer) >= BATCH_SIZE:
                # Flush immediately if batch size reached
                batch = event_buffer[:]
                event_buffer = []
                threading.Thread(target=process_batch, args=(batch,)).start()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=BATCH_SIZE)
    channel.basic_consume(queue='user.activity', on_message_callback=callback)
    
    logger.info('Waiting for user.activity messages.')
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()

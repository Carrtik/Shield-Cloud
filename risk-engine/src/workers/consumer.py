import os
import pika
import json
import logging
from src.scoring import evaluate_risk

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

def publish_high_risk(user_id, risk_score, risk_level):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='risk.high', durable=True)
    
    payload = {
        "user_id": user_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
    }
    channel.basic_publish(
        exchange='',
        routing_key='risk.high',
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()

def start_consumer():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='anomaly.score', durable=True)

    def callback(ch, method, properties, body):
        data = json.loads(body)
        user_id = data.get("user")
        anomaly_score = data.get("anomaly_score")
        
        # In a real app we fetch these from DB based on user_id
        # For simulation, we assume defaults
        normalized_login_failures = 0.0
        geo_change_flag = 0.0
        api_spike_score = 0.0
        device_change_flag = 0.0
        
        composite_risk, level = evaluate_risk(
            user_id, anomaly_score, normalized_login_failures,
            geo_change_flag, api_spike_score, device_change_flag
        )
        
        logger.info(f"User {user_id} evaluated with risk {composite_risk:.2f} ({level})")
        
        if level in ["HIGH", "CRITICAL"]:
            publish_high_risk(user_id, composite_risk, level)
            
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue='anomaly.score', on_message_callback=callback)
    
    logger.info('Waiting for anomaly.score messages.')
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()

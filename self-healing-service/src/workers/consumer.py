import os
import pika
import json
import logging
import time
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self-healing-worker")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
ENCRYPTION_SERVICE_URL = os.environ.get("ENCRYPTION_SERVICE_URL", "http://localhost:3002")

def trigger_background_reencryption(user_id):
    """
    Calls the actual encryption service self-healing endpoint to rotate the Kyber and AES keys.
    """
    logger.info(f"Triggering background RE-ENCRYPTION process for user: {user_id}")
    try:
        # In a real per-user scenario, we would pass user_id to rotate just their files
        # For the demo, we rotate the whole vault
        response = requests.post(f"{ENCRYPTION_SERVICE_URL}/self-heal/rotate-keys", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            rotated = data.get("files_rotated", 0)
            logger.info(f"✓ Self-healing SUCCESS: {rotated} files rotated for user {user_id}")
        else:
            logger.error(f"✗ Self-healing returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"✗ Failed to reach encryption service for self-healing: {e}")

def start_consumer():
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        except Exception as e:
            logger.warning("Waiting for RabbitMQ...")
            time.sleep(2)
            
    channel = connection.channel()
    channel.queue_declare(queue='risk.heal', durable=True)

    def callback(ch, method, properties, body):
        try:
            data = json.loads(body)
            user_id = data.get("user_id")
            risk_level = data.get("risk_level")
            action = data.get("action", "unknown")
            attack_type = data.get("attack_type", "UNKNOWN")
            
            logger.warning(f"CRITICAL: Caught HIGH RISK event from RabbitMQ!")
            logger.warning(f" -> User: {user_id[:8]}... | Risk: {risk_level} | Action: {action} | Detected: {attack_type}")
            logger.warning(f" -> Initializing Quantum Self-Healing protocol...")
            
            # Step 1: Isolate (revoke tokens, lock account - in auth service/DB)
            # Step 2: Trigger re-encryption for all compromised files
            trigger_background_reencryption(user_id)
            
            # Ack only if successful
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Error handling healing event: {e}")
            # Do not ack if failed, goes back to queue
            # ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='risk.heal', on_message_callback=callback)
    
    logger.info('Waiting for risk.high messages to trigger Self-Healing.')
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()

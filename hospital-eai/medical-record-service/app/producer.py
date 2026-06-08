import os
import pika
import time
import logging
import uuid

logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")


def get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
        connection_attempts=5,
        retry_delay=2
    )
    return pika.BlockingConnection(parameters)


def publish_event(message: str, queue_name: str):
    for attempt in range(5):
        try:
            connection = get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message.encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    message_id=str(uuid.uuid4()),
                    timestamp=int(time.time()),
                    headers={"x-retry-count": attempt}
                )
            )
            connection.close()
            logger.info(f"Published event to queue {queue_name}")
            return True
        except Exception as e:
            logger.warning(f"Publish attempt {attempt + 1}/5 failed: {e}")
            time.sleep(2 ** attempt)
    logger.error(f"Failed to publish event after 5 attempts")
    return False

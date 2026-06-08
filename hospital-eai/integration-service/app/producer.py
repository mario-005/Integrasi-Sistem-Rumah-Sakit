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


def publish_to_dlq(message: str, original_queue: str):
    dlq_name = f"dlq_{original_queue}"
    for attempt in range(3):
        try:
            connection = get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=dlq_name, durable=True)
            channel.basic_publish(
                exchange='',
                routing_key=dlq_name,
                body=message.encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    message_id=str(uuid.uuid4()),
                    timestamp=int(time.time()),
                    headers={"x-original-queue": original_queue, "x-dlq-reason": "processing_failed"}
                )
            )
            connection.close()
            logger.info(f"Message published to DLQ: {dlq_name}")
            return True
        except Exception as e:
            logger.warning(f"DLQ publish attempt {attempt + 1}/3 failed: {e}")
            time.sleep(2 ** attempt)
    return False

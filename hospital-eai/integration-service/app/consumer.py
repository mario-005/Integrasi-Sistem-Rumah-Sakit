import os
import json
import pika
import time
import logging
import threading
import httpx
from app.translator import json_to_xml, xml_to_json
from app.router import ContentBasedRouter
from app.producer import publish_to_dlq

logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

MEDICAL_RECORD_SERVICE_URL = os.getenv(
    "MEDICAL_RECORD_SERVICE_URL",
    "http://medical-record-service:8000"
)
PHARMACY_SERVICE_URL = os.getenv(
    "PHARMACY_SERVICE_URL",
    "http://pharmacy-service:8000"
)
BILLING_SERVICE_URL = os.getenv(
    "BILLING_SERVICE_URL",
    "http://billing-service:8000"
)


def process_patient_registered(event_data: dict, tracing_id: str):
    """
    PatientRegistered handler:
    1. Transform JSON -> XML (Message Translator)
    2. Send to Medical Record Service via HTTP
    """
    payload = event_data.get("payload", {})
    logger.info(f"[{tracing_id}] Processing PatientRegistered event")

    xml_data = json_to_xml(payload, "patient")
    logger.info(f"[{tracing_id}] JSON transformed to XML:\n{xml_data}")

    medical_record_data = {
        "patient_code": payload.get("patient_code"),
        "diagnosis": xml_data,
        "doctor_name": "System (Integration Service)",
        "prescription": ""
    }

    for attempt in range(3):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{MEDICAL_RECORD_SERVICE_URL}/medical-records",
                    json=medical_record_data
                )
                if response.status_code == 201:
                    logger.info(
                        f"[{tracing_id}] Patient data sent to Medical Record Service: "
                        f"{response.json()}"
                    )
                    return True
                else:
                    logger.warning(
                        f"[{tracing_id}] Medical Record Service responded "
                        f"{response.status_code}: {response.text}"
                    )
        except Exception as e:
            logger.warning(
                f"[{tracing_id}] Attempt {attempt + 1}/3 to Medical Record Service failed: {e}"
            )
            time.sleep(2 ** attempt)

    logger.error(f"[{tracing_id}] Failed to send patient data to Medical Record Service")
    return False


def process_prescription_created(event_data: dict, tracing_id: str):
    """
    PrescriptionCreated handler:
    1. Extract XML prescription data
    2. Transform XML -> JSON (Message Translator)
    3. Send to Pharmacy Service via HTTP
    """
    payload = event_data.get("payload", {})
    logger.info(f"[{tracing_id}] Processing PrescriptionCreated event")

    prescription_xml = payload.get("prescription_xml", "")
    if not prescription_xml:
        logger.error(f"[{tracing_id}] No prescription XML in payload")
        return False

    try:
        prescription_json = xml_to_json(prescription_xml)
        logger.info(f"[{tracing_id}] Prescription XML transformed to JSON:\n{prescription_json}")
    except Exception as e:
        logger.error(f"[{tracing_id}] Failed to convert prescription XML to JSON: {e}")
        return False

    med_data = prescription_json.get("prescription", {})
    medication = med_data.get("medication", "")

    if not medication:
        logger.warning(f"[{tracing_id}] No medication data in prescription XML")
        return False

    medicine_items = medication.split(",")
    all_success = True

    for item in medicine_items:
        item = item.strip()
        if ":" not in item:
            logger.warning(f"[{tracing_id}] Invalid medicine format: '{item}'")
            continue

        parts = item.split(":")
        if len(parts) != 2:
            logger.warning(f"[{tracing_id}] Invalid medicine format: '{item}'")
            continue

        medicine_code = parts[0].strip()
        try:
            quantity = int(parts[1].strip())
        except ValueError:
            logger.warning(f"[{tracing_id}] Invalid quantity in: '{item}'")
            continue

        for attempt in range(3):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{PHARMACY_SERVICE_URL}/prescriptions",
                        json={
                            "patient_code": payload.get("patient_code"),
                            "medicine_code": medicine_code,
                            "quantity": quantity
                        }
                    )
                    if response.status_code == 201:
                        logger.info(
                            f"[{tracing_id}] Prescription sent to Pharmacy Service: "
                            f"{response.json()}"
                        )
                        break
                    else:
                        logger.warning(
                            f"[{tracing_id}] Pharmacy Service responded "
                            f"{response.status_code}: {response.text}"
                        )
            except Exception as e:
                logger.warning(
                    f"[{tracing_id}] Attempt {attempt + 1}/3 to Pharmacy Service failed: {e}"
                )
                time.sleep(2 ** attempt)
        else:
            logger.error(
                f"[{tracing_id}] Failed to send {medicine_code} to Pharmacy Service"
            )
            all_success = False

    return all_success


def process_medicine_dispensed(event_data: dict, tracing_id: str):
    """
    MedicineDispensed handler:
    1. Extract cost data
    2. Send to Billing Service via HTTP
    """
    payload = event_data.get("payload", {})
    logger.info(f"[{tracing_id}] Processing MedicineDispensed event")

    for attempt in range(3):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{BILLING_SERVICE_URL}/invoices",
                    json={
                        "patient_code": payload.get("patient_code"),
                        "service_fee": 100000.0,
                        "medicine_fee": payload.get("total_cost", 0)
                    }
                )
                if response.status_code == 201:
                    logger.info(
                        f"[{tracing_id}] Invoice created at Billing Service: "
                        f"{response.json()}"
                    )
                    return True
                else:
                    logger.warning(
                        f"[{tracing_id}] Billing Service responded "
                        f"{response.status_code}: {response.text}"
                    )
        except Exception as e:
            logger.warning(
                f"[{tracing_id}] Attempt {attempt + 1}/3 to Billing Service failed: {e}"
            )
            time.sleep(2 ** attempt)

    logger.error(f"[{tracing_id}] Failed to create invoice at Billing Service")
    return False


def process_invoice_created(event_data: dict, tracing_id: str):
    """InvoiceCreated handler: log the invoice details."""
    payload = event_data.get("payload", {})
    logger.info(
        f"[{tracing_id}] Invoice created successfully:\n"
        f"  Patient: {payload.get('patient_code')}\n"
        f"  Service Fee: {payload.get('service_fee')}\n"
        f"  Medicine Fee: {payload.get('medicine_fee')}\n"
        f"  Total Fee: {payload.get('total_fee')}\n"
        f"  Status: {payload.get('status')}"
    )


def callback(ch, method, properties, body):
    tracing_id = "unknown"
    try:
        event_data = json.loads(body.decode())
        event_type = event_data.get("event_type", "unknown")
        tracing_id = event_data.get("tracing_id", "unknown")

        logger.info(f"[{tracing_id}] Received event '{event_type}' from queue '{method.routing_key}'")

        target = ContentBasedRouter.route(event_data)

        success = True
        if event_type == "PatientRegistered":
            success = process_patient_registered(event_data, tracing_id)
        elif event_type == "PrescriptionCreated":
            success = process_prescription_created(event_data, tracing_id)
        elif event_type == "MedicineDispensed":
            success = process_medicine_dispensed(event_data, tracing_id)
        elif event_type == "InvoiceCreated":
            process_invoice_created(event_data, tracing_id)
        else:
            logger.warning(f"[{tracing_id}] Unknown event type: {event_type}")
            success = False

        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"[{tracing_id}] Event '{event_type}' processed successfully")
        else:
            logger.error(f"[{tracing_id}] Event '{event_type}' processing failed")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            publish_to_dlq(body.decode(), method.routing_key)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        publish_to_dlq(body.decode(), method.routing_key)
    except Exception as e:
        logger.error(f"[{tracing_id}] Error processing message: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        publish_to_dlq(body.decode(), method.routing_key)


def start_consuming():
    for attempt in range(10):
        try:
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
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            queues = [
                "patient_registered_queue",
                "prescription_created_queue",
                "medicine_dispensed_queue",
                "invoice_created_queue"
            ]

            for queue in queues:
                channel.queue_declare(queue=queue, durable=True)
                channel.queue_declare(queue=f"dlq_{queue}", durable=True)
                channel.basic_consume(
                    queue=queue,
                    on_message_callback=callback,
                    auto_ack=False
                )
                logger.info(f"Listening on queue: {queue} (DLQ: dlq_{queue})")

            logger.info("Integration Service consumer started. Waiting for messages...")
            channel.start_consuming()
        except Exception as e:
            logger.warning(
                f"RabbitMQ connection attempt {attempt + 1}/10 failed: {e}"
            )
            time.sleep(5)

    logger.error("Failed to connect to RabbitMQ after 10 attempts")


def start_consumer_thread():
    thread = threading.Thread(target=start_consuming, daemon=True)
    thread.start()
    logger.info("Consumer thread started")
    return thread

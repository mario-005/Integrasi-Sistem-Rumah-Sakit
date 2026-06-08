import os
import logging
import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.consumer import start_consumer_thread

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Integration Service",
    description=(
        "Integration Service - Hospital EAI System\n\n"
        "Enterprise Integration Patterns implemented:\n"
        "1. Message Channel - RabbitMQ Queue\n"
        "2. Publish Subscribe - Event Broadcasting\n"
        "3. Message Endpoint - Producer dan Consumer\n"
        "4. Message Translator - JSON ↔ XML\n"
        "5. Content-Based Router - Routing berdasarkan event_type\n"
        "6. Canonical Data Model - Format standar event"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Hospital EAI System",
        "url": "http://localhost:8005/docs"
    }
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )


@app.on_event("startup")
async def startup():
    logger.info("Starting Integration Service...")
    start_consumer_thread()
    logger.info("Consumer thread started")


@app.get("/health",
         summary="Health check endpoint",
         description="Returns the health status of the Integration Service")
def health_check():
    return {
        "status": "healthy",
        "service": "integration-service",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/patterns",
         summary="Enterprise Integration Patterns",
         description="Returns the list of implemented Enterprise Integration Patterns")
def get_patterns():
    return {
        "patterns": [
            {
                "name": "Message Channel",
                "description": "RabbitMQ Queue sebagai saluran komunikasi antar service"
            },
            {
                "name": "Publish Subscribe",
                "description": "Event Broadcasting melalui RabbitMQ Exchange"
            },
            {
                "name": "Message Endpoint",
                "description": "Producer dan Consumer untuk mengirim dan menerima pesan"
            },
            {
                "name": "Message Translator",
                "description": "Transformasi format data JSON ↔ XML"
            },
            {
                "name": "Content-Based Router",
                "description": "Routing pesan berdasarkan event_type"
            },
            {
                "name": "Canonical Data Model",
                "description": "Format standar event dengan event_type, timestamp, tracing_id, payload"
            }
        ]
    }


@app.get("/queues",
         summary="RabbitMQ Queues",
         description="Returns the list of RabbitMQ queues used by the system")
def get_queues():
    return {
        "queues": [
            {"name": "patient_registered_queue", "dlq": "dlq_patient_registered_queue"},
            {"name": "prescription_created_queue", "dlq": "dlq_prescription_created_queue"},
            {"name": "medicine_dispensed_queue", "dlq": "dlq_medicine_dispensed_queue"},
            {"name": "invoice_created_queue", "dlq": "dlq_invoice_created_queue"}
        ]
    }

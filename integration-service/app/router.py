import json
import logging

logger = logging.getLogger(__name__)


class ContentBasedRouter:

    @staticmethod
    def route(event_data: dict) -> str:
        event_type = event_data.get("event_type", "")
        tracing_id = event_data.get("tracing_id", "unknown")
        logger.info(f"[{tracing_id}] Content-Based Router: routing event type '{event_type}'")

        routing_map = {
            "PatientRegistered": "medical_record_service",
            "PrescriptionCreated": "pharmacy_service",
            "MedicineDispensed": "billing_service",
            "InvoiceCreated": "logging"
        }

        target = routing_map.get(event_type, "unknown")
        if target == "unknown":
            logger.warning(f"[{tracing_id}] Unknown event type '{event_type}', routing to DLQ")
        else:
            logger.info(f"[{tracing_id}] Routed '{event_type}' -> {target}")

        return target

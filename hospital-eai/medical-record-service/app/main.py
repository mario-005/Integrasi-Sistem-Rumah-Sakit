import json
import os
import logging
from typing import List
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models, schemas, database, producer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Medical Record Service",
    description="Medical Record Service - Hospital EAI System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Hospital EAI System",
        "url": "http://localhost:8002/docs"
    }
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )


@app.post("/medical-records", response_model=schemas.MedicalRecordResponse, status_code=201,
          summary="Create a medical record",
          description="Creates a new medical record with diagnosis and publishes PrescriptionCreated event to RabbitMQ")
def create_medical_record(record: schemas.MedicalRecordCreate, db: Session = Depends(database.get_db)):
    db_record = models.MedicalRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    prescription_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<prescription>
    <patient_code>{db_record.patient_code}</patient_code>
    <diagnosis><![CDATA[{db_record.diagnosis}]]></diagnosis>
    <doctor_name>{db_record.doctor_name}</doctor_name>
    <medication><![CDATA[{db_record.prescription or ''}]]></medication>
    <created_at>{db_record.created_at.isoformat()}</created_at>
</prescription>"""

    event = {
        "event_type": "PrescriptionCreated",
        "timestamp": datetime.utcnow().isoformat(),
        "tracing_id": f"med-{db_record.id}-{int(datetime.utcnow().timestamp())}",
        "payload": {
            "id": db_record.id,
            "patient_code": db_record.patient_code,
            "diagnosis": db_record.diagnosis,
            "doctor_name": db_record.doctor_name,
            "prescription_xml": prescription_xml,
            "created_at": db_record.created_at.isoformat()
        }
    }

    queue_name = os.getenv("PRESCRIPTION_CREATED_QUEUE", "prescription_created_queue")
    producer.publish_event(json.dumps(event), queue_name)
    logger.info(f"Published PrescriptionCreated event for patient {db_record.patient_code}")

    return db_record


@app.get("/medical-records", response_model=List[schemas.MedicalRecordResponse],
         summary="Get all medical records",
         description="Returns a list of all medical records")
def get_medical_records(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    records = db.query(models.MedicalRecord).offset(skip).limit(limit).all()
    return records


@app.get("/medical-records/{id}", response_model=schemas.MedicalRecordResponse,
         summary="Get medical record by ID",
         description="Returns a single medical record by its database ID")
def get_medical_record(id: int, db: Session = Depends(database.get_db)):
    record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    return record


@app.get("/health",
         summary="Health check endpoint",
         description="Returns the health status of the Medical Record Service")
def health_check():
    return {
        "status": "healthy",
        "service": "medical-record-service",
        "timestamp": datetime.utcnow().isoformat()
    }

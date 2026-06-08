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
    title="Registration Service",
    description="Patient Registration Service - Hospital EAI System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Hospital EAI System",
        "url": "http://localhost:8001/docs"
    }
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )


@app.post("/patients", response_model=schemas.PatientResponse, status_code=201,
          summary="Register a new patient",
          description="Creates a new patient record and publishes PatientRegistered event to RabbitMQ")
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(database.get_db)):
    existing = db.query(models.Patient).filter(
        models.Patient.patient_code == patient.patient_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient code already exists")

    db_patient = models.Patient(**patient.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)

    event = {
        "event_type": "PatientRegistered",
        "timestamp": datetime.utcnow().isoformat(),
        "tracing_id": f"reg-{db_patient.id}-{int(datetime.utcnow().timestamp())}",
        "payload": {
            "id": db_patient.id,
            "patient_code": db_patient.patient_code,
            "name": db_patient.name,
            "gender": db_patient.gender,
            "birth_date": str(db_patient.birth_date) if db_patient.birth_date else None,
            "address": db_patient.address
        }
    }

    queue_name = os.getenv("PATIENT_REGISTERED_QUEUE", "patient_registered_queue")
    producer.publish_event(json.dumps(event), queue_name)
    logger.info(f"Published PatientRegistered event for patient {db_patient.patient_code}")

    return db_patient


@app.get("/patients", response_model=List[schemas.PatientResponse],
         summary="Get all patients",
         description="Returns a list of all registered patients")
def get_patients(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    patients = db.query(models.Patient).offset(skip).limit(limit).all()
    return patients


@app.get("/patients/{id}", response_model=schemas.PatientResponse,
         summary="Get patient by ID",
         description="Returns a single patient by their database ID")
def get_patient(id: int, db: Session = Depends(database.get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get("/health",
         summary="Health check endpoint",
         description="Returns the health status of the Registration Service")
def health_check():
    return {
        "status": "healthy",
        "service": "registration-service",
        "timestamp": datetime.utcnow().isoformat()
    }

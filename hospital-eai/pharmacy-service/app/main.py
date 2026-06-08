import json
import os
import logging
from typing import List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from bson import ObjectId

from app import database, schemas, producer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pharmacy Service",
    description="Pharmacy Service - Hospital EAI System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Hospital EAI System",
        "url": "http://localhost:8003/docs"
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
def seed_medicines():
    db = database.get_db()
    if db["medicines"].count_documents({}) == 0:
        default_medicines = [
            {"medicine_code": "MED001", "medicine_name": "Paracetamol", "stock": 100, "price": 15000.0},
            {"medicine_code": "MED002", "medicine_name": "Amoxicillin", "stock": 50, "price": 25000.0},
            {"medicine_code": "MED003", "medicine_name": "Ibuprofen", "stock": 80, "price": 20000.0},
            {"medicine_code": "MED004", "medicine_name": "Omeprazole", "stock": 60, "price": 30000.0},
            {"medicine_code": "MED005", "medicine_name": "Cetirizine", "stock": 90, "price": 12000.0},
        ]
        db["medicines"].insert_many(default_medicines)
        logger.info("Seeded default medicines")


@app.post("/prescriptions", response_model=schemas.PrescriptionResponse, status_code=201,
          summary="Create a prescription",
          description="Creates a new prescription, reduces medicine stock, and publishes MedicineDispensed event")
def create_prescription(prescription: schemas.PrescriptionCreate):
    db = database.get_db()

    medicine = db["medicines"].find_one({"medicine_code": prescription.medicine_code})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    if medicine["stock"] < prescription.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    prescription_data = {
        "patient_code": prescription.patient_code,
        "medicine_code": prescription.medicine_code,
        "quantity": prescription.quantity,
        "created_at": datetime.utcnow()
    }
    result = db["prescriptions"].insert_one(prescription_data)

    db["medicines"].update_one(
        {"_id": medicine["_id"]},
        {"$inc": {"stock": -prescription.quantity}}
    )

    created = db["prescriptions"].find_one({"_id": result.inserted_id})

    total_cost = medicine["price"] * prescription.quantity
    event = {
        "event_type": "MedicineDispensed",
        "timestamp": datetime.utcnow().isoformat(),
        "tracing_id": f"pha-{str(created['_id'])}-{int(datetime.utcnow().timestamp())}",
        "payload": {
            "id": str(created["_id"]),
            "patient_code": created["patient_code"],
            "medicine_code": created["medicine_code"],
            "medicine_name": medicine["medicine_name"],
            "quantity": created["quantity"],
            "total_cost": total_cost
        }
    }

    queue_name = os.getenv("MEDICINE_DISPENSED_QUEUE", "medicine_dispensed_queue")
    producer.publish_event(json.dumps(event), queue_name)
    logger.info(f"Published MedicineDispensed event for patient {created['patient_code']}")

    return {
        "id": str(created["_id"]),
        "patient_code": created["patient_code"],
        "medicine_code": created["medicine_code"],
        "quantity": created["quantity"],
        "created_at": created["created_at"]
    }


@app.post("/medicines", response_model=schemas.MedicineResponse, status_code=201,
          summary="Add a new medicine",
          description="Adds a new medicine to the pharmacy inventory")
def create_medicine(medicine: schemas.MedicineCreate):
    db = database.get_db()
    existing = db["medicines"].find_one({"medicine_code": medicine.medicine_code})
    if existing:
        raise HTTPException(status_code=400, detail="Medicine code already exists")

    result = db["medicines"].insert_one(medicine.model_dump())
    created = db["medicines"].find_one({"_id": result.inserted_id})
    return {
        "id": str(created["_id"]),
        "medicine_code": created["medicine_code"],
        "medicine_name": created["medicine_name"],
        "stock": created["stock"],
        "price": created["price"]
    }


@app.get("/medicines", response_model=List[schemas.MedicineResponse],
         summary="Get all medicines",
         description="Returns a list of all available medicines")
def get_medicines():
    db = database.get_db()
    medicines = db["medicines"].find()
    result = []
    for med in medicines:
        result.append({
            "id": str(med["_id"]),
            "medicine_code": med["medicine_code"],
            "medicine_name": med["medicine_name"],
            "stock": med["stock"],
            "price": med["price"]
        })
    return result


@app.put("/medicines/{id}", response_model=schemas.MedicineResponse,
         summary="Update medicine",
         description="Updates medicine stock and/or price by MongoDB ObjectId")
def update_medicine(id: str, medicine: schemas.MedicineUpdate):
    db = database.get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    existing = db["medicines"].find_one({"_id": ObjectId(id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Medicine not found")

    update_data = {k: v for k, v in medicine.model_dump().items() if v is not None}
    if update_data:
        db["medicines"].update_one({"_id": ObjectId(id)}, {"$set": update_data})

    updated = db["medicines"].find_one({"_id": ObjectId(id)})
    return {
        "id": str(updated["_id"]),
        "medicine_code": updated["medicine_code"],
        "medicine_name": updated["medicine_name"],
        "stock": updated["stock"],
        "price": updated["price"]
    }


@app.get("/health",
         summary="Health check endpoint",
         description="Returns the health status of the Pharmacy Service")
def health_check():
    return {
        "status": "healthy",
        "service": "pharmacy-service",
        "timestamp": datetime.utcnow().isoformat()
    }

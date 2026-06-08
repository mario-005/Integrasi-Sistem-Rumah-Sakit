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
    title="Billing Service",
    description="Billing Service - Hospital EAI System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Hospital EAI System",
        "url": "http://localhost:8004/docs"
    }
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )


@app.post("/invoices", response_model=schemas.InvoiceResponse, status_code=201,
          summary="Create an invoice",
          description="Creates a new invoice with calculated total fee and publishes InvoiceCreated event")
def create_invoice(invoice: schemas.InvoiceCreate, db: Session = Depends(database.get_db)):
    db_invoice = models.Invoice(
        patient_code=invoice.patient_code,
        service_fee=invoice.service_fee,
        medicine_fee=invoice.medicine_fee,
        total_fee=invoice.service_fee + invoice.medicine_fee,
        status="pending"
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    event = {
        "event_type": "InvoiceCreated",
        "timestamp": datetime.utcnow().isoformat(),
        "tracing_id": f"bil-{db_invoice.id}-{int(datetime.utcnow().timestamp())}",
        "payload": {
            "id": db_invoice.id,
            "patient_code": db_invoice.patient_code,
            "service_fee": db_invoice.service_fee,
            "medicine_fee": db_invoice.medicine_fee,
            "total_fee": db_invoice.total_fee,
            "status": db_invoice.status
        }
    }

    queue_name = os.getenv("INVOICE_CREATED_QUEUE", "invoice_created_queue")
    producer.publish_event(json.dumps(event), queue_name)
    logger.info(f"Published InvoiceCreated event for patient {db_invoice.patient_code}")

    return db_invoice


@app.get("/invoices", response_model=List[schemas.InvoiceResponse],
         summary="Get all invoices",
         description="Returns a list of all invoices")
def get_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    invoices = db.query(models.Invoice).offset(skip).limit(limit).all()
    return invoices


@app.get("/invoices/{id}", response_model=schemas.InvoiceResponse,
         summary="Get invoice by ID",
         description="Returns a single invoice by its database ID")
def get_invoice(id: int, db: Session = Depends(database.get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.get("/health",
         summary="Health check endpoint",
         description="Returns the health status of the Billing Service")
def health_check():
    return {
        "status": "healthy",
        "service": "billing-service",
        "timestamp": datetime.utcnow().isoformat()
    }

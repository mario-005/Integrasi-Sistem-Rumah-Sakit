from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InvoiceCreate(BaseModel):
    patient_code: str
    service_fee: float = 0.0
    medicine_fee: float = 0.0


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    patient_code: str
    service_fee: float
    medicine_fee: float
    total_fee: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

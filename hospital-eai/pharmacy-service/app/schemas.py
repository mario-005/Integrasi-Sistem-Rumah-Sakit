from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MedicineCreate(BaseModel):
    medicine_code: str
    medicine_name: str
    stock: int
    price: float


class MedicineResponse(BaseModel):
    id: str
    medicine_code: str
    medicine_name: str
    stock: int
    price: float


class MedicineUpdate(BaseModel):
    stock: Optional[int] = None
    price: Optional[float] = None


class PrescriptionCreate(BaseModel):
    patient_code: str
    medicine_code: str
    quantity: int


class PrescriptionResponse(BaseModel):
    id: str
    patient_code: str
    medicine_code: str
    quantity: int
    created_at: datetime

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class PatientCreate(BaseModel):
    patient_code: str
    name: str
    gender: str
    birth_date: Optional[date] = None
    address: Optional[str] = None


class PatientResponse(BaseModel):
    id: int
    patient_code: str
    name: str
    gender: str
    birth_date: Optional[date] = None
    address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

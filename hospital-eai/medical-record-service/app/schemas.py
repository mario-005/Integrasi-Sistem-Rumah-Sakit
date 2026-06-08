from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MedicalRecordCreate(BaseModel):
    patient_code: str
    diagnosis: str
    doctor_name: str
    prescription: Optional[str] = None


class MedicalRecordResponse(BaseModel):
    id: int
    patient_code: str
    diagnosis: str
    doctor_name: str
    prescription: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

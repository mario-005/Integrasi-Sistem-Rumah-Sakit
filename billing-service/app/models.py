from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_code = Column(String(20), index=True, nullable=False)
    service_fee = Column(Float, default=0.0, nullable=False)
    medicine_fee = Column(Float, default=0.0, nullable=False)
    total_fee = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

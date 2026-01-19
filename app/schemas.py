import datetime
from pydantic import BaseModel
from typing import Optional
from enum import Enum

# These match your Database Enums
class PriorityLevel(int, Enum):
    NORMAL = 1
    URGENT = 5
    CRITICAL = 10

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str  # "doctor", "receptionist", "patient"

class PatientCreate(BaseModel):
    # Receptionist just needs to enter these 3 things
    username: str
    full_name: str
    severity: PriorityLevel 

class QueueResponse(BaseModel):
    # What the frontend will receive back
    patient_name: str
    priority_score: float
    status: str
    
    class Config:
        from_attributes = True # Crucial for SQLAlchemy compatibility

class HospitalCreate(BaseModel):
    name: str
    location: str
    contact_number: str
    icu_bed_count: int
    general_bed_count: int


class AdminCreate(BaseModel):
    username: str
    password: str
    full_name: str
    hospital_id: int

class AdmitRequest(BaseModel):
    queue_id: int
    bed_type: str 

class VisitRequest(BaseModel):
    patient_id: int
    visit_date: datetime.datetime
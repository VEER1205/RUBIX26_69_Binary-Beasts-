from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQL_Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

# --- Enums (Strict Choices) ---
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"

class BedType(str, enum.Enum):
    ICU = "ICU"
    GENERAL = "GENERAL"
    VENTILATOR = "VENTILATOR"

class BedStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"

class PriorityLevel(enum.IntEnum):
    NORMAL = 1
    URGENT = 5
    CRITICAL = 10

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"       
    HOSPITAL_ADMIN = "hospital_admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"
    AMBULANCE = "ambulance"


# --- Database Tables ---

class InventoryItem(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(100))
    category = Column(String(50)) # e.g., Medicine, Equipment
    quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10) # Automation Trigger
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))

    hospital = relationship("Hospital", back_populates="inventory")



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    role = Column(SQL_Enum(UserRole))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    
    # NEW: For Patient's Next Visit (Simple approach)
    next_visit_date = Column(DateTime, nullable=True)

    hospital = relationship("Hospital", back_populates="staff")
    queue_entry = relationship("OpdQueue", back_populates="patient", uselist=False)

class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    location = Column(String(255)) 
    contact_number = Column(String(20))
    
    staff = relationship("User", back_populates="hospital")
    beds = relationship("Bed", back_populates="hospital")
    queue = relationship("OpdQueue", back_populates="hospital")
    inventory = relationship("InventoryItem", back_populates="hospital")

class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    bed_number = Column(String(10)) # e.g., "ICU-01"
    
    bed_type = Column(SQL_Enum(BedType), default=BedType.GENERAL)
    status = Column(SQL_Enum(BedStatus), default=BedStatus.AVAILABLE)
    
    current_patient_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    hospital = relationship("Hospital", back_populates="beds")

class OpdQueue(Base):
    __tablename__ = "opd_queue"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    patient_id = Column(Integer, ForeignKey("users.id"))
    
    check_in_time = Column(DateTime, default=datetime.utcnow)
    severity = Column(SQL_Enum(PriorityLevel), default=PriorityLevel.NORMAL)
    
    priority_score = Column(Float, index=True, default=0.0)
    
    status = Column(String(20), default="WAITING") 

    hospital = relationship("Hospital", back_populates="queue")
    patient = relationship("User", back_populates="queue_entry")


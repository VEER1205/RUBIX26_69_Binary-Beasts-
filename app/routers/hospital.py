from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from ..schemas import AdmitRequest, VisitRequest
from .. import database, schemas, crud, models
from .auth import get_current_user 
from .dashboard import public_manager

router = APIRouter(
    prefix="/hospital",
    tags=["Hospital Operations"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
get_db = database.get_db

# --- Request Models ---


# ==========================================
# 1. RECEPTIONIST: Register Patient
# ==========================================
@router.post("/register-patient")
async def register_patient_and_queue(
    patient_data: schemas.PatientCreate, 
    hospital_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.RECEPTIONIST:
        raise HTTPException(status_code=403, detail="Only Receptionists can register patients")

    # Check if patient exists
    existing = await db.execute(select(models.User).where(models.User.username == patient_data.username))
    patient = existing.scalar_one_or_none()

    if not patient:
        # Create new patient user
        user_in = schemas.UserCreate(
            username=patient_data.username,
            password="defaultpassword123", 
            full_name=patient_data.full_name,
            role="patient"
        )
        patient = await crud.create_user(db, user_in)

    # Add to Queue
    await crud.add_patient_to_queue(
        db, 
        patient_id=patient.id, 
        hospital_id=hospital_id, 
        severity=patient_data.severity
    )
    
    return {"message": "Patient added to Queue", "queue_position": patient_data.severity * 1000}

# ==========================================
# 2. STAFF: View Queue
# ==========================================
@router.get("/{hospital_id}/queue")
async def view_queue(
    hospital_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Security: Ensure user belongs to this hospital (optional strict check)
    if current_user.role not in [models.UserRole.DOCTOR, models.UserRole.RECEPTIONIST]:
        raise HTTPException(status_code=403, detail="Access Denied")

    queue = await crud.get_hospital_queue(db, hospital_id)
    return queue

# ==========================================
# 3. DOCTOR: Admit Patient
# ==========================================
@router.post("/admit-patient")
async def admit_patient(
    request: AdmitRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only Doctors can admit patients")

    # Get Queue Entry
    q_result = await db.execute(select(models.OpdQueue).where(models.OpdQueue.id == request.queue_id))
    queue_entry = q_result.scalar_one_or_none()
    
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    # Find Available Bed
    b_result = await db.execute(
        select(models.Bed)
        .where(models.Bed.hospital_id == queue_entry.hospital_id)
        .where(models.Bed.bed_type == request.bed_type)
        .where(models.Bed.status == "AVAILABLE")
        .limit(1)
    )
    bed = b_result.scalar_one_or_none()
    
    if not bed:
        raise HTTPException(status_code=400, detail=f"No {request.bed_type} beds available!")

    # Update Status
    bed.status = "OCCUPIED"
    bed.current_patient_id = queue_entry.patient_id
    queue_entry.status = "COMPLETED"
    
    await db.commit()
    await public_manager.broadcast("UPDATE") # Update Public Dashboard
    
    return {"message": f"Patient admitted to Bed {bed.bed_number}"}

# ==========================================
# 4. DOCTOR: Discharge Patient
# ==========================================
@router.post("/discharge-patient/{bed_id}")
async def discharge_patient(
    bed_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only Doctors can discharge")

    bed = await db.get(models.Bed, bed_id)
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
        
    bed.status = "AVAILABLE"
    bed.current_patient_id = None
    
    await db.commit()
    await public_manager.broadcast("UPDATE") # Update Public Dashboard
    
    return {"message": f"Bed {bed.bed_number} is now AVAILABLE"}

# ==========================================
# 5. DOCTOR: Set Next Visit Date
# ==========================================
@router.post("/doctor/set-visit")
async def set_next_visit(
    request: VisitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only Doctors can set visits")
        
    patient = await db.get(models.User, request.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    patient.next_visit_date = request.visit_date
    await db.commit()
    return {"message": f"Next visit set for {request.visit_date}"}

# ==========================================
# 6. HOSPITAL ADMIN: Add Staff (Doctor/Receptionist)
# ==========================================
@router.post("/staff/add")
async def add_staff(
    user_data: schemas.UserCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.HOSPITAL_ADMIN:
        raise HTTPException(status_code=403, detail="Only Hospital Admins can add staff")

    new_user = models.User(
        username=user_data.username,
        hashed_password=pwd_context.hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role, 
        hospital_id=current_user.hospital_id # Assign to THIS admin's hospital
    )
    db.add(new_user)
    await db.commit()
    return {"message": f"Staff {user_data.username} added"}

# ==========================================
# 7. PUBLIC/HOME: Get Doctors List
# ==========================================
@router.get("/{hospital_id}/doctors")
async def get_hospital_doctors(hospital_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.User)
        .where(models.User.hospital_id == hospital_id)
        .where(models.User.role == models.UserRole.DOCTOR)
    )
    doctors = result.scalars().all()
    return [{"name": d.full_name, "id": d.id} for d in doctors]
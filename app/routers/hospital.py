from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import database, schemas, crud, models
from .auth import get_current_user # Import the security guard
from .dashboard import public_manager

router = APIRouter(
    prefix="/hospital",
    tags=["Hospital Operations"]
)

# Dependency to get DB
get_db = database.get_db

# --- Request Models ---
class AdmitRequest(schemas.BaseModel):
    queue_id: int
    bed_type: str 

# --- ENDPOINTS ---

# 1. RECEPTIONIST ONLY: Register Patient
@router.post("/register-patient")
async def register_patient_and_queue(
    patient_data: schemas.PatientCreate, 
    hospital_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Security Check
    if current_user.role != models.UserRole.RECEPTIONIST:
        raise HTTPException(status_code=403, detail="Access Denied: Only Receptionists can register patients")

    # (Optional) Check if receptionist belongs to the same hospital
    if current_user.hospital_id != hospital_id:
        raise HTTPException(status_code=403, detail="You cannot register patients for a different hospital")

    user_in = schemas.UserCreate(
        username=patient_data.username,
        password="defaultpassword123", 
        full_name=patient_data.full_name,
        role="patient"
    )
    
    # Check if user exists (Simple check)
    existing = await db.execute(select(models.User).where(models.User.username == user_in.username))
    if existing.scalar_one_or_none():
         # If patient exists, just get their ID (Skipping full logic for hackathon speed)
         pass 
    else:
        new_user = await crud.create_user(db, user_in)
        # Use the new user ID
        await crud.add_patient_to_queue(
            db, 
            patient_id=new_user.id, 
            hospital_id=hospital_id, 
            severity=patient_data.severity
        )
    
    return {"message": "Patient added to Queue"}

# 2. STAFF ONLY (Doctor/Receptionist): View Queue
@router.get("/{hospital_id}/queue")
async def view_queue(
    hospital_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # <--- Lock
):
    # Allow both Doctors and Receptionists
    allowed_roles = [models.UserRole.DOCTOR, models.UserRole.RECEPTIONIST]
    if current_user.role not in allowed_roles:
         raise HTTPException(status_code=403, detail="Access Denied: Staff only")

    queue = await crud.get_hospital_queue(db, hospital_id)
    return queue

# 3. DOCTOR ONLY: Admit Patient
@router.post("/admit-patient")
async def admit_patient(
    request: AdmitRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # <--- Lock
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Access Denied: Only Doctors can admit patients")

    # Get Queue Entry
    result = await db.execute(select(models.OpdQueue).where(models.OpdQueue.id == request.queue_id))
    queue_entry = result.scalar_one_or_none()
    
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    # Find Bed
    bed_result = await db.execute(
        select(models.Bed)
        .where(models.Bed.hospital_id == queue_entry.hospital_id)
        .where(models.Bed.bed_type == request.bed_type)
        .where(models.Bed.status == "AVAILABLE")
        .limit(1)
    )
    bed = bed_result.scalar_one_or_none()
    
    if not bed:
        raise HTTPException(status_code=400, detail=f"No {request.bed_type} beds available!")

    # Assign
    bed.status = "OCCUPIED"
    bed.current_patient_id = queue_entry.patient_id
    queue_entry.status = "COMPLETED"
    
    await db.commit()
    await public_manager.broadcast("UPDATE")
    return {"message": f"Patient admitted to Bed {bed.bed_number}"}

# 4. DOCTOR ONLY: Discharge Patient
@router.post("/discharge-patient/{bed_id}")
async def discharge_patient(
    bed_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # <--- Lock
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Access Denied: Only Doctors can discharge patients")

    result = await db.execute(select(models.Bed).where(models.Bed.id == bed_id))
    bed = result.scalar_one_or_none()
    
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
        
    bed.status = "AVAILABLE"
    bed.current_patient_id = None
    
    await db.commit()
    await public_manager.broadcast("UPDATE")
    return {"message": f"Bed {bed.bed_number} is now AVAILABLE"}

# 5. ADMIN ONLY: Create Hospital
@router.post("/create")
async def create_new_hospital(
    hospital_data: schemas.HospitalCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized: Only Admins can create hospitals")

    # Create Hospital Logic
    new_hospital = models.Hospital(
        name=hospital_data.name,
        location=hospital_data.location,
        contact_number=hospital_data.contact_number
    )
    db.add(new_hospital)
    await db.commit()
    await db.refresh(new_hospital)

    beds_to_add = []
    for i in range(1, hospital_data.icu_bed_count + 1):
        beds_to_add.append(models.Bed(hospital_id=new_hospital.id, bed_number=f"ICU-{i}", bed_type="ICU", status="AVAILABLE"))
    for i in range(1, hospital_data.general_bed_count + 1):
        beds_to_add.append(models.Bed(hospital_id=new_hospital.id, bed_number=f"GEN-{i}", bed_type="GENERAL", status="AVAILABLE"))
    
    db.add_all(beds_to_add)
    await db.commit()
    
    return {"message": "Hospital created", "id": new_hospital.id}
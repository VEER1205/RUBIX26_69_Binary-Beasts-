from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from ..schemas import AdmitRequest, VisitRequest, TransferRequest
from .. import database, schemas, crud, models
from .auth import get_current_user 
from ..websocket_manager import manager

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
    await manager.broadcast("UPDATE") # Update Public Dashboard
    
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
    await manager.broadcast("UPDATE") # Update Public Dashboard
    
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

# ... (existing imports)

# --- 8. GET ALL STAFF (For Hospital Admin Dashboard) ---
@router.get("/staff/all")
async def get_all_my_staff(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.HOSPITAL_ADMIN:
        raise HTTPException(status_code=403, detail="Access Denied")

    # Fetch Doctors and Receptionists belonging to this Admin's Hospital
    result = await db.execute(
        select(models.User)
        .where(models.User.hospital_id == current_user.hospital_id)
        .where(models.User.role.in_([models.UserRole.DOCTOR, models.UserRole.RECEPTIONIST]))
    )
    staff = result.scalars().all()
    return staff

# --- 9. REMOVE STAFF MEMBER ---
@router.delete("/staff/{user_id}")
async def remove_staff(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.HOSPITAL_ADMIN:
        raise HTTPException(status_code=403, detail="Access Denied")

    # Fetch User
    staff_member = await db.get(models.User, user_id)
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Security: Ensure Admin owns this staff member
    if staff_member.hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=403, detail="You cannot remove staff from other hospitals")

    await db.delete(staff_member)
    await db.commit()
    return {"message": "Staff member removed successfully"}


# --- 10. GET HOSPITAL BEDS (To display in Doctor Dashboard) ---
@router.get("/{hospital_id}/beds")
async def get_hospital_beds(
    hospital_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Fetch all beds for this hospital
    result = await db.execute(
        select(models.Bed)
        .where(models.Bed.hospital_id == hospital_id)
        .order_by(models.Bed.bed_number)
    )
    beds = result.scalars().all()
    return beds

# --- 11. TRANSFER PATIENT (Shift Bed) ---


@router.post("/transfer-patient")
async def transfer_patient(
    req: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only Doctors can transfer")

    # 1. Get Current Bed
    current_bed = await db.get(models.Bed, req.current_bed_id)
    if not current_bed or current_bed.status != "OCCUPIED":
        raise HTTPException(status_code=400, detail="Current bed is not occupied")

    # 2. Find Target Bed (Empty)
    result = await db.execute(
        select(models.Bed)
        .where(models.Bed.hospital_id == current_user.hospital_id)
        .where(models.Bed.bed_type == req.target_bed_type)
        .where(models.Bed.status == "AVAILABLE")
        .limit(1)
    )
    target_bed = result.scalar_one_or_none()

    if not target_bed:
        raise HTTPException(status_code=400, detail=f"No available {req.target_bed_type} beds!")

    # 3. Swap Patient
    patient_id = current_bed.current_patient_id
    
    # Empty old bed
    current_bed.status = "AVAILABLE"
    current_bed.current_patient_id = None
    
    # Fill new bed
    target_bed.status = "OCCUPIED"
    target_bed.current_patient_id = patient_id

    await db.commit()
    await manager.broadcast("UPDATE")
    
    return {"message": f"Patient transferred to {target_bed.bed_number}"}
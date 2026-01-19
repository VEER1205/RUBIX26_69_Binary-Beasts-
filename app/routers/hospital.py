from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import database, schemas, crud, models
from .auth import get_current_user 

router = APIRouter(
    prefix="/hospital",
    tags=["Hospital Operations"]
)

# Dependency to get DB
get_db = database.get_db

@router.post("/register-patient")
async def register_patient_and_queue(
    patient_data: schemas.PatientCreate, 
    hospital_id: int, # Receptionist provides this
    db: AsyncSession = Depends(get_db)
):
    # 1. Create the Patient User Account
    # Note: We give a default password for now since it's a walk-in
    user_in = schemas.UserCreate(
        username=patient_data.username,
        password="defaultpassword123", 
        full_name=patient_data.full_name,
        role="patient"
    )
    new_user = await crud.create_user(db, user_in)
    
    # 2. Add them to the Queue immediately
    queue_entry = await crud.add_patient_to_queue(
        db, 
        patient_id=new_user.id, 
        hospital_id=hospital_id, 
        severity=patient_data.severity
    )
    
    return {"message": "Patient added", "queue_position": queue_entry.priority_score}

@router.get("/{hospital_id}/queue")
async def view_queue(hospital_id: int, db: AsyncSession = Depends(get_db)):
    queue = await crud.get_hospital_queue(db, hospital_id)
    return queue

# ... existing imports ...

# Request Body for Admitting a Patient
class AdmitRequest(schemas.BaseModel):
    queue_id: int
    bed_type: str # "ICU" or "GENERAL"


@router.post("/admit-patient")
async def admit_patient(
    request: AdmitRequest, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Get the Queue Entry
    queue_entry_query = await db.execute(
        select(models.OpdQueue).where(models.OpdQueue.id == request.queue_id)
    )
    queue_entry = queue_entry_query.scalar_one_or_none()
    
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    # 2. Find an Available Bed
    bed_query = await db.execute(
        select(models.Bed)
        .where(models.Bed.hospital_id == queue_entry.hospital_id)
        .where(models.Bed.bed_type == request.bed_type)
        .where(models.Bed.status == "AVAILABLE")
        .limit(1)
    )
    bed = bed_query.scalar_one_or_none()
    
    if not bed:
        raise HTTPException(status_code=400, detail=f"No {request.bed_type} beds available!")

    # 3. Assign Patient to Bed
    bed.status = "OCCUPIED"
    bed.current_patient_id = queue_entry.patient_id
    
    # 4. Update Queue Status
    queue_entry.status = "COMPLETED"
    
    await db.commit()
    
    # TODO: Here is where you would trigger the WebSocket broadcast
    
    return {"message": f"Patient admitted to Bed {bed.bed_number}"}

@router.post("/discharge-patient/{bed_id}")
async def discharge_patient(bed_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Get the Bed
    bed_query = await db.execute(select(models.Bed).where(models.Bed.id == bed_id))
    bed = bed_query.scalar_one_or_none()
    
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
        
    # 2. Free the Bed
    bed.status = "AVAILABLE"
    bed.current_patient_id = None
    
    await db.commit()
    return {"message": f"Bed {bed.bed_number} is now AVAILABLE"}

@router.post("/create")
async def create_new_hospital(
    hospital_data: schemas.HospitalCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    # 1. Check Authorization (RBAC)
    if current_user.role != "admin": 
        raise HTTPException(status_code=403, detail="Not authorized: Only Admins can create hospitals")

    # 1. Create the Hospital Entry
    new_hospital = models.Hospital(
        name=hospital_data.name,
        location=hospital_data.location,
        contact_number=hospital_data.contact_number
    )
    db.add(new_hospital)
    await db.commit()
    await db.refresh(new_hospital) 

    # 2. Automatically Generate Beds based on the counts provided
    beds_to_add = []
    
    # Generate ICU Beds
    for i in range(1, hospital_data.icu_bed_count + 1):
        beds_to_add.append(models.Bed(
            hospital_id=new_hospital.id,
            bed_number=f"ICU-{i}",
            bed_type="ICU",
            status="AVAILABLE"
        ))
        
    # Generate General Beds
    for i in range(1, hospital_data.general_bed_count + 1):
        beds_to_add.append(models.Bed(
            hospital_id=new_hospital.id,
            bed_number=f"GEN-{i}",
            bed_type="GENERAL",
            status="AVAILABLE"
        ))
    
    db.add_all(beds_to_add)
    await db.commit()
    
    return {
        "message": "Hospital created successfully",
        "hospital_id": new_hospital.id,
        "hospital_name": new_hospital.name,
        "total_beds_created": len(beds_to_add)
    }
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from .. import database, models, schemas
from ..routers.auth import get_current_user # Security Guard
from ..schemas import AdminCreate

router = APIRouter(
    prefix="/super-admin",
    tags=["Super Admin (Platform Owner)"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency: Check if user is SUPER_ADMIN
async def check_super_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Access Denied: Super Admin Only")
    return current_user

# --- 1. ADD HOSPITAL ---
@router.post("/hospital/add")
async def add_hospital(
    hospital_data: schemas.HospitalCreate, # Reuse your schema
    db: AsyncSession = Depends(database.get_db),
    _: models.User = Depends(check_super_admin)
):
    # Create Hospital
    new_hospital = models.Hospital(
        name=hospital_data.name,
        location=hospital_data.location,
        contact_number=hospital_data.contact_number
    )
    db.add(new_hospital)
    await db.commit()
    await db.refresh(new_hospital)
    
    # Auto-generate Beds (Optional, but useful)
    beds = []
    for i in range(1, hospital_data.icu_bed_count + 1):
        beds.append(models.Bed(hospital_id=new_hospital.id, bed_number=f"ICU-{i}", bed_type="ICU", status="AVAILABLE"))
    for i in range(1, hospital_data.general_bed_count + 1):
        beds.append(models.Bed(hospital_id=new_hospital.id, bed_number=f"GEN-{i}", bed_type="GENERAL", status="AVAILABLE"))
    
    db.add_all(beds)
    await db.commit()
    
    return {"message": "Hospital Created", "hospital_id": new_hospital.id}

# --- 2. REMOVE HOSPITAL ---
@router.delete("/hospital/{hospital_id}")
async def delete_hospital(
    hospital_id: int, 
    db: AsyncSession = Depends(database.get_db),
    _: models.User = Depends(check_super_admin)
):
    hospital = await db.get(models.Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    # Note: In a real app, you must delete users/beds first (Cascade). 
    # For Hackathon, we assume DB handles cascade or we just delete the entry.
    await db.delete(hospital)
    await db.commit()
    return {"message": f"Hospital {hospital.name} deleted"}

# --- 3. CREATE ADMIN FOR A HOSPITAL ---


@router.post("/create-admin")
async def create_hospital_admin(
    admin_data: AdminCreate,
    db: AsyncSession = Depends(database.get_db),
    _: models.User = Depends(check_super_admin)
):
    # Verify Hospital Exists
    hospital = await db.get(models.Hospital, admin_data.hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital ID invalid")

    # Create User
    new_admin = models.User(
        username=admin_data.username,
        hashed_password=pwd_context.hash(admin_data.password),
        full_name=admin_data.full_name,
        role=models.UserRole.HOSPITAL_ADMIN, # Assign role
        hospital_id=admin_data.hospital_id
    )
    db.add(new_admin)
    await db.commit()
    
    return {"message": f"Admin created for {hospital.name}"}
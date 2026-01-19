from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from .. import database, models

router = APIRouter(prefix="/seed", tags=["Test Data"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 1. CREATE SUPER ADMIN (One-time Setup) ---
@router.post("/create-super-admin")
async def create_super_admin(db: AsyncSession = Depends(database.get_db)):
    # Check if exists
    result = await db.execute(select(models.User).where(models.User.role == models.UserRole.SUPER_ADMIN))
    if result.scalar_one_or_none():
        return {"message": "Super Admin already exists!"}

    # Create Super Admin (No Hospital ID)
    super_admin = models.User(
        username="superadmin",
        hashed_password=pwd_context.hash("super123"), # Change this in production!
        full_name="Platform Owner",
        role=models.UserRole.SUPER_ADMIN,
        hospital_id=None # Super Admin belongs to NO hospital
    )
    db.add(super_admin)
    await db.commit()
    return {"message": "Super Admin created! Login with 'superadmin' / 'super123'"}

# --- 2. CREATE HOSPITAL ADMIN (For a specific Hospital) ---
@router.post("/create-hospital-admin")
async def create_hospital_admin(
    hospital_id: int, 
    username: str, 
    db: AsyncSession = Depends(database.get_db)
):
    # Check if hospital exists
    hospital = await db.get(models.Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    # Create Admin for this Hospital
    admin = models.User(
        username=username,
        hashed_password=pwd_context.hash("admin123"),
        full_name=f"Admin of {hospital.name}",
        role=models.UserRole.HOSPITAL_ADMIN,
        hospital_id=hospital_id
    )
    db.add(admin)
    await db.commit()
    return {"message": f"Hospital Admin '{username}' created for Hospital {hospital_id}"}
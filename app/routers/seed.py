from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import database, models, auth  # Ensure auth is imported if you have password hashing there, or use a simple string for now.
from passlib.context import CryptContext
from sqlalchemy import select

router = APIRouter(prefix="/seed", tags=["Test Data"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/create-test-data")
async def create_test_data(db: AsyncSession = Depends(database.get_db)):
    admin = models.User(
        username="superadmin",
        hashed_password=pwd_context.hash("admin123"),
        full_name="System Administrator",
        role="admin",
        hospital_id=None # Admins might not belong to one hospital
    )
    db.add(admin)
    await db.commit()
    # 1. Create a Test Hospital
    hospital = models.Hospital(
        name="City General Hospital",
        location="Mumbai, Andheri West",
        contact_number="9998887777"
    )
    db.add(hospital)
    await db.commit()
    await db.refresh(hospital)

    # 2. Create Beds for this Hospital
    beds = []
    # 5 ICU Beds
    for i in range(1, 6):
        beds.append(models.Bed(
            hospital_id=hospital.id,
            bed_number=f"ICU-{i}",
            bed_type="ICU",
            status="AVAILABLE"
        ))
    # 10 General Beds
    for i in range(1, 11):
        beds.append(models.Bed(
            hospital_id=hospital.id,
            bed_number=f"GEN-{i}",
            bed_type="GENERAL",
            status="AVAILABLE"
        ))
    
    db.add_all(beds)

    # 3. Create a Receptionist User
    receptionist = models.User(
        username="receptionist1",
        hashed_password=pwd_context.hash("password123"),
        full_name="Anita Sharma",
        role="receptionist",
        hospital_id=hospital.id
    )
    db.add(receptionist)
    
    await db.commit()
    return {"message": "Test Hospital, Beds, and Receptionist created!", "hospital_id": hospital.id}

@router.post("/create-second-hospital")
async def create_second_hospital(db: AsyncSession = Depends(database.get_db)):
    # 1. Create Apollo Hospital
    hospital = models.Hospital(
        name="Apollo City Hospital",
        location="Mumbai, Bandra East",
        contact_number="022-5555-6666"
    )
    db.add(hospital)
    await db.commit()
    await db.refresh(hospital)

    # 2. Create Beds (Different capacity to look real)
    beds = []
    # 20 ICU Beds (Bigger hospital)
    for i in range(1, 21):
        beds.append(models.Bed(hospital_id=hospital.id, bed_number=f"ICU-{i}", bed_type="ICU", status="AVAILABLE"))
    # 50 General Beds
    for i in range(1, 51):
        beds.append(models.Bed(hospital_id=hospital.id, bed_number=f"GEN-{i}", bed_type="GENERAL", status="AVAILABLE"))
    
    db.add_all(beds)

    # 3. Create a Doctor for this hospital
    doctor = models.User(
        username="doctor_apollo",
        hashed_password=pwd_context.hash("doc123"),
        full_name="Dr. Strange",
        role="doctor",
        hospital_id=hospital.id
    )
    db.add(doctor)
    
    await db.commit()
    return {"message": "Apollo Hospital Created!", "hospital_id": hospital.id}

@router.post("/create-super-admin")
async def create_super_admin(db: AsyncSession = Depends(database.get_db)):
    # 1. Check if admin already exists to prevent duplicate error
    result = await db.execute(select(models.User).where(models.User.username == "superadmin"))
    existing_admin = result.scalar_one_or_none()
    
    if existing_admin:
        return {"message": "Super Admin already exists!"}

    # 2. Create the Admin
    admin = models.User(
        username="superadmin",
        hashed_password=pwd_context.hash("admin123"), # <--- This is the password
        full_name="System Administrator",
        role="admin", # Matches your UserRole enum
        hospital_id=None
    )
    db.add(admin)
    await db.commit()
    return {"message": "Super Admin 'superadmin' created with password 'admin123'"}

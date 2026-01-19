from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import database, models, auth  # Ensure auth is imported if you have password hashing there, or use a simple string for now.
from passlib.context import CryptContext

router = APIRouter(prefix="/seed", tags=["Test Data"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/create-test-data")
async def create_test_data(db: AsyncSession = Depends(database.get_db)):
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
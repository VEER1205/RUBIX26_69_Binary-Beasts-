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
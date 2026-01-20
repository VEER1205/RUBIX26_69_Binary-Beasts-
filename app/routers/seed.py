from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from .. import database, models
from ..routers import auth

router = APIRouter(prefix="/seed", tags=["Seed Data"])

@router.post("/master-reset")
async def master_reset_and_seed(db: AsyncSession = Depends(database.get_db)):
    """
    1. Wipes Database.
    2. Creates Hospitals, Staff, AND Patients.
    3. Fills Beds and Inventory.
    """
    
    # 1. WIPE DATA
    await db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    await db.execute(text("TRUNCATE TABLE beds;"))
    await db.execute(text("TRUNCATE TABLE inventory;"))
    await db.execute(text("TRUNCATE TABLE opd_queue;"))
    await db.execute(text("TRUNCATE TABLE users;"))
    await db.execute(text("TRUNCATE TABLE hospitals;"))
    await db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    
    # 2. CREATE HOSPITALS
    h1 = models.Hospital(name="City General Hospital", location="Borivali West", contact_number="022-2899-1234")
    h2 = models.Hospital(name="Apollo Trauma Center", location="Andheri East", contact_number="022-5555-9999")
    db.add_all([h1, h2])
    await db.flush() 

    password = auth.get_password_hash("123")

    # 3. CREATE STAFF
    staff = [
        models.User(username="superadmin", full_name="System Owner", role="super_admin", hashed_password=password),
        models.User(username="admin1", full_name="Admin CityGen", role="hospital_admin", hospital_id=h1.id, hashed_password=password),
        models.User(username="doc1", full_name="Dr. A. Smith", role="doctor", hospital_id=h1.id, hashed_password=password),
        models.User(username="reception1", full_name="Front Desk City", role="receptionist", hospital_id=h1.id, hashed_password=password),
        models.User(username="admin2", full_name="Admin Apollo", role="hospital_admin", hospital_id=h2.id, hashed_password=password),
        models.User(username="driver1", full_name="Ambulance Unit 42", role="ambulance", hashed_password=password),
    ]
    db.add_all(staff)
    await db.flush()

    # 4. CREATE PATIENTS (The Missing Step!)
    patients = []
    for i in range(1, 31): # Create 30 dummy patients
        p = models.User(
            username=f"patient{i}", 
            full_name=f"Patient {i}", 
            role="patient", 
            hashed_password=password,
            hospital_id=h1.id if i <= 20 else h2.id
        )
        patients.append(p)
    
    db.add_all(patients)
    await db.flush() # IMPORTANT: This generates the IDs for the patients

    # 5. CREATE BEDS (Now linking to existing patients)
    beds = []
    
    # Hospital 1: 10 ICU, 20 General
    # Use patients[0] to patients[19] for H1
    for i in range(1, 11): 
        # Even numbered beds are occupied by a patient from our list
        is_occupied = (i % 2 == 0)
        patient_id = patients[i-1].id if is_occupied else None
        status = "OCCUPIED" if is_occupied else "AVAILABLE"
        
        beds.append(models.Bed(
            bed_number=f"ICU-{i}", 
            bed_type="ICU", 
            status=status, 
            hospital_id=h1.id, 
            current_patient_id=patient_id
        ))

    for i in range(1, 21):
        is_occupied = (i % 3 == 0) # Every 3rd bed occupied
        # Use patients 10-29 for General beds logic (offset index)
        patient_idx = 10 + (i % 10) 
        patient_id = patients[patient_idx].id if is_occupied else None
        status = "OCCUPIED" if is_occupied else "AVAILABLE"

        beds.append(models.Bed(
            bed_number=f"GEN-{i}", 
            bed_type="GENERAL", 
            status=status, 
            hospital_id=h1.id, 
            current_patient_id=patient_id
        ))

    # Hospital 2 Beds
    for i in range(1, 6):
        beds.append(models.Bed(bed_number=f"ICU-{i}", bed_type="ICU", status="AVAILABLE", hospital_id=h2.id))

    db.add_all(beds)

    # 6. INVENTORY
    inventory = [
        models.InventoryItem(item_name="Paracetamol", category="Medicine", quantity=100, hospital_id=h1.id),
        models.InventoryItem(item_name="Oxygen Cylinder", category="Equipment", quantity=5, hospital_id=h1.id),
        models.InventoryItem(item_name="Morphine", category="Medicine", quantity=20, hospital_id=h2.id),
    ]
    db.add_all(inventory)

    await db.commit()
    return {"message": "✅ Database Reset Complete. Patients & Beds Linked Successfully."}
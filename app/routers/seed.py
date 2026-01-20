from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from .. import database, models
from ..routers import auth
from sqlalchemy import select


router = APIRouter(prefix="/seed", tags=["Seed Data"])

@router.post("/master-reset")
async def master_reset_and_seed(db: AsyncSession = Depends(database.get_db)):
    """
    Creates:
    1. City General (Mixed Availability)
    2. Apollo Trauma (Mostly Empty)
    3. Metropolis Health (100% FULL - For testing Queue/Red alerts)
    """
    
    # 1. WIPE DATA
    await db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    await db.execute(text("TRUNCATE TABLE beds;"))
    await db.execute(text("TRUNCATE TABLE inventory;"))
    await db.execute(text("TRUNCATE TABLE opd_queue;"))
    await db.execute(text("TRUNCATE TABLE users;"))
    await db.execute(text("TRUNCATE TABLE hospitals;"))
    await db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    
    # 2. CREATE 3 HOSPITALS
    h1 = models.Hospital(name="City General Hospital", location="Borivali West", contact_number="022-2899-1234")
    h2 = models.Hospital(name="Apollo Trauma Center", location="Andheri East", contact_number="022-5555-9999")
    h3 = models.Hospital(name="Metropolis Health", location="Bandra West", contact_number="022-6666-7777") # <--- FULL HOSPITAL
    
    db.add_all([h1, h2, h3])
    await db.flush() 

    password = auth.get_password_hash("123")

    # 3. CREATE STAFF
    staff = [
        models.User(username="superadmin", full_name="System Owner", role="super_admin", hashed_password=password),
        
        # H1 Staff
        models.User(username="admin1", full_name="Admin CityGen", role="hospital_admin", hospital_id=h1.id, hashed_password=password),
        models.User(username="doc1", full_name="Dr. A. Smith", role="doctor", hospital_id=h1.id, hashed_password=password),
        models.User(username="reception1", full_name="Front Desk City", role="receptionist", hospital_id=h1.id, hashed_password=password),
        
        # H2 Staff
        models.User(username="admin2", full_name="Admin Apollo", role="hospital_admin", hospital_id=h2.id, hashed_password=password),
        models.User(username="doc2", full_name="Dr. B. Strange", role="doctor", hospital_id=h2.id, hashed_password=password),
        
        # H3 Staff (Metropolis - Full)
        models.User(username="admin3", full_name="Admin Metropolis", role="hospital_admin", hospital_id=h3.id, hashed_password=password),
        models.User(username="doc3", full_name="Dr. House", role="doctor", hospital_id=h3.id, hashed_password=password),
        models.User(username="reception3", full_name="Nurse Joy", role="receptionist", hospital_id=h3.id, hashed_password=password),

        # Driver
        models.User(username="driver1", full_name="Ambulance Unit 42", role="ambulance", hashed_password=password),
    ]
    db.add_all(staff)
    await db.flush()

    # 4. CREATE PATIENTS (Need enough to fill H3 completely)
    # We will create 50 patients
    patients = []
    for i in range(1, 51):
        # Assign hospitals loosely for the user record (doesn't affect bed logic much)
        hid = h1.id
        if i > 20: hid = h2.id
        if i > 30: hid = h3.id 
        
        p = models.User(
            username=f"patient{i}", 
            full_name=f"Patient {i}", 
            role="patient", 
            hashed_password=password,
            hospital_id=hid
        )
        patients.append(p)
    
    db.add_all(patients)
    await db.flush()

    # 5. CREATE BEDS
    beds = []
    
    # --- HOSPITAL 1: Mixed (City Gen) ---
    for i in range(1, 11): # 10 ICU (Half Full)
        is_occupied = (i % 2 == 0)
        beds.append(models.Bed(bed_number=f"ICU-{i}", bed_type="ICU", status="OCCUPIED" if is_occupied else "AVAILABLE", hospital_id=h1.id, current_patient_id=patients[i-1].id if is_occupied else None))
    
    for i in range(1, 21): # 20 General (Mixed)
        is_occupied = (i % 3 == 0)
        beds.append(models.Bed(bed_number=f"GEN-{i}", bed_type="GENERAL", status="OCCUPIED" if is_occupied else "AVAILABLE", hospital_id=h1.id, current_patient_id=patients[10+i].id if is_occupied else None))

    # --- HOSPITAL 2: Empty (Apollo) ---
    for i in range(1, 6):
        beds.append(models.Bed(bed_number=f"ICU-{i}", bed_type="ICU", status="AVAILABLE", hospital_id=h2.id))

    # --- HOSPITAL 3: FULL CAPACITY (Metropolis) ---
    # 5 ICU Beds (ALL FULL)
    for i in range(1, 6):
        beds.append(models.Bed(bed_number=f"ICU-{i}", bed_type="ICU", status="OCCUPIED", hospital_id=h3.id, current_patient_id=patients[30+i].id))
        
    # 5 General Beds (ALL FULL)
    for i in range(1, 6):
        beds.append(models.Bed(bed_number=f"GEN-{i}", bed_type="GENERAL", status="OCCUPIED", hospital_id=h3.id, current_patient_id=patients[36+i].id))

    db.add_all(beds)

    # 6. INVENTORY
    inventory = [
        models.InventoryItem(item_name="Paracetamol", category="Medicine", quantity=100, hospital_id=h1.id),
        models.InventoryItem(item_name="Oxygen Cylinder", category="Equipment", quantity=2, hospital_id=h3.id), # Low Stock at full hospital
    ]
    db.add_all(inventory)

    await db.commit()
    return {"message": "✅ Database Reset. Metropolis Health is now FULL (100% Occupancy)."}

# ... (Keep existing imports and master_reset function) ...

@router.post("/add-full-hospital")
async def add_full_hospital_only(db: AsyncSession = Depends(database.get_db)):
    """
    APPENDS 'Metropolis Health' (100% Full) to the existing database.
    Does NOT delete existing data.
    """
    
    # 1. Check if it already exists to prevent duplicates
    result = await db.execute(select(models.Hospital).where(models.Hospital.name == "Metropolis Health"))
    if result.scalars().first():
        return {"message": "Metropolis Health already exists! No changes made."}

    # 2. CREATE HOSPITAL
    h_new = models.Hospital(name="Metropolis Health", location="Bandra West", contact_number="022-6666-7777")
    db.add(h_new)
    await db.flush() # Generate h_new.id

    password = auth.get_password_hash("123")

    # 3. CREATE STAFF (Unique usernames)
    staff = [
        models.User(username="admin_metro", full_name="Admin Metropolis", role="hospital_admin", hospital_id=h_new.id, hashed_password=password),
        models.User(username="doc_metro", full_name="Dr. House", role="doctor", hospital_id=h_new.id, hashed_password=password),
        models.User(username="reception_metro", full_name="Nurse Joy", role="receptionist", hospital_id=h_new.id, hashed_password=password),
    ]
    db.add_all(staff)
    
    # 4. CREATE PATIENTS (Specifically for this hospital)
    # Creating 10 patients for 10 beds
    patients = []
    for i in range(1, 11):
        p = models.User(
            username=f"metro_pat_{i}", 
            full_name=f"Metro Patient {i}", 
            role="patient", 
            hashed_password=password,
            hospital_id=h_new.id
        )
        patients.append(p)
    db.add_all(patients)
    await db.flush() # Generate Patient IDs

    # 5. CREATE BEDS (100% Occupied)
    beds = []
    # 5 ICU Beds (FULL)
    for i in range(5):
        beds.append(models.Bed(bed_number=f"ICU-{i+1}", bed_type="ICU", status="OCCUPIED", hospital_id=h_new.id, current_patient_id=patients[i].id))
    
    # 5 General Beds (FULL)
    for i in range(5, 10):
        beds.append(models.Bed(bed_number=f"GEN-{i+1}", bed_type="GENERAL", status="OCCUPIED", hospital_id=h_new.id, current_patient_id=patients[i].id))

    db.add_all(beds)

    # 6. INVENTORY
    inv = models.InventoryItem(item_name="Oxygen Cylinder", category="Equipment", quantity=0, hospital_id=h_new.id) # Out of stock!
    db.add(inv)

    await db.commit()
    return {"message": "✅ Metropolis Health (Full Capacity) Added Successfully!"}
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. Create a User (Generic)
async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# 2. The "Receptionist" Logic: Add to Queue
async def add_patient_to_queue(db: AsyncSession, patient_id: int, hospital_id: int, severity: int):
    initial_score = severity * 1000.0

    # B. Create the Queue Entry
    db_queue = models.OpdQueue(
        patient_id=patient_id,
        hospital_id=hospital_id,
        severity=severity,
        priority_score=initial_score,
        check_in_time=datetime.utcnow(),
        status="WAITING"
    )
    
    # C. Save to DB
    db.add(db_queue)
    await db.commit()
    await db.refresh(db_queue)
    return db_queue

# 3. Get the Queue (Sorted by Priority)
async def get_hospital_queue(db: AsyncSession, hospital_id: int):
    # Query: Select * from OpdQueue where hospital_id == X order by priority_score DESC
    result = await db.execute(
        select(models.OpdQueue)
        .where(models.OpdQueue.hospital_id == hospital_id)
        .where(models.OpdQueue.status == "WAITING")
        .order_by(models.OpdQueue.priority_score.desc())
    )
    return result.scalars().all()
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from .. import database, models

router = APIRouter(
    prefix="/dashboard",
    tags=["City Dashboard (Public)"]
)

@router.get("/city-stats")
async def get_city_stats(db: AsyncSession = Depends(database.get_db)):
    
    # 1. Get all Hospitals
    hospitals_result = await db.execute(select(models.Hospital))
    hospitals = hospitals_result.scalars().all()
    
    city_data = []
    
    for hospital in hospitals:
        # 2. Count Available ICU Beds
        icu_query = select(func.count(models.Bed.id)).where(
            models.Bed.hospital_id == hospital.id,
            models.Bed.bed_type == "ICU",
            models.Bed.status == "AVAILABLE"
        )
        icu_count = (await db.execute(icu_query)).scalar()
        
        # 3. Count Available General Beds
        gen_query = select(func.count(models.Bed.id)).where(
            models.Bed.hospital_id == hospital.id,
            models.Bed.bed_type == "GENERAL",
            models.Bed.status == "AVAILABLE"
        )
        gen_count = (await db.execute(gen_query)).scalar()
        
        # 4. Get Queue Length
        queue_query = select(func.count(models.OpdQueue.id)).where(
            models.OpdQueue.hospital_id == hospital.id,
            models.OpdQueue.status == "WAITING"
        )
        queue_len = (await db.execute(queue_query)).scalar()

        city_data.append({
            "hospital_name": hospital.name,
            "location": hospital.location,
            "contact": hospital.contact_number,
            "available_icu": icu_count,
            "available_general": gen_count,
            "active_queue": queue_len
        })
        
    return city_data
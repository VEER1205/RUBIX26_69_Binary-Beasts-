from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import database, models
from ..routers.auth import get_current_user

router = APIRouter(prefix="/patient", tags=["Patient Portal"])
get_db = database.get_db

@router.get("/me")
async def get_my_status(
    db: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    if user.role != models.UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Not a patient account")

    # 1. Check if in Queue
    queue_entry = await db.execute(
        select(models.OpdQueue)
        .where(models.OpdQueue.patient_id == user.id)
        .where(models.OpdQueue.status == "WAITING")
    )
    queue_data = queue_entry.scalars().first()

    # 2. Check if Admitted to Bed
    bed_entry = await db.execute(
        select(models.Bed).where(models.Bed.current_patient_id == user.id)
    )
    bed_data = bed_entry.scalars().first()

    # 3. Construct Response
    status = "Home"
    details = "No active appointments."
    
    if bed_data:
        status = "Admitted"
        details = f"You are admitted in Bed {bed_data.bed_number} ({bed_data.bed_type})."
    elif queue_data:
        status = "In Queue"
        details = f"Waiting for Doctor. Priority Score: {queue_data.priority_score}"

    return {
        "full_name": user.full_name,
        "status": status,
        "details": details,
        "next_visit": user.next_visit_date or "Not Scheduled",
        "hospital_id": user.hospital_id
    }
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .. import database, models
# IMPORT THE MANAGER from the new file
from ..websocket_manager import manager 
from ..schemas import EmergencyAlert

router = APIRouter(prefix="/emergency", tags=["Ambulance"])
get_db = database.get_db



@router.post("/notify")
async def send_emergency_alert(
    alert: EmergencyAlert,
    db: AsyncSession = Depends(get_db)
):
    hospital = await db.get(models.Hospital, alert.hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    message = {
        "type": "EMERGENCY",
        "hospital_id": hospital.id,
        "hospital_name": hospital.name,
        "driver": alert.driver_name,
        "eta": alert.eta,
        "condition": alert.patient_condition
    }
    
    await manager.broadcast(message) # This now works perfectly
    return {"status": "Alert Sent"}
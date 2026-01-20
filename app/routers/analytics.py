from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from .. import database, models
from ..routers.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics & Inventory"])
get_db = database.get_db

# --- SCHEMAS ---
class ItemCreate(BaseModel):
    item_name: str
    category: str
    quantity: int
    threshold: int = 10

# --- 1. ADD INVENTORY ITEM ---
@router.post("/inventory/add")
async def add_item(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    if user.role != models.UserRole.HOSPITAL_ADMIN:
        raise HTTPException(status_code=403, detail="Access Denied")

    new_item = models.InventoryItem(
        item_name=item.item_name,
        category=item.category,
        quantity=item.quantity,
        low_stock_threshold=item.threshold,
        hospital_id=user.hospital_id
    )
    db.add(new_item)
    await db.commit()
    return {"message": "Item added"}

# --- 2. GET INVENTORY (With Auto-Low-Stock Check) ---
@router.get("/inventory")
async def get_inventory(
    db: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.InventoryItem).where(models.InventoryItem.hospital_id == user.hospital_id)
    )
    items = result.scalars().all()
    
    # Automation Logic: Check if Low Stock
    data = []
    for i in items:
        status = "OK"
        if i.quantity <= 0: status = "OUT_OF_STOCK"
        elif i.quantity < i.low_stock_threshold: status = "LOW_STOCK" # <--- AUTOMATION
        
        data.append({
            "id": i.id,
            "name": i.item_name,
            "qty": i.quantity,
            "status": status
        })
    return data

# --- 3. GRAPH DATA (Bed Stats) ---
@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Count Beds
    result_beds = await db.execute(
        select(models.Bed.status, func.count(models.Bed.id))
        .where(models.Bed.hospital_id == user.hospital_id)
        .group_by(models.Bed.status)
    )
    bed_stats = result_beds.all() # e.g., [('AVAILABLE', 10), ('OCCUPIED', 5)]
    
    # Format for Chart.js
    stats = {"AVAILABLE": 0, "OCCUPIED": 0}
    for status, count in bed_stats:
        stats[status] = count
        
    return stats

# ... existing imports ...

# --- 4. USE INVENTORY (Doctor Dispenses Medicine) ---
class UseItemRequest(BaseModel):
    item_id: int
    quantity: int

@router.post("/inventory/use")
async def use_inventory_item(
    req: UseItemRequest,
    db: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Only Doctors (or Admins) can use stock
    if user.role not in [models.UserRole.DOCTOR, models.UserRole.HOSPITAL_ADMIN]:
        raise HTTPException(status_code=403, detail="Access Denied")

    item = await db.get(models.InventoryItem, req.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if item.hospital_id != user.hospital_id:
        raise HTTPException(status_code=403, detail="Wrong hospital")

    if item.quantity < req.quantity:
        raise HTTPException(status_code=400, detail=f"Not enough stock! Only {item.quantity} left.")

    # Deduct Stock
    item.quantity -= req.quantity
    await db.commit()
    
    return {"message": f"Dispensed {req.quantity} of {item.item_name}. Remaining: {item.quantity}"}
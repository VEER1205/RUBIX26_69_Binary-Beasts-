from fastapi import FastAPI
from .database import engine, Base
from .routers import hospital,seed

app = FastAPI(title="Hospital Operations Sync")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def read_root():
    return {"message": "Hospital Operations Backend is Running!"}

app.include_router(hospital.router)
app.include_router(seed.router)
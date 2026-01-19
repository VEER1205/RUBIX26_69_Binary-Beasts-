from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import hospital, dashboard, seed, auth
import os

app = FastAPI(title="Hospital Operations Sync")


current_dir = os.path.dirname(os.path.abspath(__file__))

templates_path = os.path.join(current_dir, "..", "templates")
templates = Jinja2Templates(directory=templates_path)


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Include Routers
app.include_router(hospital.router)
app.include_router(dashboard.router)
app.include_router(seed.router)
app.include_router(auth.router)

# --- 2. THE NEW HOME PAGE ROUTE ---
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
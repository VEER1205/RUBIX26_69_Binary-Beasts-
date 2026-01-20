from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import ssl  # <--- NEW IMPORT
from dotenv import load_dotenv

load_dotenv()

# Ensure we use the async driver
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://")

# --- 1. CONFIGURE SSL CORRECTLY ---
# We create a real SSL Context object. 
# 'create_default_context' automatically loads your computer's trusted CAs.
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE  # Accepts TiDB's certificate without fighting

# --- 2. CREATE ENGINE ---
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,  # Fixes "Lost connection"
    pool_recycle=300,    # Refreshes connections every 5 mins
    # Pass the SSL Context object, NOT a dictionary
    connect_args={"ssl": ssl_context} 
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
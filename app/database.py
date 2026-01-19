from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# CHANGE THIS to your actual PostgreSQL URL
# Format: postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost/hospital_db"

engine = create_async_engine(DATABASE_URL, echo=True)

# Async Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency to get DB session in endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
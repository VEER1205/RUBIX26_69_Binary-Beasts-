import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import Settings

# 1. REMOVE '?ssl=true' from the end of this URL
DATABASE_URL = Settings().DATABASE_URL

# 2. Create a standardized SSL Context
# This tells Python: "Use SSL, but don't crash if the certificate name doesn't perfectly match" (Good for Hackathons/Cloud DBs)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 3. Pass the SSL Context via connect_args
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
    connect_args={"ssl": ssl_context} 
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
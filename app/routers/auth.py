from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from .. import database, models
from ..config import Settings

router = APIRouter(tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONFIGURATION (Keep these secret in production!) ---
SECRET_KEY = Settings().SECRET_KEY
ALGORITHM =  Settings().ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 300 

def get_password_hash(password):
    return pwd_context.hash(password)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- HELPER FUNCTIONS ---

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- DEPENDENCY: Get Current User (The Guard) ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Find the user in DB
    result = await db.execute(select(models.User).where(models.User.username == username))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# --- LOGIN ENDPOINT (Generates Token) ---
@router.post("/token") # Standard name for Swagger UI to work
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(database.get_db)):
    # 1. Find User
    result = await db.execute(select(models.User).where(models.User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    # 2. Check Password
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # 3. Generate Token
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    
    # 4. Return Token + User Info (Convenient for Frontend)
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role,
        "hospital_id": user.hospital_id
    }
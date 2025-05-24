from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client
from typing import Optional, Annotated, AsyncGenerator

from database import create_supabase_client, get_user_by_email
from app.models import TokenData, User
from config import JWT_SECRET_KEY, JWT_ALGORITHM, AI_MODEL_NAME
from app.ai_engines.gemini_engine import GeminiEngine
from app.feedback_engine import FeedbackEngine

# settings = get_settings() # Removed: get_settings does not exist

# --- Database Session Dependency ---
async def get_db_session() -> AsyncGenerator[Client, None]:
    db_client = create_supabase_client()
    try:
        yield db_client
    finally:
        pass

# --- Authentication Dependencies ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # tokenUrl might use a config var if dynamic

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Client = Depends(get_db_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not JWT_SECRET_KEY:
        # Handle missing JWT_SECRET_KEY appropriately. 
        # This dependency will fail if it's not set.
        # Log this issue or raise a more specific server configuration error.
        print("Critical Error: JWT_SECRET_KEY is not configured. Authentication will fail.")
        raise credentials_exception 
        
    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, # Use directly imported constant
            algorithms=[JWT_ALGORITHM] # Use directly imported constant
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(db, email=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# --- AI Engine Dependencies ---

# Global instance of GeminiEngine to be reused
# This helps in managing resources like API connections if any are persistent
# and avoids re-initializing the model on every request.
_gemini_engine_instance: Optional[GeminiEngine] = None

def get_gemini_engine() -> GeminiEngine:
    global _gemini_engine_instance
    if _gemini_engine_instance is None:
        # Use the directly imported AI_MODEL_NAME or a fallback if it's None
        model_to_use = AI_MODEL_NAME if AI_MODEL_NAME else "gemini-1.5-flash-latest"
        _gemini_engine_instance = GeminiEngine(model_name=model_to_use)
    return _gemini_engine_instance

# Global instance of FeedbackEngine
_feedback_engine_instance: Optional[FeedbackEngine] = None

def get_feedback_engine(gemini_engine: GeminiEngine = Depends(get_gemini_engine)) -> FeedbackEngine:
    global _feedback_engine_instance
    if _feedback_engine_instance is None:
        _feedback_engine_instance = FeedbackEngine(gemini_engine=gemini_engine)
    return _feedback_engine_instance 
"""
Centralized env-var loader for LinguaLog backend.

This module loads and validates environment variables from the .env file
and exposes them as constants for use throughout the application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Environment variables
SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str | None = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# Hugging Face token for model access
HUGGINGFACE_TOKEN: str | None = os.getenv("HUGGINGFACE_TOKEN")

# Mistral model path
MISTRAL_MODEL_PATH: str = os.getenv("MISTRAL_MODEL_PATH", str(Path.home().joinpath('mistral_models', '7B-Instruct-v0.3')))
USE_MISTRAL: bool = os.getenv("USE_MISTRAL", "true").lower() == "true"
USE_TRANSFORMERS_ONLY: bool = os.getenv("USE_TRANSFORMERS_ONLY", "false").lower() == "true"

# JWT Settings
JWT_SECRET_KEY: str | None = os.getenv("JWT_SECRET_KEY") # Should be set in production
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))) # Default 7 days

# AI Model Settings
AI_MODEL_NAME: str | None = os.getenv("AI_MODEL_NAME") # e.g., "gemini-1.5-flash-latest"

def validate_env_vars() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
    ]
    
    # If not using Mistral, require Gemini API key
    if not USE_MISTRAL and not GEMINI_API_KEY:
        required_vars.append("GEMINI_API_KEY")
    
    # Validate JWT_SECRET_KEY
    if not JWT_SECRET_KEY:
        # In a real app, you might want to make this a hard requirement
        # by adding to required_vars and returning False if not set.
        # For now, just a warning, as it might be set for local dev in a way not picked by getenv immediately
        # or the user might be using an auth method not requiring this specific setup.
        print("Warning: JWT_SECRET_KEY is not set. JWT-based authentication will fail.")
        # If JWT is essential and always on, you'd make this a fatal error:
        # required_vars.append("JWT_SECRET_KEY")
    
    # If using Mistral, recommend (but don't require) the HuggingFace token
    if USE_MISTRAL and not HUGGINGFACE_TOKEN:
        print("Warning: HUGGINGFACE_TOKEN is not set. Model download may fail if the model is gated.")
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or set them in your environment.")
        return False
    
    return True


# Additional environment variables can be added here as needed 
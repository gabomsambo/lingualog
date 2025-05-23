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
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# Hugging Face token for model access
HUGGINGFACE_TOKEN: str | None = os.getenv("HUGGINGFACE_TOKEN")

# Mistral model path
MISTRAL_MODEL_PATH: str = os.getenv("MISTRAL_MODEL_PATH", str(Path.home().joinpath('mistral_models', '7B-Instruct-v0.3')))
USE_MISTRAL: bool = os.getenv("USE_MISTRAL", "true").lower() == "true"
USE_TRANSFORMERS_ONLY: bool = os.getenv("USE_TRANSFORMERS_ONLY", "false").lower() == "true"

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
    
    # If not using Mistral, require OpenAI API key
    if not USE_MISTRAL and not OPENAI_API_KEY:
        required_vars.append("OPENAI_API_KEY")
    
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
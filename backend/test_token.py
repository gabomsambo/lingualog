"""
Test script to verify Hugging Face token configuration.
"""
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import local modules
from backend.config import HUGGINGFACE_TOKEN
from backend.mistral_engine import load_model, generate_text

def main():
    """
    Test Hugging Face token and Mistral model integration.
    """
    # Print token information (without revealing the full token)
    if HUGGINGFACE_TOKEN:
        token_preview = f"{HUGGINGFACE_TOKEN[:5]}...{HUGGINGFACE_TOKEN[-5:]}"
        logger.info(f"Hugging Face token is set: {token_preview}")
    else:
        logger.warning("Hugging Face token is not set!")
    
    # Try to load the model
    logger.info("Attempting to load the Mistral model...")
    model, tokenizer = load_model()
    
    # Check if we got real model and tokenizer
    if isinstance(model, str) and model == "mock_model":
        logger.warning("Loaded mock model, not the real Mistral model.")
    else:
        logger.info("Successfully loaded the real Mistral model!")
    
    # Try to generate text
    logger.info("Attempting to generate text...")
    text = generate_text("Hello, how are you doing today?", model, tokenizer)
    logger.info(f"Generated text: {text[:100]}...")

if __name__ == "__main__":
    main() 
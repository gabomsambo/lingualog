"""
Simple test script for Mistral model in Docker.
"""
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Print environment variables
logger.info(f"HUGGINGFACE_TOKEN: {'Set' if os.environ.get('HUGGINGFACE_TOKEN') else 'Not set'}")
logger.info(f"USE_MISTRAL: {os.environ.get('USE_MISTRAL', 'Not set')}")
logger.info(f"MISTRAL_MODEL_PATH: {os.environ.get('MISTRAL_MODEL_PATH', 'Not set')}")

# Try to import transformers
try:
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    logger.info("Successfully imported torch and transformers!")
    logger.info(f"Torch version: {torch.__version__}")
    logger.info(f"Transformers version: {transformers.__version__}")
except ImportError as e:
    logger.error(f"Error importing transformers: {e}")

# Try to load the Mistral model
try:
    logger.info("Trying to load tokenizer...")
    from huggingface_hub import login
    
    # Login to Hugging Face Hub
    if os.environ.get('HUGGINGFACE_TOKEN'):
        login(token=os.environ.get('HUGGINGFACE_TOKEN'))
        logger.info("Logged in to Hugging Face Hub")
    
    # Try downloading the model info (not the full model)
    logger.info("Checking model access...")
    tokenizer = AutoTokenizer.from_pretrained(
        "mistralai/Mistral-7B-Instruct-v0.3", 
        token=os.environ.get('HUGGINGFACE_TOKEN')
    )
    logger.info("Successfully accessed the model! Tokenizer loaded.")
except Exception as e:
    logger.error(f"Error loading Mistral model: {e}")

if __name__ == "__main__":
    logger.info("Mistral test completed") 
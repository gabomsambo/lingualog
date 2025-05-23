"""
Mistral-7B-Instruct-v0.3 Integration for LinguaLog.

This module handles interactions with the Mistral-7B-Instruct-v0.3 model for generating
comprehensive language feedback for user journal entries.

It provides both a real implementation using transformers and a mock implementation
for testing and development purposes.
"""
import os
import logging
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Local imports
from config import MISTRAL_MODEL_PATH, USE_TRANSFORMERS_ONLY, HUGGINGFACE_TOKEN

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"

# Try to import transformers, but make it optional for environments without it
try:
    print("Attempting to import torch and transformers...")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
    print("Successfully imported torch and transformers!")
    # Set device and dtype constants
    DEVICE_MAP = "auto"
    TORCH_DTYPE = torch.bfloat16  # Using bfloat16 for efficiency
except ImportError as e:
    print(f"Error importing transformers: {e}")
    logger.warning("Transformers or PyTorch not available. Will use mock implementation.")
    TRANSFORMERS_AVAILABLE = False


def download_model(local_dir: Optional[str] = None) -> Path:
    """
    Download the Mistral-7B-Instruct-v0.3 model files if they don't exist.
    
    Args:
        local_dir: Custom directory to download the model to.
                   If None, uses the default path from config.
    
    Returns:
        Path: Path to the downloaded model directory
    """
    model_path = Path(local_dir) if local_dir else Path(MISTRAL_MODEL_PATH)
    
    # Create directory if it doesn't exist
    model_path.mkdir(parents=True, exist_ok=True)
    
    if TRANSFORMERS_AVAILABLE and not USE_TRANSFORMERS_ONLY:
        # Using transformers to download and cache the model
        logger.info(f"Model will be downloaded and cached by transformers to {model_path}...")
    else:
        logger.info(f"[MOCK] Model would be downloaded to {model_path}")
    
    return model_path


def load_model(model_path: Optional[str] = None):
    """
    Load the Mistral model and tokenizer.
    
    Args:
        model_path: Path to the model directory.
                    If None, uses the default path from config.
    
    Returns:
        tuple: (model, tokenizer)
    """
    if not TRANSFORMERS_AVAILABLE or USE_TRANSFORMERS_ONLY:
        logger.info(f"[MOCK] Loading Mistral model from {model_path or MISTRAL_MODEL_PATH}")
        # Return mock objects
        mock_model = "mock_model"
        mock_tokenizer = "mock_tokenizer"
        return mock_model, mock_tokenizer
    
    try:
        # Set huggingface hub cache directory if model_path is provided
        if model_path:
            os.environ["TRANSFORMERS_CACHE"] = str(model_path)
            logger.info(f"Setting transformers cache to {model_path}")
        
        # Check if we have a Hugging Face token
        use_auth = HUGGINGFACE_TOKEN is not None and HUGGINGFACE_TOKEN.strip() != ""
        if use_auth:
            logger.info("Using Hugging Face authentication token")
        else:
            logger.warning("No Hugging Face token found. Model download may fail if the model is gated.")
        
        # Load tokenizer with token if available
        logger.info(f"Loading tokenizer from {MODEL_ID}")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, 
            token=HUGGINGFACE_TOKEN if use_auth else None
        )
        
        # Load model with appropriate settings
        logger.info(f"Loading model from {MODEL_ID}")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=TORCH_DTYPE,
            device_map=DEVICE_MAP,
            token=HUGGINGFACE_TOKEN if use_auth else None
        )
        
        logger.info(f"Successfully loaded Mistral model")
        return model, tokenizer
    
    except Exception as e:
        logger.error(f"Error loading Mistral model: {str(e)}, falling back to mock")
        # Return mock objects as fallback
        mock_model = "mock_model"
        mock_tokenizer = "mock_tokenizer"
        return mock_model, mock_tokenizer


def generate_text_with_transformers(prompt: str, model, tokenizer, max_tokens: int = 1000) -> str:
    """
    Generate text using the transformers-based Mistral model.
    
    Args:
        prompt: The input text prompt
        model: Pre-loaded model
        tokenizer: Pre-loaded tokenizer
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        str: Generated text response
    """
    # Format as a simple user message
    messages = [{"role": "user", "content": prompt}]
    
    # Tokenize the input
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )
    
    # Move input tensors to the same device as the model
    inputs = inputs.to(model.device)
    
    # Generate text
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        temperature=0.7
    )
    
    # Decode and return the result
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    return result


def generate_text_mock(prompt: str, max_tokens: int = 1000) -> str:
    """
    Mock function for text generation.
    
    Args:
        prompt: The input text prompt
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        str: Generated text response
    """
    logger.info(f"[MOCK] Generating text with prompt: {prompt[:50]}...")
    
    # Generate a basic response based on the prompt
    if "translate" in prompt.lower():
        if "french" in prompt.lower():
            return "Hello, how are you today?"
        elif "german" in prompt.lower():
            return "I learn English every day and I enjoy it."
        elif "spanish" in prompt.lower():
            return "I really like to travel and learn about new cultures."
        else:
            return "This is a translation of the given text."
    elif "language learning" in prompt.lower():
        return "Learning a new language opens up a world of opportunities. It enhances cognitive abilities, provides access to new cultures, and improves career prospects. The process of language acquisition also builds discipline and perseverance."
    else:
        return "This is a mock response from the Mistral model. In a production environment, this would be generated by the actual model."


def generate_text(prompt: str, model=None, tokenizer=None, max_tokens: int = 1000) -> str:
    """
    Generate text using the Mistral model based on a prompt.
    
    Args:
        prompt: The input text prompt
        model: Pre-loaded model (optional)
        tokenizer: Pre-loaded tokenizer (optional)
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        str: Generated text response
    """
    try:
        # Check if we should use transformers or mock
        if TRANSFORMERS_AVAILABLE and not USE_TRANSFORMERS_ONLY:
            # Load model and tokenizer if not provided
            if model is None or tokenizer is None:
                model, tokenizer = load_model()
            
            # Check if we got real model and tokenizer or mock objects
            if isinstance(model, str) and model == "mock_model":
                return generate_text_mock(prompt, max_tokens)
            
            # Generate with transformers
            return generate_text_with_transformers(prompt, model, tokenizer, max_tokens)
        else:
            # Use mock implementation
            return generate_text_mock(prompt, max_tokens)
    
    except Exception as e:
        logger.error(f"Error generating text with Mistral: {str(e)}, falling back to mock")
        return generate_text_mock(prompt, max_tokens)


def analyze_entry_with_transformers(text: str, model, tokenizer) -> Dict[str, Any]:
    """
    Analyze a journal entry using the real Mistral model.
    
    Args:
        text: The journal entry text to analyze
        model: The loaded model
        tokenizer: The loaded tokenizer
        
    Returns:
        Dict: Dictionary with all feedback dimensions
    """
    # Construct a prompt that asks for JSON-formatted feedback
    prompt = f"""You are an expert language tutor. Analyze this journal entry and provide comprehensive feedback in JSON format.

Journal entry: "{text}"

Provide your feedback with the following fields:
- corrected: A version with grammar and spelling corrected
- rewrite: A more natural/native-like rewrite that sounds fluent
- fluency_score: An integer score between 0-100
- tone: The emotional tone detected (one word like "Reflective", "Confident", "Neutral", etc.)
- translation: Translation to English
- explanation: Brief explanation of main grammar issues or improvement suggestions

Return ONLY the JSON with no other text."""

    # Generate text with the Mistral model
    response = generate_text_with_transformers(prompt, model, tokenizer)
    
    # Extract the JSON part from the response
    json_start = response.find('{')
    json_end = response.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        json_str = response[json_start:json_end]
        feedback = json.loads(json_str)
    else:
        raise ValueError("No valid JSON found in response")
    
    # Check for required fields and provide defaults if missing
    required_fields = ["corrected", "rewrite", "fluency_score", "tone", "translation", "explanation"]
    for field in required_fields:
        if field not in feedback:
            if field == "fluency_score":
                feedback[field] = 70
            elif field == "tone":
                feedback[field] = "Neutral"
            elif field == "explanation":
                feedback[field] = "No explanation provided."
            else:
                feedback[field] = text
    
    return feedback


def analyze_entry_mock(text: str) -> Dict[str, Any]:
    """
    Mock function to analyze a journal entry.
    
    Args:
        text: The journal entry text to analyze
        
    Returns:
        Dict: Dictionary with all feedback dimensions
    """
    logger.info(f"[MOCK] Analyzing journal entry: {text[:50]}...")
    
    # Parse the prompt to extract any apparent errors for the mock
    has_errors = any(word in text.lower() for word in ["goed", "thinked", "buyed", "peoples"])
    
    # Create a mock JSON response
    feedback = {
        "corrected": text.replace("goed", "went").replace("thinked", "thought").replace("buyed", "bought").replace("peoples", "people"),
        "rewrite": f"Yesterday I went to the store to buy some food. The weather was nice and I saw many people outside. I thought about my weekend plans and I'm excited.",
        "fluency_score": random.randint(60, 85) if has_errors else random.randint(85, 95),
        "tone": random.choice(["Reflective", "Confident", "Neutral"]),
        "translation": f"This is a mock translation of: {text}",
        "explanation": "This is a mock analysis. The text contains some common grammatical errors: 'goed' should be 'went', 'thinked' should be 'thought', etc." if has_errors else "This text is mostly correct with good grammar and structure."
    }
    
    return feedback


def analyze_entry(text: str) -> Dict[str, Any]:
    """
    Analyze a journal entry using the Mistral model to provide comprehensive
    language feedback.
    
    Args:
        text: The journal entry text to analyze
        
    Returns:
        Dict: Dictionary with all feedback dimensions
    """
    try:
        # Check if we should use transformers or mock
        if TRANSFORMERS_AVAILABLE and not USE_TRANSFORMERS_ONLY:
            # Load model and tokenizer
            model, tokenizer = load_model()
            
            # Check if we got real model and tokenizer or mock objects
            if isinstance(model, str) and model == "mock_model":
                return analyze_entry_mock(text)
            
            # Use real implementation
            return analyze_entry_with_transformers(text, model, tokenizer)
        else:
            # Use mock implementation
            return analyze_entry_mock(text)
    
    except Exception as e:
        logger.error(f"Error analyzing entry with Mistral: {str(e)}, falling back to mock")
        return analyze_entry_mock(text) 
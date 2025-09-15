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


def analyze_entry_with_transformers(text: str, language: str, model, tokenizer) -> Dict[str, Any]:
    """
    Analyze the entry text using the Mistral model via transformers.
    Generates grammar correction, rewrite, fluency score, tone, and translation.

    Args:
        text: The journal entry text.
        language: The language of the journal entry.
        model: Pre-loaded model.
        tokenizer: Pre-loaded tokenizer.

    Returns:
        A dictionary containing all feedback components.
    """
    logger.info(f"Analyzing text (transformers): '{text[:50]}...' in language: {language}")

    # Construct a detailed prompt for Mistral
    # TODO: Refine this prompt for better results and ensure it uses the 'language' parameter.
    # For example, explicitly ask for feedback *for a {language} learner*.
    prompt = f""""Analyze the following text written in {language} by a language learner.
Provide the following feedback in a JSON format:
1.  "corrected_text": "The corrected version of the text."
2.  "fluent_rewrite": "A more fluent, native-sounding version of the text."
3.  "fluency_score": An integer score from 0 to 100 (0=beginner, 100=native-like).
4.  "tone_analysis": A brief description of the tone/emotion (e.g., "neutral", "happy", "frustrated").
5.  "target_language_translation": "Translate the original text to English. If the original text is already in English, translate it to French."
6.  "explanation_of_changes": "Briefly explain the most important corrections or changes made."

Original text:
"{text}"

JSON Feedback:
"""

    generated_json_str = generate_text(prompt, model=model, tokenizer=tokenizer, max_tokens=1500)
    
    logger.debug(f"Raw Mistral output: {generated_json_str}")

    try:
        # Attempt to parse the JSON from the model's output
        # The model might return text before or after the JSON block, so we need to extract it.
        json_start = generated_json_str.find('{')
        json_end = generated_json_str.rfind('}') + 1
        if json_start != -1 and json_end != -1 and json_start < json_end:
            feedback_json_str = generated_json_str[json_start:json_end]
            feedback = json.loads(feedback_json_str)
            
            # Validate and structure the feedback
            # Basic validation for presence of keys, can be expanded
            required_keys = ["corrected_text", "fluent_rewrite", "fluency_score", "tone_analysis", "target_language_translation", "explanation_of_changes"]
            for key in required_keys:
                if key not in feedback:
                    logger.warning(f"Key '{key}' missing in Mistral output. Using default.")
                    # Provide default values for missing keys
                    if key == "fluency_score":
                        feedback[key] = 50 
                    elif key in ["corrected_text", "fluent_rewrite"]:
                         feedback[key] = text # return original if missing
                    else:
                        feedback[key] = f"Default value for missing {key}"


            # Map to the expected output structure (consistent with feedback_engine)
            return {
                "corrected": feedback.get("corrected_text", text),
                "rewrite": feedback.get("fluent_rewrite", text),
                "fluency_score": feedback.get("fluency_score", 50),
                "tone": feedback.get("tone_analysis", "N/A"),
                "translation": feedback.get("target_language_translation", "N/A"), # Consider target lang for translation
                "explanation": feedback.get("explanation_of_changes", "No explanation provided.")
            }
        else:
            logger.error(f"Could not find valid JSON in Mistral output: {generated_json_str}")
            # Fallback to mock if JSON parsing fails badly
            return analyze_entry_mock(text, language) # Pass language here too

    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError for Mistral output: {generated_json_str}. Error: {e}")
        # Fallback to mock if JSON parsing fails
        return analyze_entry_mock(text, language) # Pass language here too
    except Exception as e:
        logger.error(f"Unexpected error processing Mistral output: {e}")
        return analyze_entry_mock(text, language) # Pass language here too


def analyze_entry_mock(text: str, language: str) -> Dict[str, Any]:
    """
    Mock function to simulate AI feedback generation.

    Args:
        text: The journal entry text.
        language: The language of the journal entry.

    Returns:
        A dictionary containing mock feedback components.
    """
    logger.info(f"[MOCK] Analyzing text: '{text[:50]}...' in language: {language}")
    
    # Simulate some language-dependent behavior for mock
    translation_target = "English"
    mock_translation = f"This is a mock translation of the {language} text to {translation_target}."
    if language.lower() == "english":
        translation_target = "French"
        mock_translation = f"Ceci est une traduction fictive du texte anglais en {translation_target}."
    elif language.lower() == "spanish":
        mock_translation = "Esta es una traducción simulada del texto en español al inglés."


    return {
        "corrected": f"[Mock Corrected {language}] {text}",
        "rewrite": f"[Mock Rewritten more fluently in {language}] {text}",
        "fluency_score": random.randint(60, 95),
        "tone": random.choice(["neutral", "positive", "slightly concerned", "formal"]),
        "translation": mock_translation,
        "explanation": f"[Mock Explanation] The anlysis was for {language}. The main point was X, and we corrected Y because Z."
    }


model_instance = None
tokenizer_instance = None

def get_model_and_tokenizer():
    global model_instance, tokenizer_instance
    if model_instance is None or tokenizer_instance is None:
        model_path = download_model() # Ensure model is downloaded
        model_instance, tokenizer_instance = load_model(str(model_path))
    return model_instance, tokenizer_instance

def analyze_entry(text: str, language: str) -> Dict[str, Any]:
    """
    Main function to analyze entry text. Uses real model or mock based on availability.

    Args:
        text: The journal entry text.
        language: The language of the journal entry.

    Returns:
        A dictionary containing all feedback components.
    """
    model, tokenizer = get_model_and_tokenizer()

    if TRANSFORMERS_AVAILABLE and not USE_TRANSFORMERS_ONLY and model != "mock_model":
        try:
            logger.info(f"Using transformers for analysis of text in {language}.")
            return analyze_entry_with_transformers(text, language, model, tokenizer)
        except Exception as e:
            logger.error(f"Error during transformers analysis: {e}. Falling back to mock.")
            return analyze_entry_mock(text, language) # Pass language
    else:
        logger.info(f"Using mock analysis for text in {language}.")
        return analyze_entry_mock(text, language) # Pass language 
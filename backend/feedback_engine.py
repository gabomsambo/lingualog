"""
AI Feedback Engine for LinguaLog.

This module handles interactions with AI models (Mistral, Claude, or OpenAI) to generate
comprehensive language feedback for user journal entries.

Mistral integration is prioritized, with OpenAI as a fallback if available,
and mock data as a final fallback for development and testing environments.
"""
import random
import logging
import json
import time
from typing import Dict, Any, Optional
import httpx

from config import GEMINI_API_KEY, USE_MISTRAL
import mistral_engine # Import the module itself
from gemini_engine import GeminiEngine

# Configure logger
logger = logging.getLogger(__name__)

# Constants for API configuration
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-3.5-turbo"
REQUEST_TIMEOUT = 15.0  # seconds

# Initialize Gemini engine if not using Mistral
gemini_ai_engine = None
if not USE_MISTRAL:
    try:
        gemini_ai_engine = GeminiEngine()
        logger.info("GeminiEngine initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize GeminiEngine: {e}")
        gemini_ai_engine = None # Ensure it's None if init fails


def generate_feedback(entry_text: str, language: str) -> Dict[str, Any]:
    """
    Generate comprehensive language feedback for journal entry text.
    
    Args:
        entry_text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        Dictionary containing various feedback dimensions:
        - corrected: Grammar-corrected version
        - rewritten: Native-like rewrite
        - score: Fluency score (0-100)
        - tone: Detected emotional tone
        - translation: Direct translation
        - explanation: Optional explanation of mistakes
    """
    # Call analyze_entry to get all dimensions of feedback
    analysis = analyze_entry(entry_text, language)
    
    # Format the output according to our API contract
    return {
        "corrected": analysis["corrected"],
        "rewritten": analysis["rewrite"],
        "score": analysis["fluency_score"],
        "tone": analysis["tone"],
        "translation": analysis["translation"],
        "explanation": analysis.get("explanation", "No detailed explanation available.")
    }


def analyze_entry(text: str, language: str) -> Dict[str, Any]:
    """
    Generate comprehensive language feedback for a journal entry.
    
    Args:
        text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        Dictionary with all feedback dimensions
    """
    # Comment out the forced mock for actual testing
    # logger.info("FORCED MOCK: Generating mock feedback data for debugging.")
    # return analyze_with_mock(text, language)

    try:
        if USE_MISTRAL:
            try:
                logger.info("Generating feedback using Mistral model")
                return mistral_engine.analyze_entry(text) # Pass language if/when mistral_engine supports it
            except Exception as e:
                logger.error(f"Error using Mistral: {str(e)}. Trying fallback.")
                # Fall through to Gemini or mock if Mistral fails
        
        # Try Gemini if not using Mistral OR if Mistral failed and Gemini engine is available
        if not USE_MISTRAL or (USE_MISTRAL and gemini_ai_engine): # Adjusted condition for fallback
            if gemini_ai_engine:
                try:
                    logger.info("Generating feedback using Gemini model")
                    return gemini_ai_engine.analyze_text(text, language)
                except Exception as e:
                    logger.error(f"Error using Gemini API: {str(e)}. Falling back to mock data.")
            else:
                logger.warning("Gemini engine not initialized, and it was the selected or fallback option.")
                
        # Fall back to mock data as a last resort
        logger.warning("Falling back to mock data as no primary AI engine is available or operational.")
        return analyze_with_mock(text, language)
        
    except Exception as e:
        logger.error(f"Critical error in analyze_entry: {str(e)}. Falling back to mock data.")
        return analyze_with_mock(text, language)


def analyze_with_openai(text: str) -> Dict[str, Any]: # This function should be reviewed/removed if Gemini is the sole non-Mistral provider
    """
    Analyze text using OpenAI API.
    
    Args:
        text: The journal entry text to analyze
        
    Returns:
        Dictionary with feedback dimensions
        
    Raises:
        Exception: If API call fails or times out
    """
    # The system prompt that guides the AI to provide structured language feedback
    system_prompt = """
    You are an expert language tutor. Analyze the journal entry and provide comprehensive feedback
    in JSON format with the following fields:
    - corrected: A version with grammar and spelling corrected
    - rewrite: A more natural/native-like rewrite that sounds fluent
    - fluency_score: An integer score between 0-100
    - tone: The emotional tone detected (one of "Reflective", "Confident", "Neutral", or other appropriate label)
    - translation: Translation to English
    - explanation: Brief explanation of main grammar issues or improvement suggestions

    Return ONLY the JSON with no other text.
    """
    
    # Prepare the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_API_KEY}"
    }
    
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.7
    }
    
    # Make the API request with timeout
    try:
        start_time = time.time()
        with httpx.Client() as client:
            response = client.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
        
        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            raise Exception(f"API request failed with status {response.status_code}")
        
        # Parse the response
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse the JSON content
        try:
            feedback = json.loads(content)
            
            # Make sure all required fields are present
            required_fields = ["corrected", "rewrite", "fluency_score", "tone", "translation"]
            for field in required_fields:
                if field not in feedback:
                    logger.warning(f"Missing {field} in API response, adding default value")
                    if field == "fluency_score":
                        feedback[field] = 70
                    else:
                        feedback[field] = text if field != "tone" else "Neutral"
            
            # Log the successful API call
            logger.info(f"LLM feedback generated in {time.time() - start_time:.2f} seconds")
            return feedback
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from API response: {content}")
            raise Exception("API returned invalid JSON")
            
    except httpx.TimeoutException:
        logger.error(f"API request timed out after {REQUEST_TIMEOUT} seconds")
        raise Exception(f"API request timed out after {REQUEST_TIMEOUT} seconds")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        raise


def analyze_with_mock(text: str, language: str) -> Dict[str, Any]:
    """
    Mock AI analysis of a journal entry.
    
    This function simulates the behavior of an AI language model analyzing text
    without actually making API calls. It generates plausible but fake feedback
    that maintains the structure expected by the application.
    
    Args:
        text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        dict: {
            "corrected": same text with minor modifications,
            "rewrite": fake rewrite of the original text,
            "fluency_score": random int between 70-100,
            "tone": randomly selected tone label,
            "translation": pretend translation of the text
        }
    """
    # Generate a random fluency score between 70 and 100
    fluency_score = random.randint(70, 100)
    
    # Randomly select a tone from predefined options
    possible_tones = ["Reflective", "Confident", "Neutral"]
    tone = random.choice(possible_tones)
    
    # Create a simple placeholder for the rewritten version
    rewrite = f"{text} (more natural)"
    
    # Create a placeholder for translation
    translation = f"Translated version of: {text}"
    
    # Add a simple message to indicate this is mock data
    explanation = "This is mock feedback for development. In production, real AI feedback will be provided."
    
    # Simulate language-specific elements if needed, e.g., for translation
    translation_target_lang = "es" # Example
    if language == "es":
        translation_target_lang = "en"

    # Return the mocked analysis dictionary
    return {
        "corrected": f"[Mock Corrected] {text}",
        "rewrite": f"[Mock Rewritten] {text} (more fluently)",
        "fluency_score": random.randint(70, 95),
        "tone": random.choice(["Reflective", "Confident", "Neutral", "Inquisitive"]),
        "translation": {translation_target_lang: f"[Mock Translation to {translation_target_lang.upper()}] {text}"},
        "explanation": f"[Mock Explanation] Consider using more varied sentence structures. The word '{random.choice(text.split() if text.split() else ['example'])}' was used well.",
        # Ensuring the mock provides the structure expected by the frontend
        "corrected_text": f"[Mock Corrected Text] {text}",
        "vocabulary_suggestions": [
            {"word": "good", "suggestion": "excellent", "context": "This is a good example."}
        ],
        "tone_emotion": [random.choice(["neutral", "happy", "analytical"])]
    }


# TODO: Implement actual AI model API calls in production version 
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
from typing import Dict, Any, Optional, List
import httpx
import asyncio

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

# Prompts for word enrichment - can be refined or moved to a config/prompts file
PROMPTS_WORD_ENRICHMENT = {
    "ai_example_sentences": "Provide 3 distinct example sentences for the word '{term}' in {language}. Each sentence should clearly demonstrate a common usage of the word. Ensure the sentences are suitable for a language learner of intermediate level. Return as a JSON list of strings.",
    "synonyms_antonyms": "For the word '{term}' in {language}:\n1. List up to 5 common synonyms.\n2. List up to 5 common antonyms.\nIf antonyms are not applicable or very rare, an empty list or null for antonyms is fine. Provide the output as a JSON object with keys 'synonyms' (list of strings) and 'antonyms' (list of strings).",
    "related_phrases": "List up to 5 common phrases or collocations that use the word '{term}' in {language}. Return as a JSON list of strings.",
    "cultural_note": "Provide a brief cultural note or usage insight for the word '{term}' in {target_language}. This could include its connotations, common contexts, or idiomatic usage. If no strong cultural note, provide insight into its typical register (formal/informal). Keep it concise (1-2 sentences).",
    "emotion_tone": "Analyze the typical emotion or tone associated with the word '{term}' when used in {target_language}. Describe it briefly (e.g., neutral, positive, negative, formal, informal). If multiple tones, mention common ones. Keep it concise (1 phrase or sentence).",
    "mnemonic": "Create a simple and memorable mnemonic, metaphor, or a short story (1-2 sentences) to help a language learner remember the meaning of the word '{term}' in {target_language}. Keep it concise and easy to understand."
}

_mistral_model = None
_mistral_tokenizer = None

def _get_mistral_components():
    global _mistral_model, _mistral_tokenizer
    if not _mistral_model or not _mistral_tokenizer:
        if mistral_engine.TRANSFORMERS_AVAILABLE and not mistral_engine.USE_TRANSFORMERS_ONLY: 
            logger.info("Loading Mistral model and tokenizer for word enrichment...")
            _mistral_model, _mistral_tokenizer = mistral_engine.load_model() 
        else:
            logger.info("Mistral (transformers) not fully available or set to mock for word enrichment.")
            _mistral_model, _mistral_tokenizer = "mock_model", "mock_tokenizer" 
    return _mistral_model, _mistral_tokenizer


async def generate_feedback(entry_text: str, language: str) -> Dict[str, Any]:
    """
    Generate comprehensive language feedback for journal entry text.
    
    Args:
        entry_text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        Dictionary containing various feedback dimensions including:
        - corrected: Grammar-corrected version
        - rewritten: Native-like rewrite
        - score: Fluency score (0-100)
        - rubric: Detailed scores for grammar, vocabulary, complexity
        - tone: Detected emotional tone
        - translation: Direct translation
        - explanation: Optional explanation of mistakes
        - grammar_suggestions: List of specific grammar fixes
        - new_words: List of new or notable vocabulary words
    """
    analysis = await analyze_entry(entry_text, language)
    
    # Format the output according to our API contract (defined by FeedbackResponse model)
    return {
        "corrected": analysis.get("corrected", entry_text),
        "rewritten": analysis.get("rewrite", entry_text),
        "score": analysis.get("score", 0),
        "rubric": analysis.get("rubric", {"grammar": 0, "vocabulary": 0, "complexity": 0}),
        "tone": analysis.get("tone", "Neutral"),
        "translation": analysis.get("translation", "Translation not available."),
        "explanation": analysis.get("explanation", "No detailed explanation available."),
        "grammar_suggestions": analysis.get("grammar_suggestions", []),
        "new_words": analysis.get("new_words", [])
    }


async def analyze_entry(text: str, language: str) -> Dict[str, Any]:
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
                return mistral_engine.analyze_entry(text, language) # Pass language if/when mistral_engine supports it
            except Exception as e:
                logger.error(f"Error using Mistral: {str(e)}. Trying fallback.")
                # Fall through to Gemini or mock if Mistral fails
        
        # Try Gemini if not using Mistral OR if Mistral failed and Gemini engine is available
        if not USE_MISTRAL or (USE_MISTRAL and gemini_ai_engine): # Adjusted condition for fallback
            if gemini_ai_engine:
                try:
                    logger.info("Generating feedback using Gemini model")
                    return await gemini_ai_engine.analyze_text(text, language)
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


async def analyze_with_openai(text: str) -> Dict[str, Any]: # This function should be reviewed/removed if Gemini is the sole non-Mistral provider
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
    that maintains the structure expected by the application, including new fields.
    
    Args:
        text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        dict: Mock feedback including corrected text, rewrite, score, rubric, 
              tone, translation, explanation, grammar suggestions, and new words.
    """
    fluency_score = random.randint(70, 95)
    possible_tones = ["Reflective", "Confident", "Neutral", "Inquisitive"]
    tone = random.choice(possible_tones)
    translation_target_lang = "en" if language != "en" else "fr" # Example: translate to EN, or FR if input is EN

    mock_rubric = {
        "grammar": random.randint(60, 90),
        "vocabulary": random.randint(65, 95),
        "complexity": random.randint(50, 85)
    }

    mock_suggestions = []
    if len(text.split()) > 3:
        original_snippet = " ".join(text.split()[:3]) # Take first 3 words as an example
        mock_suggestions.append({
            "id": "mock-sugg-1",
            "original": original_snippet,
            "corrected": f"[Mock Corrected Snippet] {original_snippet}",
            "note": "This is a mock suggestion. Consider rephrasing for clarity."
        })
    if len(text.split()) > 6:
        original_snippet_2 = " ".join(text.split()[3:6]) # Take next 3 words
        mock_suggestions.append({
            "id": "mock-sugg-2",
            "original": original_snippet_2,
            "corrected": f"[Mock Corrected Snippet 2] {original_snippet_2}",
            "note": "Another mock suggestion about word choice."
        })

    mock_new_words = []
    words_in_text = list(set(filter(None, text.lower().replace(".","").replace(",","").split())))
    if words_in_text:
        selected_word = random.choice(words_in_text)
        mock_new_words.append({
            "id": "mock-word-1",
            "term": selected_word,
            "reading": None,
            "pos": random.choice(["noun", "verb", "adjective", "adverb"]),
            "definition": f"This is a mock definition for '{selected_word}'.",
            "example": f"A mock example sentence using '{selected_word}'.",
            "proficiency": random.choice(["beginner", "intermediate", "advanced"])
        })
    if len(words_in_text) > 1:
        selected_word_2 = random.choice([w for w in words_in_text if w != selected_word])
        mock_new_words.append({
            "id": "mock-word-2",
            "term": selected_word_2,
            "reading": None,
            "pos": random.choice(["noun", "verb", "adjective"]),
            "definition": f"Mock definition for the word '{selected_word_2}'.",
            "example": f"Another example, this time with '{selected_word_2}'.",
            "proficiency": random.choice(["A2", "B1", "C1"])
        })

    return {
        "corrected": f"[Mock Corrected] {text}",
        "rewrite": f"[Mock Rewritten] {text} (more fluently and naturally)",
        "score": fluency_score,
        "rubric": mock_rubric,
        "tone": tone,
        "translation": f"[Mock Translation to {translation_target_lang.upper()}] {text}",
        "explanation": f"[Mock Explanation] This is a mock explanation. The text shows good potential. The word '{random.choice(words_in_text if words_in_text else ['example'])}' was used effectively.",
        "grammar_suggestions": mock_suggestions,
        "new_words": mock_new_words,
        # Keep these for potential partial frontend compatibility if it expects them, though they are not in the new FeedbackResponse
        "corrected_text": f"[Mock Corrected Text] {text}", 
        "vocabulary_suggestions": [ # This seems to be an old field, new_words is more structured
            {"word": "good", "suggestion": "excellent", "context": "This is a good example."}
        ],
        "tone_emotion": [tone.lower()] # Old field, new 'tone' is a string
    }


async def generate_word_enrichment_details(term: str, language: str) -> Dict[str, Any]:
    """
    Generates various AI-powered enrichment details for a given word and language.
    Orchestrates calls to the configured AI engine (Mistral or Gemini).
    """
    enrichment_data = {}
    tasks = []

    formatted_prompts = {
        key: prompt_template.format(term=term, language=language, target_language=language)
        for key, prompt_template in PROMPTS_WORD_ENRICHMENT.items()
    }

    async def get_field_data_gemini(field_name: str, prompt: str) -> Any:
        try:
            if field_name in ["ai_example_sentences", "synonyms_antonyms", "related_phrases"]:
                return await gemini_ai_engine.generate_custom_json(prompt)
            else:
                return await gemini_ai_engine.generate_custom_text(prompt)
        except Exception as e:
            logger.error(f"Gemini: Error generating field '{field_name}' for term '{term}': {e}")
            return None

    def get_field_data_mistral(field_name: str, prompt: str, model, tokenizer) -> Any:
        try:
            response_str = mistral_engine.generate_text(prompt, model=model, tokenizer=tokenizer, max_tokens=300) 
            if field_name in ["ai_example_sentences", "synonyms_antonyms", "related_phrases"]:
                try:
                    return json.loads(response_str) 
                except json.JSONDecodeError as je:
                    logger.error(f"Mistral: Failed to parse JSON for field '{field_name}' for term '{term}': {je}. Response: {response_str}")
                    if field_name == "synonyms_antonyms": return {"synonyms": [], "antonyms": []}
                    return [] 
            else: 
                return response_str
        except Exception as e:
            logger.error(f"Mistral: Error generating field '{field_name}' for term '{term}': {e}")
            return None

    if USE_MISTRAL:
        logger.info(f"Using Mistral for word enrichment of '{term}' in {language}")
        m_model, m_tokenizer = _get_mistral_components()
        for field, prompt in formatted_prompts.items():
            enrichment_data[field] = get_field_data_mistral(field, prompt, m_model, m_tokenizer)
            await asyncio.sleep(0.1) 
    elif gemini_ai_engine:
        logger.info(f"Using Gemini for word enrichment of '{term}' in {language}")
        for field, prompt in formatted_prompts.items():
            tasks.append(get_field_data_gemini(field, prompt))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, field in enumerate(formatted_prompts.keys()):
            if isinstance(results[i], Exception):
                logger.error(f"Gemini: Exception for field '{field}' during asyncio.gather: {results[i]}")
                enrichment_data[field] = None 
            else:
                enrichment_data[field] = results[i]
    else:
        logger.warning(f"No AI engine (Mistral or Gemini) available for word enrichment of '{term}'. Returning empty.")
        enrichment_data = {
            "ai_example_sentences": [],
            "synonyms_antonyms": {"synonyms": [], "antonyms": []},
            "related_phrases": [],
            "cultural_note": "AI enrichment not available.",
            "emotion_tone": "N/A",
            "mnemonic": "AI enrichment not available."
        }
        return enrichment_data

    if enrichment_data.get("synonyms_antonyms") is None:
        enrichment_data["synonyms_antonyms"] = {"synonyms": [], "antonyms": []}

    logger.info(f"Completed word enrichment for '{term}': {enrichment_data}")
    return enrichment_data


# TODO: Implement actual AI model API calls in production version 
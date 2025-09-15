# backend/gemini_engine.py
"""
Handles interactions with the Google Gemini API for AI feedback.
"""

import os
import json
import logging # Added logger
import asyncio # Added for async operations
from typing import Dict, Any, List, Union # Added List and Union

from config import GEMINI_API_KEY, validate_env_vars

import google.generativeai as genai # Uncommented and will be used

logger = logging.getLogger(__name__) # Added logger instance

class GeminiEngine:
    """Engine to generate feedback using Google Gemini."""

    def __init__(self):
        """Initializes the GeminiEngine, configuring the API key."""
        if not validate_env_vars(): # This primarily checks Supabase vars, GEMINI_API_KEY is checked next
            # Log a warning but don't necessarily raise error if only Supabase vars are missing,
            # as GeminiEngine might be used independently in some contexts.
            logger.warning("Potential missing Supabase environment variables during GeminiEngine init.")
        
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set. Cannot initialize GeminiEngine.")
            raise ValueError("GEMINI_API_KEY is not set. Cannot initialize GeminiEngine.")
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Using gemini-1.5-flash as it's fast and good for chat/structured output.
            # Consider gemini-pro if higher quality is needed and latency is less critical.
            self.model = genai.GenerativeModel('gemini-1.5-flash') 
            logger.info("GeminiEngine initialized successfully with gemini-1.5-flash model.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise ConnectionError(f"Failed to initialize Gemini model: {e}")

    async def analyze_text(self, text: str, language: str) -> Dict[str, Any]:
        """
        Analyzes the given text using the Gemini API.

        Args:
            text: The text to analyze.
            language: The language of the text.

        Returns:
            A dictionary containing AI-generated feedback.
            Includes keys like 'corrected', 'rewrite', 'score', 'tone', 'translation', 
            'explanation', 'rubric', 'grammar_suggestions', 'new_words'.
        """
        logger.info(f"GeminiEngine: Analyzing text (length: {len(text)}, language: {language})")

        # Construct the prompt for Gemini
        # Specifying JSON output directly in the prompt is crucial.
        prompt = f"""\
You are an expert language tutor. Analyze the following journal entry written in {language} by a language learner.
Provide comprehensive feedback STRICTLY in JSON format with NO OTHER TEXT OR MARKDOWN WRAPPERS.
The JSON object must have the following top-level keys and adhere to the specified structures:

- "corrected": "A version of the original text with grammar and spelling corrected." (string)
- "rewrite": "A more natural/native-like rewrite of the original text that sounds fluent." (string)
- "score": An overall fluency score as an integer between 0 and 100. (integer)
- "rubric": {{
    "grammar": An integer score for grammar (0-100). (integer),
    "vocabulary": An integer score for vocabulary (0-100). (integer),
    "complexity": An integer score for sentence/idea complexity (0-100). (integer)
  }} (object)
- "tone": "A one or two-word description of the emotional tone detected (e.g., 'Reflective', 'Confident', 'Neutral', 'Anxious')." (string)
- "translation": "Translate the original text to English. If the original text is already in English, translate it to French." (string)
- "explanation": "A brief explanation of the main grammar issues, stylistic improvements, or positive feedback. Focus on 1-2 key points." (string)
- "grammar_suggestions": [
    {{
      "original": "The original problematic text snippet.", (string)
      "corrected": "The suggested correction for the snippet.", (string)
      "note": "A brief note explaining the grammar rule or reason for correction." (string)
    }}
    //... (list of 0 to 5 suggestion objects)
  ] (array of objects)
- "new_words": [
    {{
      "term": "The new or notable word/phrase.", (string)
      "reading": "(Optional) Pronunciation or reading, e.g., for Japanese Kanji. Null if not applicable.", (string or null)
      "pos": "Part of speech (e.g., 'noun', 'verb', 'adjective').", (string)
      "definition": "A concise definition of the word in English.", (string)
      "example": "An example sentence using the word, ideally from the original text or a variation.", (string)
      "proficiency": "Estimated proficiency level (e.g., 'beginner', 'intermediate', 'advanced', 'A1', 'B2')." (string)
    }}
    //... (list of 0 to 5 new word objects)
  ] (array of objects)

Original text:
"{text}"

JSON Feedback:
"""

        try:
            # Generation config for structured output
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" # Request JSON output
            )
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            logger.debug(f"Raw Gemini API response text: {response.text}")
            
            # The response.text should be the JSON string.
            feedback_json = json.loads(response.text)

            # Define expected structure with defaults for robust parsing
            processed_feedback = {
                "corrected": feedback_json.get("corrected", f"Content for 'corrected' not provided by AI."),
                "rewrite": feedback_json.get("rewrite", f"Content for 'rewrite' not provided by AI."),
                "score": feedback_json.get("score", 50),
                "tone": feedback_json.get("tone", "Neutral"),
                "translation": feedback_json.get("translation", f"Content for 'translation' not provided by AI."),
                "explanation": feedback_json.get("explanation", "No explanation provided by AI."),
                "rubric": feedback_json.get("rubric", {"grammar": 0, "vocabulary": 0, "complexity": 0}),
                "grammar_suggestions": feedback_json.get("grammar_suggestions", []),
                "new_words": feedback_json.get("new_words", [])
            }

            # Validate score
            if not isinstance(processed_feedback["score"], int) or not (0 <= processed_feedback["score"] <= 100):
                logger.warning(f"Invalid fluency score from Gemini: {processed_feedback['score']}. Defaulting to 50.")
                processed_feedback["score"] = 50
            
            # Validate rubric structure and scores
            rubric = processed_feedback["rubric"]
            if not isinstance(rubric, dict) or any(key not in rubric for key in ["grammar", "vocabulary", "complexity"]):
                logger.warning(f"Invalid rubric structure from Gemini: {rubric}. Using default.")
                processed_feedback["rubric"] = {"grammar": 0, "vocabulary": 0, "complexity": 0}
            else:
                for key in ["grammar", "vocabulary", "complexity"]:
                    if not isinstance(rubric.get(key), int) or not (0 <= rubric.get(key, 0) <= 100):
                        logger.warning(f"Invalid rubric score for '{key}': {rubric.get(key)}. Defaulting to 0.")
                        rubric[key] = 0
            
            # Validate grammar_suggestions (list of dicts with required keys)
            suggestions = processed_feedback["grammar_suggestions"]
            if not isinstance(suggestions, list):
                logger.warning(f"grammar_suggestions from Gemini was not a list: {suggestions}. Defaulting to empty list.")
                processed_feedback["grammar_suggestions"] = []
            else:
                valid_suggestions = []
                for sug in suggestions:
                    if isinstance(sug, dict) and all(k in sug for k in ["original", "corrected", "note"]):
                        valid_suggestions.append(sug)
                    else:
                        logger.warning(f"Invalid suggestion object from Gemini: {sug}. Skipping.")
                processed_feedback["grammar_suggestions"] = valid_suggestions

            # Validate new_words (list of dicts with required keys)
            words = processed_feedback["new_words"]
            if not isinstance(words, list):
                logger.warning(f"new_words from Gemini was not a list: {words}. Defaulting to empty list.")
                processed_feedback["new_words"] = []
            else:
                valid_words = []
                for word in words:
                    if isinstance(word, dict) and all(k in word for k in ["term", "pos", "definition", "example", "proficiency"]):
                        valid_words.append(word)
                    else:
                        logger.warning(f"Invalid new_word object from Gemini: {word}. Skipping.")
                processed_feedback["new_words"] = valid_words

            logger.info("Successfully received and processed feedback from Gemini API.")
            return processed_feedback

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {response.text}. Error: {e}")
            # Fallback to a structured mock if JSON parsing fails
            return await self._get_error_fallback(text, language, "JSON parsing error from AI.")
        except Exception as e:
            logger.error(f"Error calling Gemini API or processing its response: {e}")
            # Fallback for other errors
            return await self._get_error_fallback(text, language, f"API call/processing error: {str(e)}")

    async def _get_error_fallback(self, text: str, language: str, error_msg: str) -> Dict[str, Any]:
        """Provides a structured fallback response in case of errors."""
        logger.warning(f"Using error fallback for GeminiEngine due to: {error_msg}")
        return {
            "corrected": text, # Return original text
            "rewrite": f"Could not generate rewrite due to an error: {error_msg}",
            "score": 0,
            "rubric": {"grammar": 0, "vocabulary": 0, "complexity": 0},
            "tone": "Error",
            "translation": f"Could not generate translation due to an error: {error_msg}",
            "explanation": f"An error occurred while generating AI feedback: {error_msg}. Please try again.",
            "grammar_suggestions": [],
            "new_words": []
        }

    async def generate_custom_text(self, prompt: str) -> str:
        """
        Generates text content based on a custom prompt using the Gemini model.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            The generated text as a string.

        Raises:
            Exception: If the API call fails.
        """
        logger.info(f"GeminiEngine: Generating custom text (prompt length: {len(prompt)})")
        try:
            # Use generate_content_async for async operation
            response = await self.model.generate_content_async(prompt) 
            logger.debug(f"Raw Gemini API response for custom text: {response.text}")
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini API for custom text prompt: {e}")
            raise ConnectionError(f"Gemini API call failed for custom text: {str(e)}")

    async def generate_custom_json(self, prompt: str) -> Union[Dict[str, Any], List[Any]]: # Return type can be List for e.g. list of sentences
        """
        Generates JSON content based on a custom prompt using the Gemini model.
        The prompt must instruct the model to return JSON.

        Args:
            prompt: The prompt to send to the model, instructing it to return JSON.

        Returns:
            The generated JSON as a dictionary or list.

        Raises:
            Exception: If the API call fails or JSON parsing fails.
        """
        logger.info(f"GeminiEngine: Generating custom JSON (prompt length: {len(prompt)})")
        try:
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            logger.debug(f"Raw Gemini API response for custom JSON: {response.text}")
            # The response.text should be the JSON string.
            loaded_json = json.loads(response.text)
            if not isinstance(loaded_json, (dict, list)):
                logger.error(f"Gemini API returned JSON but it was not a dict or list: {type(loaded_json)}")
                raise ValueError("Gemini API did not return a JSON object or array.")
            return loaded_json
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini custom_json response: {response.text}. Error: {e}")
            raise ValueError(f"Gemini API did not return valid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling Gemini API for custom JSON prompt: {e}")
            raise ConnectionError(f"Gemini API call failed for custom JSON: {str(e)}")

if __name__ == '__main__':
    # Example usage (requires .env to be set up with GEMINI_API_KEY)
    print("Testing GeminiEngine (Full Implementation)...")
    # Configure basic logging for testing
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting GeminiEngine test script.")

    # Ensure .env is loaded if this script is run directly for testing
    from dotenv import load_dotenv
    from pathlib import Path # Ensure Path is imported for .env loading
    dotenv_path = Path(__file__).resolve().parent.parent / ".env" 
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path) # Specify dotenv_path
        logger.info(f".env file loaded from {dotenv_path}")
    else:
        logger.warning(f".env file not found at {dotenv_path}. GEMINI_API_KEY must be set in environment.")

    # Re-check GEMINI_API_KEY after attempting to load .env
    GEMINI_API_KEY_TEST = os.getenv("GEMINI_API_KEY") # Use a different var to avoid conflict with global
    if not GEMINI_API_KEY_TEST:
        logger.error("GEMINI_API_KEY not found after trying to load .env. Please set it.")
    else:
        logger.info("GEMINI_API_KEY found for test.")
        try:
            engine = GeminiEngine() # Will use the globally configured GEMINI_API_KEY
            sample_text = "Je vais au magasin hier. J'ai acheter une pomme. Elle etre rouge."
            sample_language = "French"
            logger.info(f"Sending sample text to Gemini: '{sample_text}'")
            feedback = engine.analyze_text(sample_text, sample_language)
            
            print("\\n--- Feedback Received ---")
            if feedback:
                # Pretty print the JSON for better readability
                print(json.dumps(feedback, indent=2, ensure_ascii=False))
            else:
                print("  No feedback received or an error occurred.")
            print("--- End of Feedback ---")

        except Exception as e:
            print(f"Error during GeminiEngine test: {e}")
            logger.error(f"Critical error during GeminiEngine __main__ test: {e}", exc_info=True) 
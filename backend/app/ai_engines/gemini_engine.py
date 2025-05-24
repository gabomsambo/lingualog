import logging
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import json
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

class GeminiEngine:
    def __init__(self, model_name: Optional[str] = None):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured in .env or environment.")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model_name = model_name or "gemini-1.5-flash-latest" # Sensible default
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"GeminiEngine initialized with model: {self.model_name}")

    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Helper function to call Gemini API and handle common errors."""
        try:
            response = await self.model.generate_content_async(prompt)
            # TODO: Add more sophisticated error checking based on response.prompt_feedback if needed
            # https://ai.google.dev/api/python/google/generativeai/types/GenerateContentResponse#prompt_feedback
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            logger.warning(f"Gemini API returned no content or unexpected structure. Prompt: {prompt[:100]}...")
            return None
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}. Prompt: {prompt[:100]}...", exc_info=True)
            return None

    async def analyze_journal_entry(self, entry_text: str, language: str) -> Dict[str, Any]:
        """Analyzes a journal entry for grammar, fluency, tone, etc."""
        # This is a placeholder. Implement the actual prompt and parsing.
        logger.info(f"GeminiEngine: Analyzing journal entry in {language}.")
        prompt = (
            f"Analyze the following journal entry written in {language}. "
            f"Provide: 1. Corrected text. 2. Fluent rewrite. 3. Overall fluency score (0-100). "
            f"4. Tone analysis (e.g., {{'joy': 0.8}}). 5. Style analysis (e.g., {{'formal': 0.7}}). "
            f"6. Specific grammar suggestions (list of dicts: {{'original': '', 'suggestion': '', 'explanation': ''}}). "
            f"7. Vocabulary suggestions. 8. List of new/noteworthy words used. 9. General explanation of changes."
            f"Format the entire output as a single JSON object with keys: corrected_content, fluent_rewrite, overall_score, tone_analysis, style_analysis, grammar_suggestions, vocabulary_suggestions, new_words_used, explanation_of_changes."
            f"\n\nJournal Entry:\n{entry_text}"
        )
        raw_response = await self._call_gemini_api(prompt)
        if raw_response:
            try:
                # Attempt to strip markdown and parse JSON
                if raw_response.strip().startswith("```json"):
                    json_str = raw_response.strip()[7:-3].strip()
                elif raw_response.strip().startswith("```"):
                    json_str = raw_response.strip()[3:-3].strip()
                else:
                    json_str = raw_response
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini for journal analysis: {e}. Raw: {raw_response}")
                return {} # Return empty dict on parsing failure
        return {}

    async def generate_word_enrichment_details_gemini(self, term: str, language: str) -> Dict[str, Any]:
        """Generates detailed enrichment for a word using Gemini."""
        logger.info(f"GeminiEngine: Generating word enrichment for '{term}' in {language}.")
        prompt = (
            f"Provide comprehensive details for the word/phrase '{term}' in {language}. "
            f"Include: example sentences, definitions (with part of speech), synonyms, antonyms, related phrases, "
            f"a cultural note or usage insight, a pronunciation guide (IPA or common transliteration), alternative forms (if any), "
            f"and common mistakes learners make. Ensure the output is a single JSON object with keys: "
            f"ai_example_sentences (list of strings), ai_definitions (list of dicts with 'part_of_speech' and 'definition'), "
            f"ai_synonyms (list of strings), ai_antonyms (list of strings), ai_related_phrases (list of strings), "
            f"ai_cultural_note (string), ai_pronunciation_guide (string), ai_alternative_forms (list of strings), "
            f"ai_common_mistakes (list of dicts with 'mistake' and 'correction')."
        )
        raw_response = await self._call_gemini_api(prompt)
        if raw_response:
            try:
                if raw_response.strip().startswith("```json"):
                    json_str = raw_response.strip()[7:-3].strip()
                elif raw_response.strip().startswith("```"):
                    json_str = raw_response.strip()[3:-3].strip()
                else:
                    json_str = raw_response
                data = json.loads(json_str)
                data["language"] = language # Add language and source_model to the response
                data["source_model"] = self.model_name
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini for word enrichment: {e}. Raw: {raw_response}")
        # Fallback if API call fails or JSON parsing fails
        return {
            "language": language, "source_model": self.model_name,
            "ai_example_sentences": [], "ai_definitions": [], "ai_synonyms": [], "ai_antonyms": [],
            "ai_related_phrases": [], "ai_cultural_note": "Failed to generate details.",
            "ai_pronunciation_guide": "", "ai_alternative_forms": [], "ai_common_mistakes": []
        }

    async def generate_more_examples_gemini(self, word: str, language: str, existing_examples: Optional[List[str]], target_audience_level: Optional[str], prompt_template: str) -> List[str]:
        logger.info(f"GeminiEngine: Generating more examples for '{word}' in {language} using prompt: {prompt_template[:100]}...")
        raw_response = await self._call_gemini_api(prompt_template)
        if raw_response:
            # Simple split by newline, might need more robust parsing based on actual Gemini output format
            examples = [ex.strip() for ex in raw_response.split('\n') if ex.strip() and ex.strip().lower() != word.lower()]
            # Filter out examples that are just the word itself or too short
            examples = [ex for ex in examples if len(ex) > len(word) + 5]
            logger.debug(f"Gemini raw response for more examples: {raw_response}, Parsed: {examples}")
            return examples
        logger.warning(f"Gemini returned empty text for more examples of '{word}'.")
        return []

    async def generate_eli5_explanation_gemini(self, term: str, language: str, prompt_template: str) -> str:
        logger.info(f"GeminiEngine: Generating ELI5 for '{term}' in {language} using prompt: {prompt_template[:100]}...")
        raw_response = await self._call_gemini_api(prompt_template)
        logger.debug(f"Gemini raw response for ELI5: {raw_response}")
        return raw_response if raw_response else ""

    async def generate_mini_quiz_gemini(self, word: str, language: str, difficulty_level: Optional[str], num_questions: Optional[int], prompt_template: str) -> Optional[Dict[str, Any]]:
        logger.info(f"GeminiEngine: Generating mini-quiz for '{word}' in {language} using prompt: {prompt_template[:100]}...")
        raw_response = await self._call_gemini_api(prompt_template)
        if not raw_response:
            logger.warning(f"Gemini returned empty text for mini-quiz on '{word}'.")
            return None
        
        logger.debug(f"Gemini raw response for mini-quiz: {raw_response}")
        try:
            # Attempt to parse the JSON output, stripping markdown if present
            if raw_response.strip().startswith("```json"):
                json_str = raw_response.strip()[7:-3].strip()
            elif raw_response.strip().startswith("```"):
                json_str = raw_response.strip()[3:-3].strip()
            else:
                json_str = raw_response
            
            quiz_data = json.loads(json_str)
            if "questions" not in quiz_data or not isinstance(quiz_data["questions"], list):
                logger.error(f"Parsed JSON for quiz on '{word}' is missing 'questions' list or it's not a list. Data: {quiz_data}")
                return None
            return quiz_data
        except json.JSONDecodeError as je:
            logger.error(f"Failed to decode JSON response from Gemini for mini-quiz on '{word}'. Error: {je}. Raw text: {raw_response}", exc_info=True)
            return None
        except Exception as e: # Catch any other unexpected error during parsing
            logger.error(f"Unexpected error parsing quiz data for '{word}': {e}. Raw text: {raw_response}", exc_info=True)
            return None

# Example usage (for testing, not part of the class structure)
# ... existing code ... 
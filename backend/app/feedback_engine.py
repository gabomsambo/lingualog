import logging
from typing import Optional, List, Dict, Any

from app.models import (
    AiFeedback, MiniQuizResponse, MiniQuizQuestion # Removed unused models
)
# from config import get_settings # This import is not needed here
from app.ai_engines.gemini_engine import GeminiEngine # Ensure GeminiEngine is imported

logger = logging.getLogger(__name__)

class FeedbackEngine:
    def __init__(self, gemini_engine: GeminiEngine):
        self.gemini_engine = gemini_engine

    async def generate_ai_feedback_for_entry(self, entry_text: str, language: str) -> AiFeedback:
        # ... (existing implementation for journal entry feedback - assumed to be here)
        logger.info(f"FeedbackEngine: Generating AI feedback for entry in {language}.")
        # This would call a method on self.gemini_engine, e.g., self.gemini_engine.analyze_journal_entry(...)
        # For now, returning a placeholder AiFeedback object
        # Actual implementation would populate this based on Gemini output
        raw_feedback = await self.gemini_engine.analyze_journal_entry(
            entry_text=entry_text, 
            language=language
        )
        # Adapt raw_feedback (dict) to AiFeedback model
        # This is a simplified adaptation
        return AiFeedback(**raw_feedback) if raw_feedback else AiFeedback() # Return empty if None

    async def generate_word_enrichment_details(self, term: str, language: str) -> Dict[str, Any]:
        logger.info(f"FeedbackEngine: Generating word enrichment details for '{term}' in {language}.")
        try:
            raw_ai_response = await self.gemini_engine.generate_word_enrichment_details_gemini(term, language)
            # Ensure raw_ai_response is a dict. If Gemini returns None or error, handle it.
            if not raw_ai_response:
                logger.error(f"Gemini engine returned None for word enrichment of '{term}'.")
                # Return a dict that conforms to WordAiCacheBase structure but indicates failure
                return {
                    "language": language,
                    "ai_example_sentences": [],
                    "ai_definitions": [],
                    "ai_synonyms": [],
                    "ai_antonyms": [],
                    "ai_related_phrases": [],
                    "ai_cultural_note": "AI enrichment failed to generate data.",
                    # Populate other WordAiCacheBase fields with defaults
                }
            return raw_ai_response # Return the dictionary as expected by the service
        except Exception as e:
            logger.error(f"Error processing AI response for word enrichment: {e}", exc_info=True)
            return {
                "language": language,
                "ai_example_sentences": [],
                "ai_definitions": [],
                "ai_synonyms": [],
                "ai_antonyms": [],
                "ai_related_phrases": [],
                "ai_cultural_note": f"Error generating AI details: {str(e)}",
            }

    async def generate_additional_examples(self, word: str, language: str, existing_examples: Optional[List[str]] = None, target_audience_level: Optional[str] = "intermediate") -> List[str]:
        """Generates additional example sentences for a word."""
        logger.info(f"FeedbackEngine: Generating additional examples for '{word}' in {language}.")
        try:
            prompt = f"Generate 3 diverse and natural-sounding example sentences for the word '{word}' in {language}."
            if existing_examples:
                prompt += f" Avoid examples similar to these: {'; '.join(existing_examples)}."
            if target_audience_level:
                prompt += f" The examples should be suitable for a {target_audience_level} learner."
            
            new_examples = await self.gemini_engine.generate_more_examples_gemini(word, language, existing_examples, target_audience_level, prompt_template=prompt)
            if not new_examples:
                logger.warning(f"GeminiEngine returned no new examples for '{word}'.")
                return []
            return new_examples
        except Exception as e:
            logger.error(f"Error in FeedbackEngine generating additional examples for '{word}': {e}", exc_info=True)
            return []

    async def generate_eli5_explanation(self, term: str, language:str) -> str:
        """Generates an ELI5 explanation for a term."""
        logger.info(f"FeedbackEngine: Generating ELI5 for '{term}' in {language}.")
        try:
            prompt = f"Explain the term '{term}' in {language} as if you were talking to a 5-year-old. Keep it simple, use analogies if possible, and make it short."
            explanation = await self.gemini_engine.generate_eli5_explanation_gemini(term, language, prompt_template=prompt)
            if not explanation:
                logger.warning(f"GeminiEngine returned no ELI5 explanation for '{term}'.")
                return "Could not generate an explanation at this time."
            return explanation
        except Exception as e:
            logger.error(f"Error in FeedbackEngine generating ELI5 for '{term}': {e}", exc_info=True)
            return "Error generating explanation."

    async def generate_quiz(self, word: str, language: str, difficulty_level: Optional[str] = "medium", num_questions: Optional[int] = 3) -> Optional[MiniQuizResponse]:
        """Generates a mini-quiz related to the word."""
        logger.info(f"FeedbackEngine: Generating mini-quiz for '{word}' in {language}.")
        try:
            prompt = f"Create a mini quiz with {num_questions} questions about the word '{word}' in {language}. Difficulty: {difficulty_level}. For each question, provide the question text, a list of 3-4 options, the 0-based index of the correct answer, and a brief explanation for the correct answer. Format the output as a JSON object with a 'quiz_title' (string) and a 'questions' (list of objects, where each object has 'question_text', 'options', 'correct_answer_index', 'explanation')."
            
            quiz_data_dict = await self.gemini_engine.generate_mini_quiz_gemini(word, language, difficulty_level, num_questions, prompt_template=prompt)
            
            if not quiz_data_dict or not quiz_data_dict.get("questions"):
                logger.warning(f"GeminiEngine returned no or invalid quiz data for '{word}'. Dict: {quiz_data_dict}")
                return None
            
            questions = []
            for q_data in quiz_data_dict.get("questions", []):
                # Add validation here if Gemini might return malformed question data
                try:
                    questions.append(MiniQuizQuestion(**q_data))
                except Exception as q_val_error:
                    logger.error(f"Error validating question data from Gemini: {q_data}, error: {q_val_error}")
                    continue # Skip malformed question
            
            if not questions: # If all questions were malformed
                logger.warning(f"No valid questions could be parsed for quiz on '{word}'.")
                return None

            return MiniQuizResponse(
                quiz_title=quiz_data_dict.get("quiz_title", f"Mini Quiz for '{word}'"),
                questions=questions
            )

        except Exception as e:
            logger.error(f"Error in FeedbackEngine generating quiz for '{word}': {e}", exc_info=True)
            return None

# Note: The standalone 'generate_word_enrichment_details' function that was previously here
# has been removed as its functionality is now handled by the class method above,
# and the service layer has been updated to use an instance of FeedbackEngine. 
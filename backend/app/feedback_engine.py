import logging
from typing import Optional, List, Dict, Any

from app.models import (
    AiFeedback, MiniQuizResponse, MiniQuizQuestion # Removed unused models
)
from agents import VocabularyEnrichmentAgent, QuizGenerationAgent
from agents.schemas import Definition, CommonMistake
# from config import get_settings # This import is not needed here
from app.ai_engines.gemini_engine import GeminiEngine # Keep for journal analysis

logger = logging.getLogger(__name__)

class FeedbackEngine:
    def __init__(self, gemini_engine: GeminiEngine):
        self.gemini_engine = gemini_engine
        # Initialize vocabulary agents
        self.vocabulary_enrichment_agent = VocabularyEnrichmentAgent()
        self.quiz_generation_agent = QuizGenerationAgent()

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
            # Use the VocabularyEnrichmentAgent instead of GeminiEngine
            enrichment_result = await self.vocabulary_enrichment_agent.enrich_async(
                term=term,
                language=language,
                context=None,  # Could be enhanced to pass context if available
                user_level="intermediate"  # Could be made configurable
            )
            
            # Convert the structured result to the dictionary format expected by the service
            result_dict = {
                "language": enrichment_result.language,
                "ai_example_sentences": enrichment_result.ai_example_sentences,
                "ai_definitions": [{
                    "part_of_speech": defn.part_of_speech,
                    "definition": defn.definition
                } for defn in enrichment_result.ai_definitions],
                "ai_synonyms": enrichment_result.ai_synonyms,
                "ai_antonyms": enrichment_result.ai_antonyms,
                "ai_related_phrases": enrichment_result.ai_related_phrases,
                "ai_cultural_note": enrichment_result.ai_cultural_note,
                "ai_pronunciation_guide": enrichment_result.ai_pronunciation_guide,
                "ai_alternative_forms": enrichment_result.ai_alternative_forms,
                "ai_common_mistakes": [{
                    "mistake": mistake.mistake,
                    "correction": mistake.correction,
                    "explanation": mistake.explanation
                } for mistake in enrichment_result.ai_common_mistakes],
                "emotion_tone": enrichment_result.emotion_tone,
                "mnemonic": enrichment_result.mnemonic,
                "ai_conjugation_info": enrichment_result.ai_conjugation_info or {},
                "emoji": enrichment_result.emoji,
                "source_model": "gpt-4o-mini",  # Could be made configurable
            }
            
            logger.info(f"Successfully enriched '{term}' with {len(enrichment_result.ai_definitions)} definitions, "
                       f"{len(enrichment_result.ai_example_sentences)} examples")
            return result_dict
            
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
                "ai_pronunciation_guide": "",
                "ai_alternative_forms": [],
                "ai_common_mistakes": [],
                "source_model": "gpt-4o-mini",
            }

    async def generate_additional_examples(self, word: str, language: str, existing_examples: Optional[List[str]] = None, target_audience_level: Optional[str] = "intermediate") -> List[str]:
        """Generates additional example sentences for a word."""
        logger.info(f"FeedbackEngine: Generating additional examples for '{word}' in {language}.")
        try:
            # Use the QuizGenerationAgent for more examples
            examples_result = await self.quiz_generation_agent.generate_more_examples_async(
                word=word,
                language=language,
                existing_examples=existing_examples,
                target_audience_level=target_audience_level,
                num_examples=3
            )
            
            if not examples_result.new_example_sentences:
                logger.warning(f"QuizGenerationAgent returned no new examples for '{word}'.")
                return []
            
            logger.info(f"Successfully generated {len(examples_result.new_example_sentences)} examples for '{word}'")
            return examples_result.new_example_sentences
            
        except Exception as e:
            logger.error(f"Error in FeedbackEngine generating additional examples for '{word}': {e}", exc_info=True)
            return []

    async def generate_eli5_explanation(self, term: str, language:str) -> str:
        """Generates an ELI5 explanation for a term."""
        logger.info(f"FeedbackEngine: Generating ELI5 for '{term}' in {language}.")
        try:
            # Use the QuizGenerationAgent for ELI5 explanations
            eli5_result = await self.quiz_generation_agent.explain_eli5_async(
                term=term,
                language=language,
                context=None  # Could be enhanced to pass context if available
            )
            
            if not eli5_result.explanation:
                logger.warning(f"QuizGenerationAgent returned no ELI5 explanation for '{term}'.")
                return "Could not generate an explanation at this time."
            
            logger.info(f"Successfully generated ELI5 explanation for '{term}'")
            return eli5_result.explanation
            
        except Exception as e:
            logger.error(f"Error in FeedbackEngine generating ELI5 for '{term}': {e}", exc_info=True)
            return "Error generating explanation."

    async def generate_quiz(self, word: str, language: str, difficulty_level: Optional[str] = "medium", num_questions: Optional[int] = 3) -> Optional[MiniQuizResponse]:
        """Generates a mini-quiz related to the word."""
        logger.info(f"FeedbackEngine: Generating mini-quiz for '{word}' in {language}.")
        try:
            # Use the QuizGenerationAgent for quiz generation
            quiz_result = await self.quiz_generation_agent.generate_quiz_async(
                word=word,
                language=language,
                num_questions=num_questions,
                difficulty=difficulty_level
            )
            
            if not quiz_result.questions:
                logger.warning(f"QuizGenerationAgent returned no questions for '{word}'.")
                return None
            
            # Convert from QuizGenerationOutputSchema to MiniQuizResponse
            questions = []
            for q in quiz_result.questions:
                try:
                    questions.append(MiniQuizQuestion(
                        question_text=q.question_text,
                        options=q.options,
                        correct_answer_index=q.correct_answer_index,
                        explanation=q.explanation
                    ))
                except Exception as q_val_error:
                    logger.error(f"Error converting question data: {q}, error: {q_val_error}")
                    continue # Skip malformed question
            
            if not questions: # If all questions were malformed
                logger.warning(f"No valid questions could be converted for quiz on '{word}'.")
                return None

            logger.info(f"Successfully generated quiz for '{word}' with {len(questions)} questions")
            return MiniQuizResponse(
                quiz_title=quiz_result.quiz_title,
                questions=questions
            )

        except Exception as e:
            logger.error(f"Error in FeedbackEngine generating quiz for '{word}': {e}", exc_info=True)
            return None

# Note: The standalone 'generate_word_enrichment_details' function that was previously here
# has been removed as its functionality is now handled by the class method above,
# and the service layer has been updated to use an instance of FeedbackEngine. 
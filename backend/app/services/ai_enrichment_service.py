# backend/app/services/ai_enrichment_service.py
import uuid
import logging
import asyncio # Added for simulated AI call
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # This is fine if sqlalchemy is installed

from app.models import (
    UserVocabularyItemResponse, 
    WordAiCacheDB, 
    WordAiCacheCreate, 
    EnrichedWordDetailsResponse,
    MoreExamplesRequest, MoreExamplesResponse, ELI5Request, ELI5Response, MiniQuizRequest, MiniQuizResponse, MiniQuizQuestion
)

# Corrected import path for database functions
from database import (
    fetch_vocabulary_item_by_id_and_user as fetch_user_vocabulary_item_by_id, # Corrected name and aliased
    fetch_word_ai_cache_entry as get_word_ai_cache_entry_by_vocab_id_lang, # Corrected name and aliased
    save_word_ai_cache_entry as create_word_ai_cache_entry # Corrected name and aliased
)
from app.feedback_engine import FeedbackEngine

logger = logging.getLogger(__name__)

# This function now directly calls the feedback_engine
async def call_ai_for_word_enrichment(term: str, language: str, feedback_engine: FeedbackEngine) -> Dict[str, Any]: # Added feedback_engine dependency
    """
    Calls the feedback_engine to generate AI word enrichment details.
    Returns a dictionary structured to match WordAiCacheBase fields.
    """
    logger.info(f"Service: Calling feedback_engine for AI enrichment. Term='{term}', Language='{language}'")
    try:
        # Pass the FeedbackEngine instance
        ai_data = await feedback_engine.generate_word_enrichment_details(term=term, language=language)
        return ai_data
    except Exception as e:
        logger.error(f"Error calling feedback_engine.generate_word_enrichment_details for term '{term}': {e}")
        # Fallback to a default structure in case of error from feedback_engine
        return {
            "ai_example_sentences": [],
            "ai_synonyms": [],
            "ai_antonyms": [],
            "ai_related_phrases": [],
            "ai_cultural_note": "AI enrichment failed.",
            "ai_definitions": [], # Added missing field from WordAiCacheBase
            # Ensure all fields from WordAiCacheBase are covered here for fallback
        }

async def get_or_create_enriched_details_service(
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    language: str,
    db: AsyncSession, # Added db session
    feedback_engine: FeedbackEngine # Added FeedbackEngine dependency
) -> EnrichedWordDetailsResponse:
    """
    Service to get or create AI-enriched details for a vocabulary item.
    """
    # 1. Validate ownership and get the vocabulary item
    # Assuming fetch_user_vocabulary_item_by_id also checks user_id for ownership
    vocab_item = await fetch_user_vocabulary_item_by_id(db=db, item_id=item_id, user_id=user_id)
    if not vocab_item:
        logger.warning(f"Vocabulary item {item_id} not found for user {user_id} or does not exist.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary item not found or you do not have permission to access it."
        )
    
    if vocab_item.language != language:
        logger.warning(f"Requested language '{language}' does not match vocabulary item's language '{vocab_item.language}' for item {item_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The requested language '{language}' does not match the language of the stored vocabulary item ('{vocab_item.language}')."
        )
    
    term_to_enrich = vocab_item.word # Assuming the field is 'word' in UserVocabularyItem model
    if not term_to_enrich:
        logger.error(f"Vocabulary item {item_id} for user {user_id} is missing the 'word' field.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vocabulary item data is incomplete (missing word/term)."
        )

    # 2. Check cache
    cached_enrichment = await get_word_ai_cache_entry_by_vocab_id_lang(db=db, word_vocabulary_id=item_id, language=language)

    if cached_enrichment:
        logger.info(f"Cache hit for item_id: {item_id}, language: {language}")
        try:
            # Ensure all fields are correctly mapped from WordAiCacheDB to EnrichedWordDetailsResponse
            return EnrichedWordDetailsResponse(**cached_enrichment.model_dump())
        except Exception as e: 
            logger.error(f"Error validating/transforming cached data for {item_id}: {e}. Will try to regenerate.")

    logger.info(f"Cache miss for item_id: {item_id}, language: {language}. Generating new enrichment.")

    # 3. If not cached, generate, cache, and return
    try:
        # Pass the FeedbackEngine instance to call_ai_for_word_enrichment
        ai_generated_data_dict = await call_ai_for_word_enrichment(term=term_to_enrich, language=language, feedback_engine=feedback_engine)
        
        cache_create_model = WordAiCacheCreate(
            word_vocabulary_id=item_id,
            language=language,
            **ai_generated_data_dict # Unpack all fields from AI response matching WordAiCacheBase
        )
        
        # Ensure create_word_ai_cache_entry takes the model and returns the DB model
        saved_cache_db_model = await create_word_ai_cache_entry(db=db, cache_entry_data=cache_create_model)
        
        if not saved_cache_db_model:
             logger.error(f"Failed to save AI enrichment to cache for item_id: {item_id}")
             transient_id = uuid.uuid4()
             # Construct response from the data we attempted to save
             response_data_on_save_fail = {
                "id": transient_id,
                **cache_create_model.model_dump(exclude_none=True)
             }
             return EnrichedWordDetailsResponse(**response_data_on_save_fail)

        logger.info(f"Successfully generated and cached AI enrichment for item_id: {item_id}, language: {language}")
        return EnrichedWordDetailsResponse(**saved_cache_db_model.model_dump())

    except Exception as e:
        logger.error(f"Error during AI enrichment or caching for item_id {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate or cache AI enrichment: {str(e)}"
        )

async def generate_more_examples(
    db: AsyncSession, 
    request: MoreExamplesRequest,
    feedback_engine: FeedbackEngine
) -> MoreExamplesResponse:
    """Generates more example sentences for a given word using the AI feedback engine."""
    try:
        logger.info(f"Generating more examples for word: {request.word} in language: {request.language}")
        ai_generated_examples = await feedback_engine.generate_additional_examples(
            word=request.word,
            language=request.language,
            existing_examples=request.existing_examples,
            target_audience_level=request.target_audience_level
        )
        if not ai_generated_examples:
            raise HTTPException(status_code=500, detail="AI engine failed to generate more examples.")
        return MoreExamplesResponse(new_example_sentences=ai_generated_examples)
    except HTTPException as http_exc:
        logger.error(f"HTTPException in generate_more_examples: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error generating more examples for word '{request.word}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate more examples: {str(e)}")

async def explain_like_i_am_five(
    db: AsyncSession, 
    request: ELI5Request,
    feedback_engine: FeedbackEngine
) -> ELI5Response:
    """Generates an ELI5 explanation for a term using the AI feedback engine."""
    try:
        logger.info(f"Generating ELI5 for term: {request.term} in language: {request.language}")
        ai_explanation = await feedback_engine.generate_eli5_explanation(
            term=request.term,
            language=request.language
        )
        if not ai_explanation:
            raise HTTPException(status_code=500, detail="AI engine failed to generate ELI5 explanation.")
        return ELI5Response(explanation=ai_explanation)
    except HTTPException as http_exc:
        logger.error(f"HTTPException in explain_like_i_am_five: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error generating ELI5 for term '{request.term}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate ELI5 explanation: {str(e)}")

async def generate_mini_quiz(
    db: AsyncSession, 
    request: MiniQuizRequest,
    feedback_engine: FeedbackEngine
) -> MiniQuizResponse:
    """Generates a mini-quiz for a given word using the AI feedback engine."""
    try:
        logger.info(f"Generating mini quiz for word: {request.word} in language: {request.language}")
        quiz_data = await feedback_engine.generate_quiz(
            word=request.word,
            language=request.language,
            difficulty_level=request.difficulty_level,
            num_questions=request.num_questions
        )
        if not quiz_data or not quiz_data.questions:
            raise HTTPException(status_code=500, detail="AI engine failed to generate a mini quiz.")
        return quiz_data
    except HTTPException as http_exc:
        logger.error(f"HTTPException in generate_mini_quiz: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error generating mini quiz for word '{request.word}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate mini quiz: {str(e)}") 
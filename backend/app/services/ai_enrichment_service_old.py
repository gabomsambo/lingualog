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
    # Note: fetch_user_vocabulary_item_by_id doesn't use db parameter - it creates its own Supabase client
    vocab_item = await fetch_user_vocabulary_item_by_id(item_id=item_id, user_id=user_id)
    if not vocab_item:
        logger.warning(f"Vocabulary item {item_id} not found for user {user_id} or does not exist.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary item not found or you do not have permission to access it."
        )
    
    # Comprehensive bidirectional language mapping for multilingual support
    # Supports both full names -> codes and codes -> full names
    LANGUAGE_MAPPINGS = {
        # Full names to codes
        'Spanish': 'es', 'English': 'en', 'French': 'fr', 'German': 'de',
        'Italian': 'it', 'Portuguese': 'pt', 'Japanese': 'ja', 'Chinese': 'zh',
        'Korean': 'ko', 'Russian': 'ru', 'Arabic': 'ar', 'Hindi': 'hi',
        'Dutch': 'nl', 'Swedish': 'sv', 'Norwegian': 'no', 'Danish': 'da',
        'Finnish': 'fi', 'Polish': 'pl', 'Czech': 'cs', 'Hungarian': 'hu',
        'Turkish': 'tr', 'Greek': 'el', 'Hebrew': 'he', 'Thai': 'th',
        'Vietnamese': 'vi', 'Indonesian': 'id', 'Malay': 'ms', 'Filipino': 'tl',
        # Codes to full names
        'es': 'Spanish', 'en': 'English', 'fr': 'French', 'de': 'German',
        'it': 'Italian', 'pt': 'Portuguese', 'ja': 'Japanese', 'zh': 'Chinese',
        'ko': 'Korean', 'ru': 'Russian', 'ar': 'Arabic', 'hi': 'Hindi',
        'nl': 'Dutch', 'sv': 'Swedish', 'no': 'Norwegian', 'da': 'Danish',
        'fi': 'Finnish', 'pl': 'Polish', 'cs': 'Czech', 'hu': 'Hungarian',
        'tr': 'Turkish', 'el': 'Greek', 'he': 'Hebrew', 'th': 'Thai',
        'vi': 'Vietnamese', 'id': 'Indonesian', 'ms': 'Malay', 'tl': 'Filipino',
    }
    
    def normalize_language(lang: str) -> tuple[str, str]:
        """
        Normalize language to both code and full name for flexible matching.
        Returns (language_code, full_name) tuple.
        """
        lang_lower = lang.lower()
        lang_title = lang.title()
        
        # If it's already a known code
        if lang_lower in LANGUAGE_MAPPINGS:
            code = lang_lower
            full_name = LANGUAGE_MAPPINGS[lang_lower]
            return code, full_name
            
        # If it's a full name
        if lang_title in LANGUAGE_MAPPINGS:
            full_name = lang_title
            code = LANGUAGE_MAPPINGS[lang_title]
            return code, full_name
            
        # Fallback: return as-is
        return lang_lower, lang_title
    
    # Normalize both vocabulary item language and requested language
    vocab_language = vocab_item['language']
    vocab_lang_code, vocab_lang_full = normalize_language(vocab_language)
    requested_lang_code, requested_lang_full = normalize_language(language)
    
    # Check if languages match (either by code or full name)
    if vocab_lang_code != requested_lang_code and vocab_lang_full != requested_lang_full:
        logger.warning(f"Requested language '{language}' does not match vocabulary item's language '{vocab_language}' for item {item_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The requested language '{language}' does not match the language of the stored vocabulary item ('{vocab_language}')."
        )
    
    term_to_enrich = vocab_item['term']  # Correct field name from database
    if not term_to_enrich:
        logger.error(f"Vocabulary item {item_id} for user {user_id} is missing the 'term' field.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vocabulary item data is incomplete (missing word/term)."
        )

    # 2. Check cache with flexible language matching
    # Try to find cached data with multiple language formats for backward compatibility
    cached_enrichment = None
    
    # Try exact match first (most common case)
    cached_enrichment = await get_word_ai_cache_entry_by_vocab_id_lang(word_vocabulary_id=item_id, language=vocab_language)
    
    # If not found and we have different formats, try the alternate format
    if not cached_enrichment and vocab_lang_code != vocab_language.lower():
        cached_enrichment = await get_word_ai_cache_entry_by_vocab_id_lang(word_vocabulary_id=item_id, language=vocab_lang_code)
    
    if not cached_enrichment and vocab_lang_full != vocab_language:
        cached_enrichment = await get_word_ai_cache_entry_by_vocab_id_lang(word_vocabulary_id=item_id, language=vocab_lang_full)

    if cached_enrichment:
        logger.info(f"Cache hit for item_id: {item_id}, language: {language}")
        try:
            # Handle both dict and Pydantic model responses from database
            if hasattr(cached_enrichment, 'model_dump'):
                cache_data = cached_enrichment.model_dump()
            else:
                cache_data = cached_enrichment  # Already a dict
            
            return EnrichedWordDetailsResponse(**cache_data)
        except Exception as e: 
            logger.error(f"Error validating/transforming cached data for {item_id}: {e}. Will try to regenerate.")

    logger.info(f"Cache miss for item_id: {item_id}, language: {vocab_language}. Generating new enrichment.")

    # 3. If not cached, generate, cache, and return
    try:
        # Use the language code for AI generation (more standardized)
        ai_generated_data_dict = await call_ai_for_word_enrichment(term=term_to_enrich, language=vocab_lang_code, feedback_engine=feedback_engine)
        
        # Remove language from ai_generated_data_dict if it exists to avoid duplication
        ai_data_copy = dict(ai_generated_data_dict)
        ai_data_copy.pop('language', None)  # Remove language if present
        
        # Store with the original language format from user_vocabulary for consistency
        cache_create_model = WordAiCacheCreate(
            word_vocabulary_id=item_id,
            language=vocab_language,  # Use original format for backward compatibility
            **ai_data_copy # Unpack all fields from AI response except language
        )
        
        # Save to cache (function expects dict, not Pydantic model)
        cache_data_dict = cache_create_model.model_dump()
        saved_cache_db_model = await create_word_ai_cache_entry(cache_data=cache_data_dict)
        
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
        
        # Handle both dict and Pydantic model responses from database
        if hasattr(saved_cache_db_model, 'model_dump'):
            cache_data = saved_cache_db_model.model_dump()
        else:
            cache_data = saved_cache_db_model  # Already a dict
            
        return EnrichedWordDetailsResponse(**cache_data)

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
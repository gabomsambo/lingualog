# backend/app/routers/vocabulary_ai.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional

# Corrected import paths
from app.models import EnrichedWordDetailsResponse, UserVocabularyItemResponse, MoreExamplesRequest, MoreExamplesResponse, ELI5Request, ELI5Response, MiniQuizRequest, MiniQuizResponse, User
from app.services.ai_enrichment_service import get_or_create_enriched_details_service, generate_more_examples, explain_like_i_am_five, generate_mini_quiz
from app.dependencies import get_db_session, get_current_active_user, get_feedback_engine

# Need to import FeedbackEngine for type hinting if it's used directly as a type in router function signatures
# Reading the file content provided, FeedbackEngine is used as a type for a Depends parameter.
from app.feedback_engine import FeedbackEngine

# Need to import AsyncSession for type hinting db parameters
from sqlalchemy.ext.asyncio import AsyncSession

# It seems logger is used but not imported. Adding it.
import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai/vocabulary",
    tags=["Vocabulary AI Enrichment"],
)

# Placeholder for a dependency to get authenticated user_id
# This should align with how you get user_id in server.py (e.g., from request.headers)
async def get_user_id_from_request(request: Request) -> uuid.UUID:
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided or authentication failed"
        )
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid User ID format. Must be a valid UUID."
        )

@router.get(
    "/{item_id}/enrich",
    response_model=EnrichedWordDetailsResponse,
    summary="Get AI-enriched details for a vocabulary item",
    description="Fetches cached AI-generated details (examples, synonyms, cultural notes, etc.) for a specific vocabulary item. If not cached or stale, it will generate them.",
)
async def get_enriched_vocabulary_item_details(
    item_id: uuid.UUID,
    language: str, # Query parameter to specify language, e.g., "en", "ja"
    request: Request, # To get user_id or other request context
    user_id: uuid.UUID = Depends(get_user_id_from_request), # Use Depends for cleaner injection and type safety
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
    feedback_engine: FeedbackEngine = Depends(get_feedback_engine)
):
    """
    Retrieves AI-enriched information for a given vocabulary item ID and language.

    - **item_id**: The unique identifier of the vocabulary item in the user's list.
    - **language**: The language of the vocabulary item for which to get enrichment.
    """
    # user_id is now directly injected by Depends as uuid.UUID
    try:
        enriched_details = await get_or_create_enriched_details_service(
            item_id=item_id, 
            user_id=current_user.id, 
            language=language,
            db=db,
            feedback_engine=feedback_engine
        )
        return enriched_details
    except HTTPException as he:
        # Re-raise HTTPExceptions directly if they are intentionally raised by the service
        raise he
    except Exception as e:
        # Log the exception server-side
        logger.error(f"Error in /ai/vocabulary/{item_id}/enrich: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# TODO: Add other endpoints for on-demand AI generation (e.g., more examples, ELI5, mini-quiz)
# For example:
# @router.post("/{item_id}/generate-examples", response_model=List[str])
# async def generate_more_examples_for_item(...):
#     # Logic to call AI for more examples
#     pass 

# --- On-Demand AI Generation Endpoints ---

@router.post("/on-demand/more-examples", response_model=MoreExamplesResponse)
async def get_more_examples(
    request: MoreExamplesRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user), # Assuming on-demand actions also need user context
    feedback_engine: FeedbackEngine = Depends(get_feedback_engine) 
):
    """Generates more example sentences for a given word."""
    logger.info(f"User {current_user.id} requesting more examples for word: {request.word}, lang: {request.language}")
    try:
        response = await generate_more_examples(
            db=db, # Though not strictly used by current service impl, good to pass for consistency
            request=request,
            feedback_engine=feedback_engine
        )
        return response
    except HTTPException as http_exc:
        logger.error(f"HTTPException in /on-demand/more-examples: {http_exc.detail}", exc_info=True)
        raise http_exc # Re-raise the HTTPException from the service
    except Exception as e:
        logger.error(f"Error in /on-demand/more-examples for word '{request.word}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate more examples: {str(e)}")

@router.post("/on-demand/eli5", response_model=ELI5Response)
async def get_eli5_explanation(
    request: ELI5Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
    feedback_engine: FeedbackEngine = Depends(get_feedback_engine)
):
    """Generates an "Explain Like I'm 5" explanation for a term."""
    logger.info(f"User {current_user.id} requesting ELI5 for term: {request.term}, lang: {request.language}")
    try:
        response = await explain_like_i_am_five(
            db=db, # Consistent service signature
            request=request,
            feedback_engine=feedback_engine
        )
        return response
    except HTTPException as http_exc:
        logger.error(f"HTTPException in /on-demand/eli5: {http_exc.detail}", exc_info=True)
        raise http_exc
    except Exception as e:
        logger.error(f"Error in /on-demand/eli5 for term '{request.term}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate ELI5 explanation: {str(e)}")

@router.post("/on-demand/mini-quiz", response_model=MiniQuizResponse)
async def get_mini_quiz(
    request: MiniQuizRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
    feedback_engine: FeedbackEngine = Depends(get_feedback_engine)
):
    """Generates a mini-quiz for a given word/concept."""
    logger.info(f"User {current_user.id} requesting mini-quiz for word: {request.word}, lang: {request.language}")
    try:
        response = await generate_mini_quiz(
            db=db, # Consistent service signature
            request=request,
            feedback_engine=feedback_engine
        )
        return response
    except HTTPException as http_exc:
        logger.error(f"HTTPException in /on-demand/mini-quiz: {http_exc.detail}", exc_info=True)
        raise http_exc
    except Exception as e:
        logger.error(f"Error in /on-demand/mini-quiz for word '{request.word}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate mini-quiz: {str(e)}")

# Ensure the router is included in the main FastAPI app 
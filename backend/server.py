"""
Main FastAPI application for the LinguaLog backend.

This module defines the FastAPI application and routes for handling journal entries
and generating AI feedback for language learning.
"""
import logging
import os
import sys
import uuid
from typing import List, Optional

# Add current directory to path to make imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from models import (
    JournalEntryRequest,
    FeedbackResponse,
    LoginRequest,
    UserVocabularyItemCreate,
    UserVocabularyItemResponse,
    Rubric,
    Suggestion,
    Word,
)
from app.models import JournalEntry, User, UserUpdate, UserSettings, UserSettingsUpdate # Corrected import for JournalEntry

# Import new language policy and prompt builder modules
from lang_policy import resolve_effective, EffectiveSettings
from prompt_builder import build_messages, build_user_message, extract_snapshot_data
from database import (
    save_entry,
    fetch_entries,
    sign_in_with_magic_link,
    fetch_single_entry,
    delete_entry,
    update_entry_analysis,
    save_vocabulary_item,
    fetch_user_vocabulary,
    delete_vocabulary_item,
    fetch_vocabulary_item_by_term,
    init_db_schema
)

# Gemini tutor adapter
from ai.schemas import JournalFeedback
from ai.gemini import (
    generate_structured,
    mock_generate_structured,
    GeminiError,
    GEMINI_MODEL_FEEDBACK,
    AI_PROVIDER,
)

# Import the new router
from app.routers import vocabulary_ai # Adjusted import path
from app.services.stats_service import get_user_stats_service
from app.schemas.stats_schemas import UserStatsResponse

# Configure logger
# Ensure basicConfig is called to set up the root logger handler and level
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) # Output to stdout, set level to DEBUG

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set our specific logger to DEBUG as well
logger.propagate = True # Ensure messages go to the root logger

# Test log to see if basicConfig is working on startup
logger.debug("Root logger configured, LinguaLog API logger set to DEBUG.")

def _parse_cors_origins() -> List[str]:
    origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


async def fetch_user_profile_settings(user_id: Optional[str]) -> Optional[dict]:
    """
    Fetch user profile settings for language policy resolution.
    
    Args:
        user_id: User ID to fetch settings for
        
    Returns:
        Dictionary of user settings or None if not found/authenticated
    """
    if not user_id:
        logger.info("No user_id provided, using default settings")
        return None
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Get user settings from user_settings table
        response = supabase.table('user_settings').select('*').eq('user_id', user_id).execute()
        
        if response.data:
            settings_data = response.data[0]
            logger.info(f"Fetched user settings for user {user_id}")
            return settings_data
        else:
            logger.info(f"No settings found for user {user_id}, will use defaults")
            return None
            
    except Exception as e:
        logger.warning(f"Failed to fetch user settings for {user_id}: {str(e)}")
        return None


def _build_feedback_response(result: JournalFeedback) -> FeedbackResponse:
    """Convert the Gemini structured output to the API response model."""
    return FeedbackResponse(
        corrected=result.corrected,
        rewritten=result.rewrite,
        score=result.score,
        tone=result.tone,
        translation="",
        explanation=result.explanation,
        rubric=Rubric(**result.rubric.model_dump()),
        grammar_suggestions=[
            Suggestion(**suggestion.model_dump())
            for suggestion in result.grammar_suggestions
        ],
        new_words=[
            Word(**word.model_dump())
            for word in result.new_words
        ],
        is_mock=result.is_mock,
    )


async def _analyze_with_provider(text: str, effective: EffectiveSettings) -> JournalFeedback:
    """Run the journal tutor (Gemini or mock) using the resolved policy prompt."""
    system_prompt, _user_payload = build_messages(text, effective)
    user_message = build_user_message(text, effective)

    if AI_PROVIDER == "mock":
        return await mock_generate_structured(
            system_prompt, user_message, JournalFeedback
        )
    return await generate_structured(
        system_prompt, user_message, JournalFeedback, timeout=30.0
    )


# --- Background Tasks ---

async def enrich_vocabulary_in_background(item_id: str, user_id: uuid.UUID, language: str):
    """
    Background task to automatically enrich vocabulary when words are added.
    This runs asynchronously after the user gets their success response.
    """
    logger.info(f"🤖 BACKGROUND TASK STARTED: Enriching vocabulary item {item_id} ({language}) for user {user_id}")
    
    try:
        # Import here to avoid circular imports
        import sys
        import os
        
        # Add the app directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.join(current_dir, 'app')
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        
        logger.info(f"🔧 Importing enrichment service...")
        from app.services.ai_enrichment_service import get_or_create_enriched_details_service
        from app.dependencies import get_db_session, get_feedback_engine
        
        logger.info(f"🔧 Getting feedback engine...")
        
        feedback_engine = get_feedback_engine()
        
        logger.info(f"🚀 Calling enrichment service for item {item_id}...")
        
        # Create a dummy database session (not used by database functions but required by service signature)
        mock_db = None
        
        # Trigger enrichment (this will create word_ai_cache entry)
        enriched_data = await get_or_create_enriched_details_service(
            item_id=uuid.UUID(item_id),
            user_id=user_id,
            language=language,
            db=mock_db,  # Not used by the underlying database functions
            feedback_engine=feedback_engine
        )
        
        logger.info(f"✅ Background enrichment completed for vocabulary item {item_id}")
        logger.info(f"📊 Generated {len(enriched_data.ai_example_sentences or [])} example sentences, "
                   f"{len(enriched_data.ai_synonyms or [])} synonyms, "
                   f"{len(enriched_data.ai_antonyms or [])} antonyms")
        
    except ImportError as e:
        logger.error(f"❌ Import error in background enrichment for {item_id}: {str(e)}")
        logger.error(f"📝 Check if all required modules are available")
    except Exception as e:
        logger.error(f"❌ Background enrichment failed for vocabulary item {item_id}: {str(e)}")
        logger.error(f"📝 Full error details:", exc_info=True)
        logger.error(f"📝 This is not critical - user can still click 'Learn It' to trigger enrichment manually")

app = FastAPI(
    title="LinguaLog API",
    description="API for language learning journal with AI feedback",
    version="0.1.0"
)

# TODO: Tighten CORS origins once Vercel/Railway deployment domains are known
# Currently using permissive settings for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the new AI vocabulary router
app.include_router(vocabulary_ai.router)


@app.post("/login", status_code=status.HTTP_200_OK)
async def login(login_request: LoginRequest):
    """
    Send a magic link to the user's email for passwordless authentication.
    
    Args:
        login_request: User's email
        
    Returns:
        Success message if the magic link was sent successfully
        
    Raises:
        HTTPException: If there's an error during authentication
    """
    try:
        result = sign_in_with_magic_link(login_request.email)
        return result
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )


@app.post("/log-entry", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry(entry: JournalEntryRequest, request: Request):
    """
    Process a journal entry and generate AI feedback using language policy resolution.

    Args:
        entry: The journal entry request with text and optional language overrides
        request: The request object containing user info (if available)

    Returns:
        FeedbackResponse with grammar correction, rewriting, and other feedback dimensions

    Raises:
        HTTPException: If there's an error processing the request
    """
    # Get user_id from request headers if present
    user_id = request.headers.get("X-User-ID")

    # Fetch user profile settings
    profile_settings = await fetch_user_profile_settings(user_id)

    # Build request overrides from entry fields
    request_overrides = {}
    if entry.target_language:
        request_overrides['target_language'] = entry.target_language
    if entry.language:
        request_overrides['language'] = entry.language
    if entry.ui_language:
        request_overrides['ui_language'] = entry.ui_language
    if entry.explanation_mode:
        request_overrides['explanation_mode'] = entry.explanation_mode
    if entry.strictness:
        request_overrides['strictness'] = entry.strictness
    if entry.formality:
        request_overrides['formality'] = entry.formality
    if entry.immersion_level is not None:
        request_overrides['immersion_level'] = entry.immersion_level

    # Resolve effective language settings
    effective_settings = resolve_effective(profile_settings, request_overrides)
    snapshot_data = extract_snapshot_data(effective_settings)

    try:
        result = await _analyze_with_provider(entry.text, effective_settings)
        feedback_response = _build_feedback_response(result)
    except GeminiError as e:
        logger.error(f"AI feedback failed ({e.code}): {e.message}")
        # Keep the entry so the learner can retry later.
        failed_entry = {
            "user_id": user_id,
            "original_text": entry.text,
            "title": entry.title,
            "language": entry.language or effective_settings.l2,
            "analysis_status": "failed",
            "analysis_model": GEMINI_MODEL_FEEDBACK,
            "analysis_error_code": e.code,
            **snapshot_data,
        }
        saved_entry = save_entry(failed_entry)
        entry_id = saved_entry.get("id", "unknown")
        logger.info(f"Entry saved without feedback: {entry_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": e.code,
                "entry_id": entry_id,
                "message": e.message,
            },
        ) from e

    # Save entry and feedback to Supabase with language snapshots
    entry_data = {
        "user_id": user_id,
        "original_text": entry.text,
        "title": entry.title,
        "language": entry.language or effective_settings.l2,
        "corrected": feedback_response.corrected,
        "rewrite": feedback_response.rewritten,
        "score": feedback_response.score,
        "tone": feedback_response.tone,
        "translation": feedback_response.translation,
        "explanation": feedback_response.explanation,
        "rubric": feedback_response.rubric.model_dump() if feedback_response.rubric else None,
        "grammar_suggestions": [sugg.model_dump() for sugg in feedback_response.grammar_suggestions] if feedback_response.grammar_suggestions else [],
        "new_words": [word.model_dump() for word in feedback_response.new_words] if feedback_response.new_words else [],
        "analysis_status": "ok",
        "analysis_model": GEMINI_MODEL_FEEDBACK if not feedback_response.is_mock else "mock",
        "analysis_error_code": None,
        **snapshot_data,
    }

    saved_entry = save_entry(entry_data)
    logger.info(f"Entry saved with ID: {saved_entry.get('id', 'unknown')} and language snapshots")

    return feedback_response


@app.get("/entries", status_code=status.HTTP_200_OK)
async def get_entries(request: Request, language: Optional[str] = None):
    """
    Retrieve journal entries for the authenticated user, optionally filtered by language.

    Args:
        request: The request object containing user info (if available)
        language: Optional language filter (e.g., 'es', 'fr', 'ja') to show only entries in that language

    Returns:
        List of journal entries with their feedback

    Raises:
        HTTPException: If there's an error retrieving entries
    """
    try:
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            # If no X-User-ID, it could be an unauthenticated request or error.
            # For now, let's return an empty list or an error.
            # Depending on desired behavior, you might allow fetching all if admin, etc.
            logger.warning("Attempted to fetch entries without X-User-ID header.")
            # Option 1: Return empty list
            return []
            # Option 2: Raise an error
            # raise HTTPException(
            #     status_code=status.HTTP_401_UNAUTHORIZED,
            #     detail="User ID not provided"
            # )

        entries = fetch_entries(user_id=user_id, language=language)
        return entries
    except Exception as e:
        logger.error(f"Error fetching entries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching entries: {str(e)}"
        )


@app.get("/entries/{entry_id}", response_model=JournalEntry)
async def get_single_entry(entry_id: str, request: Request):
    print("!!!!!!!!!! (PRINT) ENTERING get_single_entry FUNCTION !!!!!!!!!!", file=sys.stderr) # Prominent entry print
    logger.info("!!!!!!!!!! (LOGGER.INFO) ENTERING get_single_entry FUNCTION !!!!!!!!!!") # Prominent entry log
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        print("!!!!!!!!!! (PRINT) User ID not provided in get_single_entry !!!!!!!!!!", file=sys.stderr)
        logger.error("User ID not provided in get_single_entry")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    
    entry_data_dict = None
    try:
        print(f"!!!!!!!!!! (PRINT) Fetching entry: {entry_id} for user: {user_id} !!!!!!!!!!", file=sys.stderr)
        logger.info(f"Fetching entry data for entry_id: {entry_id} by user_id: {user_id}")
        entry_data_dict = fetch_single_entry(entry_id, user_id)
        
        if not entry_data_dict:
            print(f"!!!!!!!!!! (PRINT) Entry not found in DB: id {entry_id} for user {user_id} !!!!!!!!!!", file=sys.stderr)
            logger.warning(f"Entry not found in DB: id {entry_id} for user {user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
        
        print("!!!!!!!!!! (PRINT) REACHED DETAILED LOGGING BLOCK !!!!!!!!!!", file=sys.stderr)
        logger.info("!!!!!!!!!! (LOGGER.INFO) REACHED DETAILED LOGGING BLOCK !!!!!!!!!!")
        
        logger.debug(f"Raw entry_data_dict from DB: {entry_data_dict}") # Changed to debug for potentially large output

        if 'ai_feedback' in entry_data_dict and entry_data_dict['ai_feedback'] is not None:
            ai_feedback_data = entry_data_dict['ai_feedback']
            logger.info(f"ai_feedback type: {type(ai_feedback_data)}")
            logger.info(f"ai_feedback raw content: {ai_feedback_data}")
            if isinstance(ai_feedback_data, dict):
                logger.info(f"ai_feedback keys: {list(ai_feedback_data.keys())}")
                for key, value in ai_feedback_data.items():
                    logger.info(f"ai_feedback field - {key}: {value} (type: {type(value)})")
            elif isinstance(ai_feedback_data, str):
                logger.warning(f"ai_feedback is a STRING: '{ai_feedback_data}'. Expected a dict/JSON object.")
            else:
                logger.warning(f"ai_feedback is of unexpected type: {type(ai_feedback_data)}. Content: {ai_feedback_data}")
        else:
            logger.info(f"No 'ai_feedback' field in entry_data_dict or it is None. Keys: {list(entry_data_dict.keys()) if isinstance(entry_data_dict, dict) else 'entry_data_dict is not a dict'}")
        
        print("!!!!!!!!!! (PRINT) Attempting Pydantic model creation... !!!!!!!!!!", file=sys.stderr)
        logger.info("Attempting Pydantic model creation for JournalEntry...")
        journal_entry = JournalEntry(**entry_data_dict)
        print("!!!!!!!!!! (PRINT) Pydantic model JournalEntry CREATED. !!!!!!!!!!", file=sys.stderr)
        logger.info("Pydantic model JournalEntry created successfully.")
        return journal_entry
        
    except ValidationError as e:
        print(f"!!!!!!!!!! (PRINT) Pydantic VALIDATION ERROR for entry {entry_id} !!!!!!!!!!", file=sys.stderr)
        logger.error(f"Pydantic validation error for entry {entry_id}: {e.errors()}") # Log detailed errors
        logger.error(f"Raw entry data causing validation error: {entry_data_dict}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Data validation error processing entry. Details: {e.errors()}" # Send errors to client
        )
    except HTTPException:
        print("!!!!!!!!!! (PRINT) Re-raising HTTPException !!!!!!!!!!", file=sys.stderr)
        raise
    except Exception as e:
        print(f"!!!!!!!!!! (PRINT) UNEXPECTED ERROR in get_single_entry for {entry_id}: {type(e).__name__} - {e} !!!!!!!!!!", file=sys.stderr)
        logger.error(f"Unexpected error in get_single_entry for entry {entry_id}: {type(e).__name__} - {e}")
        raw_data_info = entry_data_dict if entry_data_dict is not None else "Raw data not fetched or available."
        logger.error(f"Raw entry data at point of unexpected error: {raw_data_info}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error while fetching entry: {type(e).__name__} - {e}"
        )


@app.post("/entries/{entry_id}/analyze", response_model=FeedbackResponse)
async def analyze_existing_entry(entry_id: str, request: Request):
    """
    Retry AI analysis for an existing journal entry.

    The entry must belong to the authenticated user. The current language
    settings are used, with the entry's target language preserved from the
    snapshot.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided",
        )

    entry = fetch_single_entry(entry_id, user_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )

    profile_settings = await fetch_user_profile_settings(user_id)
    overrides = {
        "target_language": entry.get("target_language") or entry.get("language"),
    }
    effective_settings = resolve_effective(profile_settings, overrides)

    try:
        result = await _analyze_with_provider(entry["content"], effective_settings)
    except GeminiError as e:
        logger.error(f"Retry analysis failed for {entry_id} ({e.code}): {e.message}")
        update_entry_analysis(
            entry_id,
            user_id,
            {"analysis_status": "failed", "analysis_error_code": e.code},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": e.code,
                "entry_id": entry_id,
                "message": e.message,
            },
        ) from e

    feedback_response = _build_feedback_response(result)
    update_data = {
        "corrected": feedback_response.corrected,
        "rewrite": feedback_response.rewritten,
        "score": feedback_response.score,
        "tone": feedback_response.tone,
        "translation": feedback_response.translation,
        "explanation": feedback_response.explanation,
        "rubric": feedback_response.rubric.model_dump() if feedback_response.rubric else None,
        "grammar_suggestions": [sugg.model_dump() for sugg in feedback_response.grammar_suggestions] if feedback_response.grammar_suggestions else [],
        "new_words": [word.model_dump() for word in feedback_response.new_words] if feedback_response.new_words else [],
        "analysis_status": "ok",
        "analysis_model": GEMINI_MODEL_FEEDBACK if not feedback_response.is_mock else "mock",
        "analysis_error_code": None,
    }
    update_entry_analysis(entry_id, user_id, update_data)
    return feedback_response


@app.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry_route(entry_id: str, request: Request):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    
    try:
        success = delete_entry(entry_id=entry_id, user_id=user_id)
        if not success:
            # This case might indicate the entry didn't exist or didn't belong to the user
            # delete_entry should ideally raise a specific exception or return a more detailed status
            logger.warning(f"Attempt to delete entry {entry_id} for user {user_id} was not successful (entry not found or no permission).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found or user does not have permission to delete.")
        logger.info(f"Entry {entry_id} deleted successfully for user {user_id}.")
        return # FastAPI handles the 204 No Content response
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error deleting entry {entry_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting entry: {str(e)}"
        )


# --- Vocabulary Endpoints ---

@app.post("/vocabulary", response_model=UserVocabularyItemResponse, status_code=status.HTTP_201_CREATED)
async def add_vocabulary_item_route(item: UserVocabularyItemCreate, request: Request, background_tasks: BackgroundTasks):
    """
    Add a new word to the user's vocabulary.
    The user_id is extracted from the request headers.
    Automatically triggers AI enrichment in the background.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided"
        )
    
    try:
        # Convert Pydantic model to dict for database function
        item_data = item.model_dump()
        saved_item = save_vocabulary_item(item_data=item_data, user_id=user_id)
        
        # 🚀 AUTOMATIC ENRICHMENT: Trigger background AI enrichment for the saved word
        logger.info(f"📋 VOCABULARY SAVED: {item.term} ({item.language}) with ID {saved_item['id']}")
        logger.info(f"🚀 TRIGGERING BACKGROUND ENRICHMENT for vocabulary item {saved_item['id']}")
        
        background_tasks.add_task(
            enrich_vocabulary_in_background,
            saved_item["id"],  # vocabulary item ID
            uuid.UUID(user_id),  # user ID
            item.language  # language
        )
        
        logger.info(f"✅ Background enrichment task added for vocabulary item {saved_item['id']} ({item.term} in {item.language})")
        logger.info(f"📝 User should see immediate success, enrichment will happen in background")
        
        return saved_item # User gets immediate response while enrichment happens in background
    except Exception as e:
        logger.error(f"Error adding vocabulary item for user {user_id}: {str(e)}")
        # Check for specific error types if needed, e.g., duplicate handling if not an upsert
        if "unique constraint" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vocabulary item '{item.term}' in {item.language} already exists for this user."
            ) # This might be redundant if upsert handles it, but good for clarity.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save vocabulary item: {str(e)}"
        )

@app.get("/vocabulary", status_code=status.HTTP_200_OK)
async def get_user_vocabulary_route(request: Request, language: Optional[str] = None):
    """
    Fetch all vocabulary items for the authenticated user, optionally filtered by language.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided"
        )
    
    try:
        vocab_items = fetch_user_vocabulary(user_id=user_id, language=language)
        return vocab_items # FastAPI will serialize List[Dict] to List[UserVocabularyItemResponse]
    except Exception as e:
        logger.error(f"Error fetching vocabulary for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch vocabulary: {str(e)}"
        )

@app.delete("/vocabulary/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocabulary_item_route(item_id: str, request: Request):
    """
    Delete a specific vocabulary item for the authenticated user.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided"
        )
    
    try:
        success = delete_vocabulary_item(item_id=item_id, user_id=user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vocabulary item with id {item_id} not found or not owned by user."
            )
        return # Returns 204 No Content by default
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error deleting vocabulary item {item_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete vocabulary item: {str(e)}"
        )


# TODO: Add user authentication middleware/dependencies

@app.post("/log-entry-atomic", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry_atomic(entry: JournalEntryRequest, request: Request):
    """
    Process a journal entry using Atomic Agents (experimental endpoint).
    
    This endpoint uses the new Atomic Agents framework for AI analysis
    and runs in parallel with the existing system for comparison.
    """
    try:
        # Import here to avoid startup issues if atomic agents aren't available
        from services.agent_service import analyze_entry_atomic_compat
        
        user_id = request.headers.get("X-User-ID")
        
        logger.info(f"Processing entry with Atomic Agents: {len(entry.text)} chars, language: {entry.language}")
        
        # Generate feedback using Atomic Agents
        analysis = await analyze_entry_atomic_compat(entry.text, entry.language)
        
        # Convert to FeedbackResponse format
        feedback_response = FeedbackResponse(**{
            "corrected": analysis.get("corrected", entry.text),
            "rewritten": analysis.get("rewrite", entry.text),
            "score": analysis.get("score", 0),
            "tone": analysis.get("tone", "Neutral"),
            "translation": analysis.get("translation", "Translation not available."),
            "explanation": analysis.get("explanation", "No detailed explanation available."),
            "rubric": analysis.get("rubric", {"grammar": 0, "vocabulary": 0, "complexity": 0}),
            "grammar_suggestions": analysis.get("grammar_suggestions", []),
            "new_words": analysis.get("new_words", [])
        })
        
        # Save entry and feedback to Supabase (same as original endpoint)
        try:
            entry_data = {
                "user_id": user_id,
                "original_text": entry.text,
                "title": entry.title,
                "language": entry.language,
                "corrected": feedback_response.corrected,
                "rewrite": feedback_response.rewritten,
                "score": feedback_response.score,
                "tone": feedback_response.tone,
                "translation": feedback_response.translation,
                "explanation": feedback_response.explanation,
                "rubric": feedback_response.rubric.model_dump() if feedback_response.rubric else None,
                "grammar_suggestions": [sugg.model_dump() for sugg in feedback_response.grammar_suggestions] if feedback_response.grammar_suggestions else [],
                "new_words": [word.model_dump() for word in feedback_response.new_words] if feedback_response.new_words else []
            }
            
            saved_entry = save_entry(entry_data)
            logger.info(f"Atomic Agents entry saved with ID: {saved_entry.get('id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to save atomic agents entry to database: {str(e)}")
        
        return feedback_response
        
    except Exception as e:
        logger.error(f"Error in atomic agents endpoint: {str(e)}")
        # Fallback to original endpoint logic
        logger.info("Falling back to original analysis method")
        return await create_log_entry(entry, request)


# User Profile and Stats Endpoints

@app.get("/user/profile", response_model=User, status_code=status.HTTP_200_OK)
async def get_user_profile(request: Request):
    """
    Get the current user's profile information.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        # Get user from Supabase auth users table
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Get user profile from auth.users
        response = supabase.auth.admin.get_user_by_id(user_id)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = response.user
        
        # Get additional profile data from users table if it exists
        profile_response = supabase.table('users').select('*').eq('id', user_id).execute()
        profile_data = profile_response.data[0] if profile_response.data else {}
        
        return User(
            id=uuid.UUID(user.id),
            email=user.email or "",
            full_name=profile_data.get('username') or user.user_metadata.get('full_name'),
            is_active=True,
            is_superuser=False,
            created_at=user.created_at,
            updated_at=user.updated_at or user.created_at
        )
        
    except Exception as e:
        logger.error(f"Error fetching user profile for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch user profile: {str(e)}"
        )

@app.put("/user/profile", response_model=User, status_code=status.HTTP_200_OK)
async def update_user_profile(user_update: UserUpdate, request: Request):
    """
    Update the current user's profile information.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Update user metadata in auth.users if needed
        update_data = {}
        if user_update.email:
            update_data['email'] = user_update.email
        if user_update.full_name:
            update_data['user_metadata'] = {'full_name': user_update.full_name}
        
        if update_data:
            supabase.auth.admin.update_user_by_id(user_id, update_data)
        
        # Update username in users table (only username, never email)
        if user_update.full_name:
            # Use UPDATE instead of UPSERT to avoid setting email to null
            update_response = supabase.table('users').update({
                'username': user_update.full_name
            }).eq('id', user_id).execute()
            
            # If no rows were updated, the user doesn't exist in users table
            # Create the record with email from auth.users
            if not update_response.data:
                auth_user = supabase.auth.admin.get_user_by_id(user_id)
                if auth_user.user and auth_user.user.email:
                    supabase.table('users').insert({
                        'id': user_id,
                        'email': auth_user.user.email,
                        'username': user_update.full_name
                    }).execute()
        
        # Fetch and return updated user profile
        return await get_user_profile(request)
        
    except Exception as e:
        logger.error(f"Error updating user profile for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update user profile: {str(e)}"
        )

@app.get("/user/stats", response_model=UserStatsResponse, status_code=status.HTTP_200_OK)
async def get_user_stats(request: Request):
    """
    Get comprehensive statistics for the current user.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Use the existing stats service
        stats = await get_user_stats_service(supabase, user_id)
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching user stats for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch user stats: {str(e)}"
        )

# User Settings Endpoints

@app.get("/user/settings", response_model=UserSettings, status_code=status.HTTP_200_OK)
async def get_user_settings(request: Request):
    """
    Get the current user's settings.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Get user settings from user_settings table
        response = supabase.table('user_settings').select('*').eq('user_id', user_id).execute()
        
        if not response.data:
            # Create default settings for new user
            default_settings = {
                'user_id': user_id,
                'native_language': 'en',
                'target_languages': ['es'],
                'email_notifications': True,
                'push_notifications': True,
                'daily_reminders': True,
                'weekly_progress': True,
                'reminder_time': '09:00',
                'theme': 'system',
                'app_language': 'en',
                'sound_effects': True,
                'animations': True,
                'difficulty_level': 'intermediate',
                'daily_goal': 100,
                'weekly_goal': 700,
                'auto_save': True,
                'show_hints': True,
                'public_profile': False,
                'share_progress': False,
                'analytics_opt_in': True
            }
            
            create_response = supabase.table('user_settings').insert(default_settings).execute()
            if create_response.data:
                settings_data = create_response.data[0]
            else:
                raise Exception("Failed to create default settings")
        else:
            settings_data = response.data[0]
        
        return UserSettings(
            id=uuid.UUID(settings_data['id']),
            user_id=uuid.UUID(settings_data['user_id']),
            native_language=settings_data['native_language'],
            target_languages=settings_data['target_languages'],
            email_notifications=settings_data['email_notifications'],
            push_notifications=settings_data['push_notifications'],
            daily_reminders=settings_data['daily_reminders'],
            weekly_progress=settings_data['weekly_progress'],
            reminder_time=settings_data['reminder_time'],
            theme=settings_data['theme'],
            app_language=settings_data['app_language'],
            sound_effects=settings_data['sound_effects'],
            animations=settings_data['animations'],
            difficulty_level=settings_data['difficulty_level'],
            daily_goal=settings_data['daily_goal'],
            weekly_goal=settings_data['weekly_goal'],
            auto_save=settings_data['auto_save'],
            show_hints=settings_data['show_hints'],
            public_profile=settings_data['public_profile'],
            share_progress=settings_data['share_progress'],
            analytics_opt_in=settings_data['analytics_opt_in'],
            created_at=settings_data['created_at'],
            updated_at=settings_data['updated_at'],
            # New multilingual fields from migration
            interface_lang=settings_data.get('interface_lang', 'en'),
            native_lang=settings_data.get('native_lang', 'en'),
            default_target_lang=settings_data.get('default_target_lang'),
            explanation_mode=settings_data.get('explanation_mode', 'bilingual'),
            immersion_level=settings_data.get('immersion_level', 1),
            strictness=settings_data.get('strictness', 'medium'),
            formality=settings_data.get('formality', 'neutral')
        )
        
    except Exception as e:
        logger.error(f"Error fetching user settings for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch user settings: {str(e)}"
        )

@app.put("/user/settings", response_model=UserSettings, status_code=status.HTTP_200_OK)
async def update_user_settings(settings_update: UserSettingsUpdate, request: Request):
    """
    Update the current user's settings.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Prepare update data, only including non-None fields
        update_data = {}
        for field, value in settings_update.model_dump(exclude_none=True).items():
            update_data[field] = value
        
        if not update_data:
            # If no fields to update, just return current settings
            return await get_user_settings(request)
        
        # Update settings in database
        response = supabase.table('user_settings').update(update_data).eq('user_id', user_id).execute()
        
        if not response.data:
            raise Exception("No settings found to update")
        
        # Return updated settings
        return await get_user_settings(request)
        
    except Exception as e:
        logger.error(f"Error updating user settings for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update user settings: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 
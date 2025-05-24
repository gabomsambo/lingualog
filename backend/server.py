"""
Main FastAPI application for the LinguaLog backend.

This module defines the FastAPI application and routes for handling journal entries
and generating AI feedback for language learning.
"""
import logging
import os
import sys
from typing import List, Optional

# Add current directory to path to make imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from models import (
    JournalEntryRequest, 
    FeedbackResponse, 
    LoginRequest,
    UserVocabularyItemCreate,
    UserVocabularyItemResponse
)
from app.models import JournalEntry # Corrected import for JournalEntry
from feedback_engine import generate_feedback, analyze_entry
from database import (
    save_entry, 
    fetch_entries, 
    sign_in_with_magic_link, 
    fetch_single_entry, 
    delete_entry,
    save_vocabulary_item,
    fetch_user_vocabulary,
    delete_vocabulary_item,
    fetch_vocabulary_item_by_term,
    init_db_schema
)

# Import the new router
from app.routers import vocabulary_ai # Adjusted import path

# Configure logger
# Ensure basicConfig is called to set up the root logger handler and level
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) # Output to stdout, set level to DEBUG

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set our specific logger to DEBUG as well
logger.propagate = True # Ensure messages go to the root logger

# Test log to see if basicConfig is working on startup
logger.debug("Root logger configured, LinguaLog API logger set to DEBUG.")

app = FastAPI(
    title="LinguaLog API",
    description="API for language learning journal with AI feedback",
    version="0.1.0"
)

# TODO: Tighten CORS origins once Vercel/Railway deployment domains are known
# Currently using permissive settings for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specific origin for credentials
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
    Process a journal entry and generate AI feedback.
    
    Args:
        entry: The journal entry text from the user
        request: The request object containing user info (if available)
        
    Returns:
        FeedbackResponse with grammar correction, rewriting, and other feedback dimensions
        
    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        # Get user_id from request headers if present
        user_id = request.headers.get("X-User-ID")
        
        # Generate feedback using the AI engine
        analysis = await analyze_entry(entry.text, entry.language)
        
        # Convert dictionary to Pydantic model for validation
        # Ensure all fields required by FeedbackResponse are present in analysis,
        # or provide defaults directly here if not handled by generate_feedback.
        feedback_response = FeedbackResponse(**{
            "corrected": analysis.get("corrected", entry.text), # Default to original if missing
            "rewritten": analysis.get("rewrite", entry.text), # Default to original if missing
            "score": analysis.get("score", 0),
            "tone": analysis.get("tone", "Neutral"),
            "translation": analysis.get("translation", "Translation not available."),
            "explanation": analysis.get("explanation", "No detailed explanation available."),
            "rubric": analysis.get("rubric", {"grammar": 0, "vocabulary": 0, "complexity": 0}),
            "grammar_suggestions": analysis.get("grammar_suggestions", []),
            "new_words": analysis.get("new_words", [])
        })
        
        # Save entry and feedback to Supabase - this is optional and shouldn't fail the request
        try:
            entry_data = {
                "user_id": user_id,  # Will be None if not authenticated
                "original_text": entry.text,
                "title": entry.title,
                "language": entry.language,
                "corrected": feedback_response.corrected,
                "rewrite": feedback_response.rewritten,
                "score": feedback_response.score,
                "tone": feedback_response.tone,
                "translation": feedback_response.translation,
                "explanation": feedback_response.explanation, # Added explanation
                "rubric": feedback_response.rubric.model_dump() if feedback_response.rubric else None, # Serialize Rubric
                "grammar_suggestions": [sugg.model_dump() for sugg in feedback_response.grammar_suggestions] if feedback_response.grammar_suggestions else [], # Serialize List[Suggestion]
                "new_words": [word.model_dump() for word in feedback_response.new_words] if feedback_response.new_words else [] # Serialize List[Word]
            }
            
            saved_entry = save_entry(entry_data)
            logger.info(f"Entry saved with ID: {saved_entry.get('id', 'unknown')}")
        except Exception as e:
            # Log the error but don't fail the request if database save fails
            logger.error(f"Failed to save entry to database: {str(e)}")
            # Continue to return the feedback even if saving fails
        
        return feedback_response
    except Exception as e:
        logger.error(f"Error generating feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating feedback: {str(e)}"
        )


@app.get("/entries", status_code=status.HTTP_200_OK)
async def get_entries(request: Request):
    """
    Retrieve journal entries for the authenticated user.
    
    Args:
        request: The request object containing user info (if available)
        
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

        entries = fetch_entries(user_id=user_id)
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
async def add_vocabulary_item_route(item: UserVocabularyItemCreate, request: Request):
    """
    Add a new word to the user's vocabulary.
    The user_id is extracted from the request headers.
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
        return saved_item # FastAPI will serialize this dict to UserVocabularyItemResponse based on the model
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

@app.get("/vocabulary", response_model=List[UserVocabularyItemResponse], status_code=status.HTTP_200_OK)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 
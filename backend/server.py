"""
Main FastAPI application for the LinguaLog backend.

This module defines the FastAPI application and routes for handling journal entries
and generating AI feedback for language learning.
"""
import logging
import os
import sys

# Add current directory to path to make imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware

from models import JournalEntryRequest, FeedbackResponse, LoginRequest
from feedback_engine import generate_feedback, analyze_entry
from database import save_entry, fetch_entries, sign_in_with_magic_link, fetch_single_entry

# Configure logger
logger = logging.getLogger(__name__)

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
        analysis = analyze_entry(entry.text)
        
        # Convert dictionary to Pydantic model for validation
        feedback_response = FeedbackResponse(**{
            "corrected": analysis["corrected"],
            "rewritten": analysis["rewrite"], 
            "score": analysis["fluency_score"],
            "tone": analysis["tone"],
            "translation": analysis["translation"],
            "explanation": analysis.get("explanation", "No detailed explanation available.")
        })
        
        # Save entry and feedback to Supabase - this is optional and shouldn't fail the request
        try:
            entry_data = {
                "user_id": user_id,  # Will be None if not authenticated
                "original_text": entry.text,
                "title": entry.title,
                "language": entry.language,
                "corrected": analysis["corrected"],
                "rewrite": analysis["rewrite"],
                "score": analysis["fluency_score"],
                "tone": analysis["tone"],
                "translation": analysis["translation"]
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


@app.get("/entries/{entry_id}", status_code=status.HTTP_200_OK)
async def get_single_entry(entry_id: str, request: Request):
    """
    Retrieve a single journal entry by its ID for the authenticated user.
    
    Args:
        entry_id: The ID of the journal entry to retrieve.
        request: The request object containing user info.
        
    Returns:
        The journal entry if found and belongs to the user.
    
    Raises:
        HTTPException: If the entry is not found or doesn't belong to the user, 
                       or if there's another error.
    """
    try:
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            logger.warning(f"Attempted to fetch entry {entry_id} without X-User-ID header.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not provided"
            )

        entry = fetch_single_entry(entry_id=entry_id, user_id=user_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry with id {entry_id} not found for user."
            )
        return entry
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error fetching single entry {entry_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching entry: {str(e)}"
        )


# TODO: Add user authentication middleware/dependencies

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 
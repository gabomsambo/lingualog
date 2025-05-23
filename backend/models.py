"""
Pydantic models for data validation and serialization.

This module defines the data models used for API requests and responses
in the LinguaLog application.
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class JournalEntryRequest(BaseModel):
    """Schema for submitting a journal entry."""
    text: str = Field(..., description="The journal entry text in the target language")
    title: str = Field("", description="The title of the journal entry")
    language: str = Field("", description="The language the journal entry is written in")
    
    # TODO: Add additional fields as needed (target language, etc.)


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(..., description="User's email address")


class FeedbackResponse(BaseModel):
    """Schema for AI feedback response."""
    corrected: str = Field("", description="Grammar-corrected version of the entry")
    rewritten: str = Field("", description="Native-like rewritten version")
    score: int = Field(0, description="Fluency score (0-100)", ge=0, le=100)
    tone: str = Field("", description="Detected emotional tone/style")
    translation: str = Field("", description="Direct translation to user's native language")
    explanation: Optional[str] = Field(None, description="Optional explanation of mistakes")
    
    # TODO: Add metrics/analytics fields as needed for progress tracking 
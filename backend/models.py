"""
Pydantic models for data validation and serialization.

This module defines the data models used for API requests and responses
in the LinguaLog application.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
import uuid


class JournalEntryRequest(BaseModel):
    """Schema for submitting a journal entry."""
    text: str = Field(..., description="The journal entry text in the target language")
    title: str = Field("", description="The title of the journal entry")
    language: str = Field("", description="The language the journal entry is written in")
    
    # TODO: Add additional fields as needed (target language, etc.)

    class Config:
        orm_mode = True


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(..., description="User's email address")


class Rubric(BaseModel):
    """Schema for the scoring rubric."""
    grammar: int = Field(0, description="Grammar score (0-100)", ge=0, le=100)
    vocabulary: int = Field(0, description="Vocabulary score (0-100)", ge=0, le=100)
    complexity: int = Field(0, description="Complexity score (0-100)", ge=0, le=100)


class Suggestion(BaseModel):
    """Schema for a grammar or style suggestion."""
    id: Optional[str] = Field(None, description="Unique ID for the suggestion, can be None if not persisted yet")
    original: str = Field(..., description="The original text snippet")
    corrected: str = Field(..., description="The suggested correction")
    note: str = Field(..., description="An explanatory note for the suggestion")
    dismissed: Optional[bool] = False


class Word(BaseModel):
    """Schema for a vocabulary word."""
    id: Optional[str] = Field(None, description="Unique ID for the word, can be None if not persisted yet")
    term: str = Field(..., description="The word or phrase")
    reading: Optional[str] = Field(None, description="Pronunciation or reading, e.g., for Japanese Kanji")
    pos: str = Field(..., description="Part of speech")
    definition: str = Field(..., description="Definition of the word")
    example: str = Field(..., description="Example sentence using the word")
    proficiency: str = Field(..., description="Estimated proficiency level (e.g., beginner, intermediate, advanced)")


class FeedbackResponse(BaseModel):
    """Schema for AI feedback response."""
    corrected: str = Field("", description="Grammar-corrected version of the entry")
    rewritten: str = Field("", description="Native-like rewritten version")
    score: int = Field(0, description="Fluency score (0-100)", ge=0, le=100)
    tone: str = Field("", description="Detected emotional tone/style")
    translation: str = Field("", description="Direct translation to user's native language")
    explanation: Optional[str] = Field(None, description="Optional explanation of mistakes")
    rubric: Optional[Rubric] = Field(None, description="Detailed scoring rubric for grammar, vocabulary, and complexity")
    grammar_suggestions: Optional[List[Suggestion]] = Field(None, description="List of specific grammar suggestions")
    new_words: Optional[List[Word]] = Field(None, description="List of new or notable vocabulary words")
    
    # TODO: Add metrics/analytics fields as needed for progress tracking 


class NewWord(BaseModel):
    """Schema for new words identified in the text."""
    term: str
    pos: Optional[str] = Field(None, description="Part of speech")
    definition: Optional[str] = None
    reading: Optional[str] = Field(None, description="Pronunciation aid, e.g., Furigana for Japanese")
    example: Optional[str] = Field(None, description="Example sentence from the entry")
    proficiency: Optional[str] = Field("unknown", description="User's proficiency with this word")
    id: Optional[str] = None


class UserVocabularyItemBase(BaseModel):
    """Base schema for a user vocabulary item."""
    term: str = Field(..., description="The vocabulary term.")
    language: str = Field(..., description="The language of the term.")
    part_of_speech: Optional[str] = Field(None, description="Part of speech.")
    definition: Optional[str] = Field(None, description="Definition of the term.")
    reading: Optional[str] = Field(None, description="Pronunciation aid (e.g., Furigana, Pinyin).")
    example_sentence: Optional[str] = Field(None, description="Example sentence using the term.")
    status: Optional[str] = Field("saved", description="Learning status of the item (e.g., saved, learning, mastered).")
    entry_id: Optional[str] = Field(None, description="ID of the journal entry where the word was sourced, if any.")


class UserVocabularyItemCreate(UserVocabularyItemBase):
    """Schema for creating a new user vocabulary item."""
    # user_id will be injected from the authenticated user server-side
    pass


class UserVocabularyItemResponse(UserVocabularyItemBase):
    """Schema for responding with a user vocabulary item."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Models for AI-enriched Vocabulary Data

class SynonymsAntonyms(BaseModel):
    """Structure for storing synonyms and antonyms."""
    synonyms: Optional[List[str]] = Field(None, description="List of synonyms.")
    antonyms: Optional[List[str]] = Field(None, description="List of antonyms.")

class WordAiCacheBase(BaseModel):
    """Base model for AI-generated word enrichment data."""
    language: str = Field(..., description="Language of the enriched word (e.g., 'en', 'es', 'ja').")
    ai_example_sentences: Optional[List[str]] = Field(None, description="AI-generated example sentences.")
    synonyms_antonyms: Optional[SynonymsAntonyms] = Field(None, description="AI-generated synonyms and antonyms.")
    related_phrases: Optional[List[str]] = Field(None, description="AI-generated related phrases or collocations.")
    cultural_note: Optional[str] = Field(None, description="AI-generated cultural note or usage insight.")
    emotion_tone: Optional[str] = Field(None, description="AI-detected typical emotion or tone of the word.")
    mnemonic: Optional[str] = Field(None, description="AI-generated mnemonic or metaphor for learning.")

class WordAiCacheCreate(WordAiCacheBase):
    """Model for creating an entry in the word_ai_cache table.
    word_vocabulary_id will be the ID of the item in UserVocabularyItem.
    """
    word_vocabulary_id: uuid.UUID = Field(..., description="Foreign key to the user_vocabulary table.")

class WordAiCacheDB(WordAiCacheCreate):
    """Model representing a record in the word_ai_cache table, including DB-specific fields."""
    id: uuid.UUID = Field(..., description="Primary key of the cache entry.")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class EnrichedWordDetailsResponse(WordAiCacheBase):
    """Response model for AI-enriched word details, including its own cache ID."""
    id: uuid.UUID = Field(..., description="Unique identifier for the AI cache entry.")
    word_vocabulary_id: uuid.UUID = Field(..., description="Identifier of the original vocabulary item this cache entry pertains to.")
    # Add created_at and updated_at if you want to expose them in this specific response
    # created_at: datetime = Field(..., description="Timestamp of cache creation.")
    # updated_at: datetime = Field(..., description="Timestamp of last cache update.")
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, HttpUrl, AliasChoices
import uuid
from datetime import datetime

# --- Authentication Models ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None # To update password
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class LoginRequest(BaseModel):
    username: EmailStr # Assuming email is used as username
    password: str

# --- User Settings Models ---
class LanguageProfile(BaseModel):
    """Immersion and proficiency for one target language."""
    l2: str
    immersion_level: int = Field(1, ge=0, le=3)
    proficiency: str = "A2"
    # False once the learner removes the language; the profile and its entries are kept.
    active: bool = True
    # Review settings. None on a save means leave the stored value alone.
    daily_new_words: Optional[int] = Field(None, ge=1, le=100)
    desired_retention: Optional[float] = Field(None, ge=0.80, le=0.95)
    goal: Optional[str] = None
    onboarded_at: Optional[datetime] = None


class UserSettings(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    native_language: str = "en"
    target_languages: List[str] = ["es"]
    email_notifications: bool = True
    push_notifications: bool = True
    daily_reminders: bool = True
    weekly_progress: bool = True
    reminder_time: str = "09:00"
    theme: str = "system"
    app_language: str = "en"
    sound_effects: bool = True
    animations: bool = True
    difficulty_level: str = "intermediate"
    daily_goal: int = 100
    weekly_goal: int = 700
    auto_save: bool = True
    show_hints: bool = True
    public_profile: bool = False
    share_progress: bool = False
    analytics_opt_in: bool = True
    created_at: datetime
    updated_at: datetime
    # New multilingual fields from migration
    interface_lang: str = "en"
    native_lang: str = "en" 
    default_target_lang: Optional[str] = None
    explanation_mode: str = "bilingual"
    explanation_mode_explicit: bool = False
    immersion_level: int = 1
    strictness: str = "medium"
    formality: str = "neutral"
    language_profiles: List[LanguageProfile] = Field(default_factory=list)

class UserSettingsUpdate(BaseModel):
    native_language: Optional[str] = None
    target_languages: Optional[List[str]] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    daily_reminders: Optional[bool] = None
    weekly_progress: Optional[bool] = None
    reminder_time: Optional[str] = None
    theme: Optional[str] = None
    app_language: Optional[str] = None
    sound_effects: Optional[bool] = None
    animations: Optional[bool] = None
    difficulty_level: Optional[str] = None
    daily_goal: Optional[int] = None
    weekly_goal: Optional[int] = None
    auto_save: Optional[bool] = None
    show_hints: Optional[bool] = None
    public_profile: Optional[bool] = None
    share_progress: Optional[bool] = None
    analytics_opt_in: Optional[bool] = None
    # New multilingual fields from migration
    interface_lang: Optional[str] = None
    native_lang: Optional[str] = None
    default_target_lang: Optional[str] = None
    explanation_mode: Optional[str] = None
    immersion_level: Optional[int] = None
    strictness: Optional[str] = None
    formality: Optional[str] = None
    language_profiles: Optional[List[LanguageProfile]] = None

# --- Journal Entry Models ---
class JournalEntryBase(BaseModel):
    language: str = Field(..., description="Language of the journal entry (e.g., 'en', 'es', 'ja').")
    title: Optional[str] = Field(None, max_length=255, description="Optional title for the entry.")
    content: str = Field(..., validation_alias=AliasChoices('content', 'original_text'), description="The main text content of the journal entry.")
    tags: Optional[List[str]] = Field(None, description="Optional tags for categorizing the entry.")

class JournalEntryCreate(JournalEntryBase):
    pass

class JournalEntryUpdate(JournalEntryBase):
    language: Optional[str] = None
    content: Optional[str] = None
    # Allow partial updates for all fields

class AiFeedback(BaseModel):
    # Use Union types and aliases to handle different data formats
    corrected_content: Optional[Union[str, Dict]] = Field(None, alias="corrected", validation_alias=AliasChoices("corrected", "corrected_content"))
    fluent_rewrite: Optional[Union[str, Dict]] = Field(None, alias="rewrite", validation_alias=AliasChoices("rewrite", "fluent_rewrite"))
    overall_score: Optional[Union[float, int, str]] = Field(None, alias="score", validation_alias=AliasChoices("score", "overall_score"))
    tone_analysis: Optional[Union[str, Dict[str, float]]] = Field(None, alias="tone", validation_alias=AliasChoices("tone", "tone_analysis"))
    style_analysis: Optional[Dict[str, float]] = Field(None) # Assuming this structure is fairly stable
    grammar_suggestions: Optional[Union[List[Dict[str, Any]], List[str]]] = Field(None)
    vocabulary_suggestions: Optional[List[Dict[str, Any]]] = Field(None)
    new_words_used: Optional[Union[List[str], List[Dict[str, Any]]]] = Field(None, alias="new_words", validation_alias=AliasChoices("new_words", "new_words_used"))
    explanation_of_changes: Optional[str] = Field(None, alias="explanation", validation_alias=AliasChoices("explanation", "explanation_of_changes"))

    # Add any fields that appear in logs but aren't in the model (or that you know might be present)
    translation: Optional[str] = Field(None)
    rubric: Optional[Dict[str, Any]] = Field(None) # Example of a potentially complex field
    sentence_mapping: Optional[List[Dict[str, Any]]] = None
    sentence_mapping_status: Optional[str] = None
    sentence_actions: Optional[List[Dict[str, Any]]] = None

    model_config = {
        "populate_by_name": True, # Allows use of aliases for population
        "from_attributes": True,  # Replaces orm_mode=True for Pydantic V2
        "extra": "ignore"         # Ignore unknown fields instead of failing
    }

class JournalEntry(JournalEntryBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    ai_feedback: Optional[AiFeedback] = None # Now directly part of the entry
    # LearningPolicy contract. `rewrite` is the stored column; `rewritten` is the
    # same text under the name the feedback response already uses.
    policy_snapshot: Optional[Dict[str, Any]] = None
    corrected: Optional[str] = None
    rewrite: Optional[str] = None
    rewritten: Optional[str] = None
    analysis_status: Optional[str] = None
    analysis_error_code: Optional[str] = None
    sentence_mapping: Optional[List[Dict[str, Any]]] = None
    sentence_mapping_status: Optional[str] = None
    sentence_actions: Optional[List[Dict[str, Any]]] = None
    target_language: Optional[str] = None
    detected_language: Optional[str] = None
    detected_language_kept: bool = False
    target_words: Optional[List[Dict[str, Any]]] = None
    target_word_uses: Optional[List[Dict[str, Any]]] = None
    focus_uses: Optional[List[Dict[str, Any]]] = None
    class_note_id: Optional[uuid.UUID] = None
    prompt_id: Optional[str] = None
    entry_mode: Optional[str] = None

    model_config = {
        "from_attributes": True, # Pydantic V2 way for orm_mode
        "extra": "ignore",
    }

class JournalEntryWithScore(JournalEntry): # For specific queries needing score prominently
    average_score: Optional[float] = None


# --- Translation Models ---
class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to be translated.")
    target_lang: str = Field(..., description="Target language code (e.g., 'en', 'es').")
    source_lang: Optional[str] = Field(None, description="Optional source language code. If not provided, auto-detection may be attempted.")

class TranslationOutput(BaseModel):
    translated_text: str = Field(..., description="The translated text.")
    detected_source_lang: Optional[str] = Field(None, description="The detected source language code (e.g., 'en', 'es').")


# --- System / Config Models ---
class AppEnvironment(BaseModel):
    ENV_NAME: str
    SENTRY_DSN: Optional[HttpUrl] = None
    # Add other critical environment variables here

    # Supabase
    SUPABASE_URL: HttpUrl
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str # For admin operations

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days


    # AI Provider Config
    AI_PROVIDER: str = "gemini" # gemini, openai, mistral, claude etc.
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    # ... other provider keys

    model_config = {
        "extra": "ignore" # Allow other env vars not explicitly defined
    }

class MessageResponse(BaseModel):
    message: str

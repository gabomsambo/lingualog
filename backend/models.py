"""
Pydantic models for data validation and serialization.

This module defines the data models used for API requests and responses
in the LinguaLog application.
"""
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class AnalyzeEntryRequest(BaseModel):
    """Optional body for POST /entries/{id}/analyze."""
    target_language: Optional[str] = Field(
        None,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="Re-analyse the entry as this studied language (the did-you-mean switch)",
    )


class JournalEntryRequest(BaseModel):
    """Schema for submitting a journal entry."""
    text: str = Field(..., description="The journal entry text in the target language")
    title: str = Field("", description="The title of the journal entry")
    language: str = Field("", description="The language the journal entry is written in")
    
    # Optional language overrides for this specific entry
    target_language: Optional[str] = Field(None, description="Override target language for this entry")
    ui_language: Optional[str] = Field(None, description="UI language for this request")
    explanation_mode: Optional[str] = Field(None, description="Override explanation mode (native_only, target_only, bilingual, smart)")
    strictness: Optional[str] = Field(None, description="Override correction strictness (gentle, medium, strict, pedantic)")
    formality: Optional[str] = Field(None, description="Override formality level (casual, neutral, formal, academic)")
    immersion_level: Optional[int] = Field(None, description="Override immersion level (0-3)", ge=0, le=3)
    prompt_id: Optional[str] = Field(None, min_length=1, max_length=100)
    entry_mode: Optional[Literal["idea", "frame", "one_sentence"]] = None
    class_note_id: Optional[UUID] = Field(None, description="Class note this entry practises")

    # Word bank: words from the learner's notebook they chose to write with in this entry
    target_word_ids: List[UUID] = Field(
        default_factory=list, max_length=30, description="Notebook words the learner meant to use in this entry"
    )
    challenge_word_ids: List[UUID] = Field(
        default_factory=list,
        max_length=30,
        description="Target words whose text stayed hidden while writing; a correct use is real recall",
    )

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
    note_l1: Optional[str] = Field("", description="Note in the learner's language")
    note_l2: Optional[str] = Field("", description="Note in the target language")
    meaning_changing: Optional[bool] = Field(False, description="True when the words as written mean something else")
    literal_reading: Optional[str] = Field("", description="As written, a native reads…")
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
    id: Optional[str] = Field(None, description="ID of the saved journal entry")
    entry_id: Optional[str] = Field(
        None, description="Saved journal entry id when persistence succeeded"
    )
    corrected: str = Field("", description="Grammar-corrected version of the entry")
    rewritten: str = Field("", description="Native-like rewritten version")
    score: int = Field(0, description="Fluency score (0-100)", ge=0, le=100)
    tone: str = Field("", description="Detected emotional tone/style")
    did_well: Optional[str] = Field(
        None, description="One short, specific positive observation when the tutor has one"
    )
    translation: str = Field("", description="Direct translation to user's native language (populated by Lara in a later PR)")
    explanation: Optional[str] = Field(None, description="Optional explanation of mistakes")
    rubric: Optional[Rubric] = Field(None, description="Detailed scoring rubric for grammar, vocabulary, and complexity")
    grammar_suggestions: Optional[List[Suggestion]] = Field(None, description="List of specific grammar suggestions")
    new_words: Optional[List[Word]] = Field(None, description="List of new or notable vocabulary words")
    is_mock: bool = Field(default=False, description="True when this feedback was generated by the mock provider")
    intended_meaning: Optional[str] = Field(None, description="What the learner meant, inferred by the tutor")
    ambiguities: Optional[List[Dict[str, Any]]] = Field(None, description="Questions asked when the meaning was unclear")
    rewrite_idioms: Optional[List[Dict[str, Any]]] = Field(None, description="Idiom glosses for the rewrite")
    sentence_mapping: Optional[List[Dict[str, Any]]] = Field(
        None, description="Validated original-to-corrected sentence index mapping"
    )
    sentence_mapping_status: Optional[str] = Field(
        None,
        description="valid for authoritative mappings, invalid* when the model mapping was rejected, null when none was stored",
    )
    sentence_actions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description=(
            "Per-source-sentence explanation for any removed/merged sentence. Always"
            " non-empty when sentence_mapping contains a removal or merge and is null"
            " otherwise. The UI shows these in 'What to fix'."
        ),
    )
    detected_language: Optional[str] = Field(
        None, description="ISO 639-1 code of the language the entry is written in, as read by the tutor"
    )
    target_word_uses: Optional[List[Dict[str, Any]]] = Field(
        None,
        description=(
            "How each word-bank word was used: status, the form written, a fix or question, and"
            " what the use did to the word. Null when no words were chosen"
        ),
    )
    focus_uses: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="How the learner used the grammar focus selected from their class note",
    )

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
    status: Literal["new", "learning", "known", "mastered", "ignored"] = Field(
        "new", description="Notebook state for this word."
    )
    entry_id: Optional[str] = Field(None, description="ID of the journal entry where the word was sourced, if any.")


class UserVocabularyItemCreate(UserVocabularyItemBase):
    """Schema for creating a new user vocabulary item."""
    encounter_id: Optional[str] = Field(
        None, description="Lookup encounter whose cached card and context should be reused."
    )


class LookupRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    sentence: Optional[str] = Field(None, max_length=5000)
    language: str = Field(..., min_length=2, max_length=35)
    source: Literal["entry", "manual", "book_session"]
    source_id: Optional[UUID] = None
    kind: Literal["lookup", "entry_text", "entry_fix", "entry_rewrite"] = "lookup"
    page: Optional[int] = Field(None, ge=1, le=20000, description="Book page, for a lookup made in a reading session")


class UserVocabularyItemPatch(BaseModel):
    """User-editable vocabulary fields."""

    note: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = Field(None, max_length=50)
    status: Optional[Literal["new", "learning", "known", "mastered", "ignored"]] = None


class UserVocabularyItemResponse(UserVocabularyItemBase):
    """Schema for responding with a user vocabulary item."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    lemma: Optional[str] = None
    sense: Optional[str] = None
    card: Optional[Dict[str, Any]] = None
    card_status: Literal["pending", "ok", "failed"] = "pending"
    card_policy: Optional[Dict[str, Any]] = None
    note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    class Config:
        orm_mode = True


class LookupResponse(BaseModel):
    encounter_id: str
    text: str
    language: str
    lemma: str
    sense: str
    card: Optional[Dict[str, Any]] = None
    card_status: Literal["ok", "failed"]
    card_policy: Dict[str, Any]
    seen_count: int
    saved_item: Optional[UserVocabularyItemResponse] = None

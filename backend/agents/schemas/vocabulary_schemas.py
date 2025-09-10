"""
Pydantic schemas for vocabulary-related AI operations.

These schemas define the input and output structures for vocabulary enrichment,
quiz generation, and ELI5 explanations.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from atomic_agents import BaseIOSchema


class VocabularyEnrichmentInputSchema(BaseIOSchema):
    """Input schema for vocabulary enrichment agent."""
    
    term: str = Field(..., description="The vocabulary term to enrich")
    language: str = Field(..., description="Language of the term")
    context: Optional[str] = Field(None, description="Optional context where the term was found")
    user_level: Optional[str] = Field("intermediate", description="User's proficiency level")


class Definition(BaseModel):
    """A definition with part of speech."""
    
    part_of_speech: str = Field(..., description="Part of speech (noun, verb, adjective, etc.)")
    definition: str = Field(..., description="The definition text")


class CommonMistake(BaseModel):
    """A common mistake and its correction."""
    
    mistake: str = Field(..., description="The common mistake")
    correction: str = Field(..., description="The correct form")
    explanation: Optional[str] = Field(None, description="Explanation of why it's wrong")


class VocabularyEnrichmentOutputSchema(BaseIOSchema):
    """Output schema for vocabulary enrichment agent."""
    
    term: str = Field(..., description="The enriched vocabulary term")
    language: str = Field(..., description="Language of the term")
    ai_example_sentences: List[str] = Field(
        default_factory=list,
        description="AI-generated example sentences"
    )
    ai_definitions: List[Definition] = Field(
        default_factory=list,
        description="AI-generated definitions with parts of speech"
    )
    ai_synonyms: List[str] = Field(
        default_factory=list,
        description="AI-generated synonyms"
    )
    ai_antonyms: List[str] = Field(
        default_factory=list,
        description="AI-generated antonyms"
    )
    ai_related_phrases: List[str] = Field(
        default_factory=list,
        description="AI-generated related phrases and collocations"
    )
    ai_cultural_note: Optional[str] = Field(
        None,
        description="Cultural context or usage notes"
    )
    ai_pronunciation_guide: Optional[str] = Field(
        None,
        description="Pronunciation guide"
    )
    ai_alternative_forms: List[str] = Field(
        default_factory=list,
        description="Alternative forms of the word"
    )
    ai_common_mistakes: List[CommonMistake] = Field(
        default_factory=list,
        description="Common mistakes when using this word"
    )
    emotion_tone: Optional[str] = Field(
        None,
        description="Emotional tone or feeling associated with this word"
    )
    mnemonic: Optional[str] = Field(
        None,
        description="Memory aid, metaphor, or mnemonic device for remembering this word"
    )
    ai_conjugation_info: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Conjugation information for verbs/adjectives (e.g., {'present': 'habla', 'past': 'habló'})"
    )
    emoji: Optional[str] = Field(
        None,
        description="Emoji that represents the emotion or concept of this word"
    )


class ELI5InputSchema(BaseIOSchema):
    """Input schema for ELI5 (Explain Like I'm 5) agent."""
    
    term: str = Field(..., description="The term to explain simply")
    language: str = Field(..., description="Language of the term")
    context: Optional[str] = Field(None, description="Context where the term was encountered")


class ELI5OutputSchema(BaseIOSchema):
    """Output schema for ELI5 agent."""
    
    explanation: str = Field(..., description="Simple, easy-to-understand explanation")


class QuizQuestion(BaseModel):
    """A single quiz question."""
    
    question_text: str = Field(..., description="The question text")
    options: List[str] = Field(..., description="Multiple choice options")
    correct_answer_index: int = Field(..., ge=0, description="Index of the correct answer (0-based)")
    explanation: Optional[str] = Field(None, description="Explanation of the correct answer")


class QuizGenerationInputSchema(BaseIOSchema):
    """Input schema for quiz generation agent."""
    
    word: str = Field(..., description="The word to create a quiz about")
    language: str = Field(..., description="Language of the word")
    num_questions: Optional[int] = Field(3, ge=1, le=10, description="Number of questions to generate")
    difficulty: Optional[str] = Field("medium", description="Quiz difficulty level")


class QuizGenerationOutputSchema(BaseIOSchema):
    """Output schema for quiz generation agent."""
    
    quiz_title: str = Field(..., description="Title of the quiz")
    questions: List[QuizQuestion] = Field(..., description="List of quiz questions")


class MoreExamplesInputSchema(BaseIOSchema):
    """Input schema for generating more examples agent."""
    
    word: str = Field(..., description="The word to generate examples for")
    language: str = Field(..., description="Language of the word")
    existing_examples: Optional[List[str]] = Field(
        default_factory=list,
        description="Existing examples to avoid duplicating"
    )
    target_audience_level: Optional[str] = Field(
        "intermediate",
        description="Target audience proficiency level"
    )
    num_examples: Optional[int] = Field(3, ge=1, le=10, description="Number of examples to generate")


class MoreExamplesOutputSchema(BaseIOSchema):
    """Output schema for generating more examples agent."""
    
    new_example_sentences: List[str] = Field(
        ...,
        description="List of new example sentences"
    )

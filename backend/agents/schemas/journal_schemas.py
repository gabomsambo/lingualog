"""
Pydantic schemas for journal analysis agents.

These schemas define the input and output structures for journal-related AI operations,
ensuring type safety and validation while maintaining compatibility with existing API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from atomic_agents import BaseIOSchema


class GrammarSuggestion(BaseModel):
    """A single grammar correction suggestion."""
    
    original: str = Field(..., description="The original problematic text snippet")
    corrected: str = Field(..., description="The suggested correction for the snippet")
    note: str = Field(..., description="Brief explanation of the grammar rule or reason for correction")


class NewWord(BaseModel):
    """A new or notable vocabulary word identified in the text."""
    
    term: str = Field(..., description="The new or notable word/phrase")
    reading: Optional[str] = Field(None, description="Pronunciation or reading (e.g., for Japanese Kanji)")
    pos: str = Field(..., description="Part of speech (e.g., 'noun', 'verb', 'adjective')")
    definition: str = Field(..., description="A concise definition of the word in English")
    example: str = Field(..., description="An example sentence using the word")
    proficiency: str = Field(..., description="Estimated proficiency level (e.g., 'beginner', 'intermediate', 'advanced')")


class FluencyRubric(BaseModel):
    """Detailed scoring rubric for different aspects of language use."""
    
    grammar: int = Field(..., ge=0, le=100, description="Grammar score (0-100)")
    vocabulary: int = Field(..., ge=0, le=100, description="Vocabulary usage score (0-100)")
    complexity: int = Field(..., ge=0, le=100, description="Sentence/idea complexity score (0-100)")


class JournalAnalysisInputSchema(BaseIOSchema):
    """Input schema for journal analysis agent."""
    
    text: str = Field(..., description="The journal entry text to analyze")
    language: str = Field(..., description="The language of the journal entry")
    title: Optional[str] = Field(None, description="Optional title for the journal entry")
    user_level: Optional[str] = Field("intermediate", description="User's proficiency level")


class JournalAnalysisOutputSchema(BaseIOSchema):
    """Output schema for journal analysis agent - matches current FeedbackResponse."""
    
    corrected: str = Field(..., description="Grammar-corrected version of the text")
    rewritten: str = Field(..., description="More natural/native-like rewrite of the text")
    score: int = Field(..., ge=0, le=100, description="Overall fluency score (0-100)")
    tone: str = Field(..., description="Detected emotional tone (e.g., 'Reflective', 'Confident', 'Neutral')")
    translation: str = Field(..., description="Translation to English (or French if already English)")
    explanation: str = Field(..., description="Brief explanation of main issues or positive feedback")
    rubric: FluencyRubric = Field(..., description="Detailed scoring breakdown")
    grammar_suggestions: List[GrammarSuggestion] = Field(
        default_factory=list, 
        description="List of specific grammar corrections"
    )
    new_words: List[NewWord] = Field(
        default_factory=list, 
        description="List of new or notable vocabulary words"
    )


class TranslationInputSchema(BaseIOSchema):
    """Input schema for translation agent."""
    
    text: str = Field(..., description="Text to translate")
    source_language: str = Field(..., description="Source language of the text")
    target_language: str = Field(..., description="Target language for translation")
    context: Optional[str] = Field(None, description="Additional context for better translation")


class TranslationOutputSchema(BaseIOSchema):
    """Output schema for translation agent."""
    
    translated_text: str = Field(..., description="The translated text")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Translation confidence score")
    notes: Optional[str] = Field(None, description="Any notes about the translation")


class VocabularyExtractionInputSchema(BaseIOSchema):
    """Input schema for vocabulary extraction agent."""
    
    text: str = Field(..., description="Text to extract vocabulary from")
    language: str = Field(..., description="Language of the text")
    difficulty_level: Optional[str] = Field("intermediate", description="Target difficulty level")
    max_words: Optional[int] = Field(10, description="Maximum number of words to extract")


class VocabularyExtractionOutputSchema(BaseIOSchema):
    """Output schema for vocabulary extraction agent."""
    
    extracted_words: List[NewWord] = Field(
        default_factory=list,
        description="List of vocabulary words extracted from the text"
    )

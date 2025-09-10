"""
Atomic Agents schemas for LinguaLog.

This module exports all the Pydantic schemas used by the various AI agents
for type safety and validation.
"""

from .journal_schemas import (
    JournalAnalysisInputSchema,
    JournalAnalysisOutputSchema,
    TranslationInputSchema,
    TranslationOutputSchema,
    VocabularyExtractionInputSchema,
    VocabularyExtractionOutputSchema,
    GrammarSuggestion,
    NewWord,
    FluencyRubric,
)

from .vocabulary_schemas import (
    VocabularyEnrichmentInputSchema,
    VocabularyEnrichmentOutputSchema,
    ELI5InputSchema,
    ELI5OutputSchema,
    QuizGenerationInputSchema,
    QuizGenerationOutputSchema,
    MoreExamplesInputSchema,
    MoreExamplesOutputSchema,
    QuizQuestion,
    Definition,
    CommonMistake,
)

__all__ = [
    # Journal schemas
    "JournalAnalysisInputSchema",
    "JournalAnalysisOutputSchema", 
    "TranslationInputSchema",
    "TranslationOutputSchema",
    "VocabularyExtractionInputSchema",
    "VocabularyExtractionOutputSchema",
    "GrammarSuggestion",
    "NewWord",
    "FluencyRubric",
    
    # Vocabulary schemas
    "VocabularyEnrichmentInputSchema",
    "VocabularyEnrichmentOutputSchema",
    "ELI5InputSchema",
    "ELI5OutputSchema",
    "QuizGenerationInputSchema",
    "QuizGenerationOutputSchema",
    "MoreExamplesInputSchema",
    "MoreExamplesOutputSchema",
    "QuizQuestion",
    "Definition",
    "CommonMistake",
]

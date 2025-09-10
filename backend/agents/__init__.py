"""
Atomic Agents for LinguaLog.

This module exports all the AI agents used by LinguaLog for various tasks
including journal analysis, vocabulary enrichment, and educational content generation.
"""

from .core.journal_analysis_agent import JournalAnalysisAgent
from .core.vocabulary_enrichment_agent import VocabularyEnrichmentAgent
from .core.quiz_generation_agent import QuizGenerationAgent
from .schemas import (
    # Journal schemas
    JournalAnalysisInputSchema,
    JournalAnalysisOutputSchema,
    TranslationInputSchema,
    TranslationOutputSchema,
    VocabularyExtractionInputSchema,
    VocabularyExtractionOutputSchema,
    GrammarSuggestion,
    NewWord,
    FluencyRubric,
    
    # Vocabulary schemas
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
    # Agents
    "JournalAnalysisAgent",
    "VocabularyEnrichmentAgent", 
    "QuizGenerationAgent",
    
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

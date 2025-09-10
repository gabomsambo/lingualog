"""
Vocabulary Enrichment Agent using Atomic Agents framework.

This agent provides comprehensive vocabulary enrichment including definitions,
examples, synonyms, antonyms, cultural notes, and advanced linguistic features.
"""

import os
import logging
from typing import Optional
import instructor
from openai import OpenAI, AsyncOpenAI
from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas import VocabularyEnrichmentInputSchema, VocabularyEnrichmentOutputSchema
from ..context_providers import UserPreferencesProvider

logger = logging.getLogger(__name__)


class VocabularyEnrichmentAgent:
    """
    Atomic Agent for comprehensive vocabulary enrichment.
    
    This agent provides rich linguistic data including definitions, examples,
    synonyms, antonyms, cultural context, pronunciation guides, and common mistakes.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "openai", use_async: bool = False):
        
        # Create system prompt generator with rich context for vocabulary enrichment
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are a highly skilled language educator and linguist specializing in vocabulary enrichment.",
                "Your expertise covers etymology, cultural context, pragmatics, and pedagogical best practices.",
                "You provide comprehensive, accurate, and pedagogically sound vocabulary information.",
            ],
            steps=[
                "Analyze the vocabulary term within its linguistic and cultural context",
                "Generate multiple accurate definitions with clear part-of-speech classifications", 
                "Create diverse, natural example sentences that demonstrate proper usage",
                "Identify meaningful synonyms and antonyms that preserve nuanced meaning",
                "Provide relevant collocations and phrase patterns",
                "Include cultural context and pragmatic usage notes where applicable",
                "Add pronunciation guidance using clear, learner-friendly notation",
                "Identify common learner mistakes and their corrections",
                "Ensure all content is appropriate for the user's proficiency level",
            ],
            output_instructions=[
                "Provide comprehensive vocabulary data using the exact schema format",
                "Ensure all example sentences are natural and contextually appropriate",
                "Include 3-5 high-quality definitions with clear part-of-speech labels",
                "Generate 5-8 diverse example sentences showcasing different contexts",
                "Provide 4-6 meaningful synonyms and 3-4 relevant antonyms",
                "Include 3-5 related phrases and collocations",
                "Add cultural context that helps learners understand appropriate usage",
                "Provide pronunciation guidance suitable for learners",
                "Include 2-3 common mistakes with clear corrections",
                "Generate emotion_tone describing the feeling/tone of the word",
                "Create a memorable mnemonic, metaphor, or memory device",
                "For verbs/adjectives, provide conjugation information in ai_conjugation_info",
                "Choose an appropriate emoji that represents the word's meaning or emotion",
                "Adapt complexity and detail to the user's proficiency level",
                "Focus on practical, real-world usage rather than academic definitions",
            ]
        )
        
        # Initialize the appropriate client
        if provider == "openai":
            # Handle both naming conventions for API key
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY or OPEN_AI_API_KEY in environment.")
            
            if use_async:
                client = instructor.from_openai(AsyncOpenAI(api_key=api_key))
            else:
                client = instructor.from_openai(OpenAI(api_key=api_key))
        else:
            raise ValueError(f"Provider {provider} not yet supported")
        
        # Create the atomic agent
        self.agent = AtomicAgent[VocabularyEnrichmentInputSchema, VocabularyEnrichmentOutputSchema](
            config=AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=system_prompt_generator,
                history=ChatHistory(),
            )
        )
        
        logger.info(f"VocabularyEnrichmentAgent initialized with {provider} {model}")
    
    def enrich(self, 
               term: str, 
               language: str, 
               context: Optional[str] = None, 
               user_level: Optional[str] = "intermediate") -> VocabularyEnrichmentOutputSchema:
        """
        Generate comprehensive vocabulary enrichment data for a term.
        
        Args:
            term: The vocabulary term to enrich
            language: The language of the term (e.g., 'en', 'ja', 'es')
            context: Optional context where the term was encountered
            user_level: User's proficiency level (beginner, intermediate, advanced)
            
        Returns:
            VocabularyEnrichmentOutputSchema with all enrichment data
        """
        logger.info(f"Enriching vocabulary term: '{term}' in language: {language}")
        
        # Add user preferences context for personalized output
        user_prefs = UserPreferencesProvider(
            user_level=user_level,
            native_language="English",  # Could be made configurable
            feedback_style="encouraging",
            focus_areas=["vocabulary", "cultural_context", "usage"]
        )
        
        # Create input schema
        input_data = VocabularyEnrichmentInputSchema(
            term=term,
            language=language,
            context=context,
            user_level=user_level
        )
        
        # Run the agent
        try:
            result = self.agent.run(input_data)
            
            logger.info(f"Successfully enriched term '{term}' with {len(result.ai_definitions)} definitions, "
                       f"{len(result.ai_example_sentences)} examples, {len(result.ai_synonyms)} synonyms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching vocabulary term '{term}': {e}", exc_info=True)
            # Return minimal valid structure on error
            return VocabularyEnrichmentOutputSchema(
                term=term,
                language=language,
                ai_definitions=[],
                ai_example_sentences=[],
                ai_synonyms=[],
                ai_antonyms=[],
                ai_related_phrases=[],
                ai_cultural_note=f"Error generating enrichment data: {str(e)}",
                ai_pronunciation_guide="",
                ai_alternative_forms=[],
                ai_common_mistakes=[]
            )
    
    async def enrich_async(self, 
                          term: str, 
                          language: str, 
                          context: Optional[str] = None, 
                          user_level: Optional[str] = "intermediate") -> VocabularyEnrichmentOutputSchema:
        """
        Async version of enrich method.
        """
        logger.info(f"Async enriching vocabulary term: '{term}' in language: {language}")
        
        # Add user preferences context for personalized output
        user_prefs = UserPreferencesProvider(
            user_level=user_level,
            native_language="English",  # Could be made configurable
            feedback_style="encouraging",
            focus_areas=["vocabulary", "cultural_context", "usage"]
        )
        
        # Create input schema
        input_data = VocabularyEnrichmentInputSchema(
            term=term,
            language=language,
            context=context,
            user_level=user_level
        )
        
        # Run the agent (async)
        try:
            result = self.agent.run(input_data)
            
            logger.info(f"Successfully enriched term '{term}' with {len(result.ai_definitions)} definitions, "
                       f"{len(result.ai_example_sentences)} examples, {len(result.ai_synonyms)} synonyms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching vocabulary term '{term}': {e}", exc_info=True)
            # Return minimal valid structure on error
            return VocabularyEnrichmentOutputSchema(
                term=term,
                language=language,
                ai_definitions=[],
                ai_example_sentences=[],
                ai_synonyms=[],
                ai_antonyms=[],
                ai_related_phrases=[],
                ai_cultural_note=f"Error generating enrichment data: {str(e)}",
                ai_pronunciation_guide="",
                ai_alternative_forms=[],
                ai_common_mistakes=[]
            )

"""
Journal Analysis Agent using Atomic Agents framework.

This agent analyzes journal entries for grammar, fluency, tone, and provides
comprehensive feedback including corrections, rewriting, and vocabulary insights.
"""

import os
import logging
from typing import Optional
import instructor
from openai import OpenAI, AsyncOpenAI
from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas import JournalAnalysisInputSchema, JournalAnalysisOutputSchema

logger = logging.getLogger(__name__)


class JournalAnalysisAgent:
    """
    Atomic Agent for comprehensive journal entry analysis.
    
    This agent provides grammar correction, fluency scoring, tone detection,
    native-like rewriting, translation, and vocabulary identification.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "openai", use_async: bool = False):
        """
        Initialize the Journal Analysis Agent.
        
        Args:
            model: The AI model to use (default: gpt-4o-mini)
            provider: The AI provider (default: openai)
            use_async: Whether to use async client (default: False)
        """
        self.model = model
        self.provider = provider
        self.use_async = use_async
        
        # Set up the system prompt
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an expert language tutor and linguist specializing in language learning feedback.",
                "Your role is to analyze journal entries written by language learners and provide comprehensive, constructive feedback.",
                "You have deep knowledge of grammar rules, vocabulary usage, cultural context, and natural language patterns across multiple languages.",
                "Your feedback should be encouraging while being precise and educational."
            ],
            steps=[
                "1. Read and understand the journal entry text and identify the language being used.",
                "2. Analyze the text for grammar errors, awkward phrasing, and areas for improvement.",
                "3. Assess the overall fluency level and assign appropriate scores for grammar, vocabulary, and complexity.",
                "4. Identify the emotional tone and style of the writing.",
                "5. Create a grammar-corrected version that fixes errors while preserving the original meaning and voice.",
                "6. Generate a more natural, native-like rewrite that improves flow and naturalness.",
                "7. Translate the original text appropriately (to English if not English, to French if already English).",
                "8. Identify 3-5 specific grammar suggestions with explanations.",
                "9. Extract 2-5 notable vocabulary words that are advanced, incorrectly used, or worth learning.",
                "10. Provide a brief, encouraging explanation of the main points for improvement."
            ],
            output_instructions=[
                "Provide all feedback in the exact JSON structure specified by the output schema.",
                "Ensure the corrected text fixes errors while maintaining the learner's original voice and intent.",
                "Make the rewritten version sound more natural and fluent while keeping the same meaning.",
                "Score grammar, vocabulary, and complexity on a 0-100 scale appropriate to the learner's level.",
                "Choose tone descriptions that are accurate and helpful (e.g., 'Reflective', 'Excited', 'Analytical').",
                "Grammar suggestions should be specific, actionable, and educational.",
                "New words should include clear definitions and example usage.",
                "Keep explanations encouraging and focus on 1-2 key improvement areas."
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
        self.agent = AtomicAgent[JournalAnalysisInputSchema, JournalAnalysisOutputSchema](
            config=AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=system_prompt_generator,
                history=ChatHistory(),
            )
        )
        
        logger.info(f"JournalAnalysisAgent initialized with {provider} {model}")
    
    def analyze(self, text: str, language: str, title: Optional[str] = None, user_level: Optional[str] = "intermediate", user_id: Optional[str] = None) -> JournalAnalysisOutputSchema:
        """
        Analyze a journal entry and return comprehensive feedback.
        
        Args:
            text: The journal entry text to analyze
            language: The language of the journal entry
            title: Optional title for the journal entry
            user_level: User's proficiency level (beginner, intermediate, advanced)
            user_id: Optional user ID for personalized context
            
        Returns:
            JournalAnalysisOutputSchema with comprehensive feedback
        """
        try:
            # Add context providers for personalized feedback
            if user_id:
                self._add_context_providers(language, user_level, user_id)
            
            # Create input schema
            input_data = JournalAnalysisInputSchema(
                text=text,
                language=language,
                title=title,
                user_level=user_level
            )
            
            logger.info(f"Analyzing journal entry in {language} (length: {len(text)} chars)")
            
            # Run the agent
            result = self.agent.run(input_data)
            
            logger.info(f"Journal analysis completed - Score: {result.score}, Tone: {result.tone}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in journal analysis: {str(e)}")
            raise
    
    def _add_context_providers(self, language: str, user_level: str, user_id: str):
        """
        Add context providers for personalized feedback.
        
        Args:
            language: Target language being learned
            user_level: User's proficiency level
            user_id: User identifier for personalized context
        """
        try:
            from ..context_providers.user_preferences_provider import (
                UserPreferencesProvider, 
                LanguageContextProvider
            )
            
            # Add user preferences context
            user_prefs = UserPreferencesProvider(
                user_level=user_level,
                native_language="English",  # Could be retrieved from user profile
                feedback_style="encouraging"
            )
            self.agent.register_context_provider("user_preferences", user_prefs)
            
            # Add language-specific context
            lang_context = LanguageContextProvider(target_language=language)
            self.agent.register_context_provider("language_context", lang_context)
            
            logger.info(f"Added context providers for user {user_id}, language {language}")
            
        except Exception as e:
            logger.warning(f"Failed to add context providers: {str(e)}")
            # Continue without context providers if they fail
    
    async def analyze_async(self, text: str, language: str, title: Optional[str] = None, user_level: Optional[str] = "intermediate", user_id: Optional[str] = None) -> JournalAnalysisOutputSchema:
        """
        Async version of analyze method.
        
        Args:
            text: The journal entry text to analyze
            language: The language of the journal entry
            title: Optional title for the journal entry
            user_level: User's proficiency level
            user_id: Optional user ID for personalized context
            
        Returns:
            JournalAnalysisOutputSchema with comprehensive feedback
        """
        try:
            # Add context providers for personalized feedback
            if user_id:
                self._add_context_providers(language, user_level, user_id)
            
            # Create input schema
            input_data = JournalAnalysisInputSchema(
                text=text,
                language=language,
                title=title,
                user_level=user_level
            )
            
            logger.info(f"Analyzing journal entry in {language} (async, length: {len(text)} chars)")
            
            # Run the agent asynchronously
            result = await self.agent.run_async(input_data)
            
            logger.info(f"Async journal analysis completed - Score: {result.score}, Tone: {result.tone}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in async journal analysis: {str(e)}")
            raise


def create_journal_analysis_agent(model: str = "gpt-4o-mini", provider: str = "openai", use_async: bool = False) -> JournalAnalysisAgent:
    """
    Factory function to create a JournalAnalysisAgent.
    
    Args:
        model: The AI model to use
        provider: The AI provider to use
        use_async: Whether to use async client
        
    Returns:
        Configured JournalAnalysisAgent instance
    """
    return JournalAnalysisAgent(model=model, provider=provider, use_async=use_async)

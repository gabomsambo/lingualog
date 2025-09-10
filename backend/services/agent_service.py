"""
Agent Service - Wrapper for Atomic Agents to maintain API compatibility.

This service provides a bridge between the existing LinguaLog API and the new
Atomic Agents implementation, ensuring backward compatibility while enabling
gradual migration.
"""

import logging
from typing import Dict, Any, Optional
import asyncio
from functools import lru_cache

from agents.core.journal_analysis_agent import create_journal_analysis_agent
from agents.schemas import JournalAnalysisOutputSchema

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service class that wraps Atomic Agents for backward compatibility.
    
    This service maintains the same interface as the old feedback_engine
    while using the new Atomic Agents architecture underneath.
    """
    
    def __init__(self):
        """Initialize the agent service."""
        self._journal_agent_sync = None
        self._journal_agent_async = None
        self._initialized = False
    
    def _get_journal_agent_sync(self):
        """Lazy initialization of the sync journal analysis agent."""
        if self._journal_agent_sync is None:
            try:
                self._journal_agent_sync = create_journal_analysis_agent(use_async=False)
                logger.info("Sync journal analysis agent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize sync journal analysis agent: {e}")
                raise
        return self._journal_agent_sync
    
    def _get_journal_agent_async(self):
        """Lazy initialization of the async journal analysis agent."""
        if self._journal_agent_async is None:
            try:
                from agents.core.journal_analysis_agent import JournalAnalysisAgent
                self._journal_agent_async = JournalAnalysisAgent(use_async=True)
                logger.info("Async journal analysis agent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize async journal analysis agent: {e}")
                raise
        return self._journal_agent_async
    
    async def analyze_entry_atomic(self, text: str, language: str, user_id: Optional[str] = None, user_level: Optional[str] = "intermediate") -> Dict[str, Any]:
        """
        Analyze a journal entry using Atomic Agents.
        
        This method uses the new JournalAnalysisAgent and converts the output
        to match the expected format of the existing API.
        
        Args:
            text: The journal entry text to analyze
            language: The language of the entry text
            user_id: Optional user ID for personalized context
            user_level: User's proficiency level for appropriate feedback
            
        Returns:
            Dictionary containing feedback in the format expected by existing API
        """
        try:
            # Get the async journal analysis agent
            agent = self._get_journal_agent_async()
            
            # Run the analysis with context
            result = await agent.analyze_async(
                text=text, 
                language=language, 
                user_level=user_level,
                user_id=user_id
            )
            
            # Convert to the format expected by the existing API
            return self._convert_agent_output_to_api_format(result)
            
        except Exception as e:
            logger.error(f"Error in atomic agent analysis: {str(e)}")
            raise
    
    def _convert_agent_output_to_api_format(self, agent_output: JournalAnalysisOutputSchema) -> Dict[str, Any]:
        """
        Convert agent output to the format expected by the existing API.
        
        Args:
            agent_output: The output from the JournalAnalysisAgent
            
        Returns:
            Dictionary in the format expected by the existing feedback API
        """
        return {
            "corrected": agent_output.corrected,
            "rewrite": agent_output.rewritten,
            "score": agent_output.score,
            "tone": agent_output.tone,
            "translation": agent_output.translation,
            "explanation": agent_output.explanation,
            "rubric": {
                "grammar": agent_output.rubric.grammar,
                "vocabulary": agent_output.rubric.vocabulary,
                "complexity": agent_output.rubric.complexity
            },
            "grammar_suggestions": [
                {
                    "id": f"suggestion-{i}",  # Add ID for compatibility
                    "original": sugg.original,
                    "corrected": sugg.corrected,
                    "note": sugg.note
                }
                for i, sugg in enumerate(agent_output.grammar_suggestions)
            ],
            "new_words": [
                {
                    "id": f"word-{i}",  # Add ID for compatibility
                    "term": word.term,
                    "reading": word.reading,
                    "pos": word.pos,
                    "definition": word.definition,
                    "example": word.example,
                    "proficiency": word.proficiency
                }
                for i, word in enumerate(agent_output.new_words)
            ]
        }
    
    async def analyze_entry_with_fallback(self, text: str, language: str, user_id: Optional[str] = None, user_level: Optional[str] = "intermediate") -> Dict[str, Any]:
        """
        Analyze entry with fallback to old system if needed.
        
        This method tries the new Atomic Agents first, and falls back to
        the old system if there are any issues.
        
        Args:
            text: The journal entry text to analyze
            language: The language of the entry text
            
        Returns:
            Dictionary containing feedback
        """
        try:
            # Try the new Atomic Agents system
            logger.info("Attempting analysis with Atomic Agents")
            return await self.analyze_entry_atomic(text, language, user_id, user_level)
            
        except Exception as e:
            logger.warning(f"Atomic Agents failed: {str(e)}, falling back to old system")
            
            # Import and use the old system as fallback
            try:
                from feedback_engine import analyze_with_mock
                logger.info("Using fallback mock system")
                return analyze_with_mock(text, language)
            except Exception as fallback_error:
                logger.error(f"Fallback system also failed: {str(fallback_error)}")
                raise Exception(f"Both new and fallback systems failed: {str(e)} | {str(fallback_error)}")


# Global instance for the service
_agent_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """
    Get the global AgentService instance (singleton pattern).
    
    Returns:
        AgentService instance
    """
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
        logger.info("AgentService singleton created")
    return _agent_service_instance


# Backward compatibility functions that match the old API
async def analyze_entry_atomic_compat(text: str, language: str, user_id: Optional[str] = None, user_level: Optional[str] = "intermediate") -> Dict[str, Any]:
    """
    Backward compatibility function for analyze_entry.
    
    This function maintains the same signature as the old analyze_entry
    function but uses the new Atomic Agents system.
    
    Args:
        text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        Dictionary containing feedback in the expected format
    """
    service = get_agent_service()
    return await service.analyze_entry_with_fallback(text, language, user_id, user_level)


async def generate_feedback_atomic_compat(entry_text: str, language: str) -> Dict[str, Any]:
    """
    Backward compatibility function for generate_feedback.
    
    Args:
        entry_text: The journal entry text to analyze
        language: The language of the entry text
        
    Returns:
        Dictionary containing various feedback dimensions
    """
    analysis = await analyze_entry_atomic_compat(entry_text, language)
    
    # Format the output according to the existing API contract
    return {
        "corrected": analysis.get("corrected", entry_text),
        "rewritten": analysis.get("rewrite", entry_text),
        "score": analysis.get("score", 0),
        "rubric": analysis.get("rubric", {"grammar": 0, "vocabulary": 0, "complexity": 0}),
        "tone": analysis.get("tone", "Neutral"),
        "translation": analysis.get("translation", "Translation not available."),
        "explanation": analysis.get("explanation", "No detailed explanation available."),
        "grammar_suggestions": analysis.get("grammar_suggestions", []),
        "new_words": analysis.get("new_words", [])
    }

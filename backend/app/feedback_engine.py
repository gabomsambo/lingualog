"""Legacy journal feedback adapter retained for old dependency callers."""

import logging

from app.ai_engines.gemini_engine import GeminiEngine
from app.models import AiFeedback

logger = logging.getLogger(__name__)


class FeedbackEngine:
    """Compatibility wrapper for the legacy journal-only Gemini engine."""

    def __init__(self, gemini_engine: GeminiEngine):
        self.gemini_engine = gemini_engine

    async def generate_ai_feedback_for_entry(
        self,
        entry_text: str,
        language: str,
    ) -> AiFeedback:
        logger.info("Generating legacy journal feedback in %s", language)
        raw_feedback = await self.gemini_engine.analyze_journal_entry(
            entry_text=entry_text,
            language=language,
        )
        return AiFeedback(**raw_feedback) if raw_feedback else AiFeedback()

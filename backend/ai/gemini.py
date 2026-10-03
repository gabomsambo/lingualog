"""
Gemini adapter for LinguaLog.

Thin, stateless wrapper around the ``google-genai`` SDK. It exposes one
async structured-output call with timeout, one retry on 429/5xx, and a
single clear log line for each error class.
"""
import asyncio
import logging
import os
from typing import Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_FEEDBACK = os.getenv("GEMINI_MODEL_FEEDBACK", "gemini-3.8-flash")
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

T = TypeVar("T", bound=BaseModel)


class GeminiError(Exception):
    """Raised when the Gemini call fails in a way the caller should surface."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _thinking_config() -> Optional[types.ThinkingConfig]:
    """Build a thinking config when a thinking level is configured."""
    if GEMINI_THINKING_LEVEL:
        return types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL)
    return None


def _error_code_from_status(status: Optional[int]) -> str:
    """Map an HTTP status to a stable error code."""
    if status == 429:
        return "ai_quota_exhausted"
    if status and 500 <= status < 600:
        return "ai_unavailable"
    return "ai_unavailable"


async def generate_structured(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    timeout: float = 30.0,
) -> T:
    """
    Generate structured output from Gemini.

    Args:
        system_prompt: System instruction that encodes the language policy.
        user_prompt: The journal entry text plus any request context.
        schema: Pydantic model describing the desired JSON output.
        timeout: Per-attempt timeout in seconds.

    Returns:
        An instance of ``schema`` populated by the model.

    Raises:
        GeminiError: On configuration, timeout, quota, availability, or schema
            validation failures. The ``code`` attribute is safe to return to
            callers as ``analysis_error_code``.
    """
    if not GEMINI_API_KEY:
        logger.error("Gemini API key missing: GEMINI_API_KEY is not set")
        raise GeminiError("ai_unconfigured", "GEMINI_API_KEY is not set")

    contents = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)])
    ]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=schema,
        thinking_config=_thinking_config(),
    )

    last_error: Optional[GeminiError] = None
    for attempt in range(2):
        client = genai.Client(api_key=GEMINI_API_KEY)
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=GEMINI_MODEL_FEEDBACK,
                    contents=contents,
                    config=config,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            logger.warning("Gemini request timed out after %.1fs", timeout)
            last_error = GeminiError(
                "ai_timeout",
                f"Gemini request timed out after {timeout}s",
            )
            break
        except genai.errors.APIError as exc:
            code = getattr(exc, "code", None)
            status = getattr(exc, "status", None)
            if code in (429, 500, 502, 503, 504) and attempt == 0:
                logger.warning(
                    "Gemini API error (status=%s code=%s), retrying once",
                    status,
                    code,
                )
                await asyncio.sleep(1)
                continue
            error_code = _error_code_from_status(code)
            logger.error(
                "Gemini API error (status=%s code=%s): %s",
                status,
                code,
                exc,
            )
            raise GeminiError(
                error_code,
                f"Gemini API error {code} ({status})",
            ) from exc
        except Exception as exc:
            logger.error(
                "Gemini request failed (%s): %s",
                type(exc).__name__,
                exc,
            )
            raise GeminiError(
                "ai_unavailable",
                f"Gemini request failed: {type(exc).__name__}",
            ) from exc

        try:
            candidate = response.candidates[0]
            text = candidate.content.parts[0].text
            parsed = schema.model_validate_json(text)
            return parsed
        except (AttributeError, IndexError, ValidationError) as exc:
            logger.error(
                "Gemini response did not match schema (%s): %s",
                type(exc).__name__,
                exc,
            )
            raise GeminiError(
                "ai_schema_invalid",
                "Gemini response could not be parsed into the expected schema",
            ) from exc

    if last_error:
        raise last_error
    raise GeminiError("ai_unavailable", "Gemini request failed after retry")


async def mock_generate_structured(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    timeout: float = 30.0,
    entry_text: Optional[str] = None,
) -> T:
    """
    Mock provider for offline development and tests.

    Returns plausible feedback and marks it with ``is_mock=True``. The
    response is never persisted as real feedback unless ``AI_PROVIDER=mock``
    is explicitly set.
    """
    logger.info("Using mock feedback provider (AI_PROVIDER=mock)")
    if entry_text is None:
        entry_text = user_prompt or ""
    entry_text = entry_text.strip()
    return schema(
        corrected=f"[Mock Corrected] {entry_text}",
        rewrite=f"[Mock Rewritten] {entry_text}",
        score=75,
        tone="Neutral",
        explanation="This is sample feedback generated because AI_PROVIDER=mock.",
        rubric={"grammar": 75, "vocabulary": 75, "complexity": 75},
        grammar_suggestions=[
            {
                "original": entry_text.split()[0] if entry_text.split() else entry_text,
                "corrected": f"[Mock suggestion] {entry_text.split()[0] if entry_text.split() else entry_text}",
                "note": "Sample suggestion for development.",
            }
        ],
        new_words=[
            {
                "term": word,
                "pos": "noun",
                "definition": f"Sample definition for '{word}'.",
                "example": f"Example using '{word}'.",
                "proficiency": "intermediate",
            }
            for word in (entry_text.split()[:2] if entry_text.split() else ["sample"])
        ],
        is_mock=True,
    )


__all__ = [
    "generate_structured",
    "mock_generate_structured",
    "GeminiError",
    "GEMINI_MODEL_FEEDBACK",
    "GEMINI_THINKING_LEVEL",
    "AI_PROVIDER",
]

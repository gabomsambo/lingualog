"""
Unit tests for the Gemini adapter.

These tests mock the ``google-genai`` SDK so they never hit the network or
require a real API key.
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from google import genai

from ai.gemini import (
    generate_structured,
    mock_generate_structured,
    GeminiError,
    GEMINI_MODEL_FEEDBACK,
)
from ai.schemas import JournalFeedback


@pytest.fixture
def schema():
    return JournalFeedback


class FakeCandidate:
    def __init__(self, text):
        self.content = MagicMock()
        self.content.parts = [MagicMock(text=text)]


class FakeResponse:
    def __init__(self, text):
        self.candidates = [FakeCandidate(text)]


def _make_client_mock(text):
    """Return a mock genai.Client whose async generate_content returns text."""
    client = MagicMock()
    client.aio.models.generate_content = MagicMock(
        return_value=asyncio.Future()
    )
    client.aio.models.generate_content.return_value.set_result(FakeResponse(text))
    return client


def _valid_feedback_json():
    return (
        '{'
        '"corrected": "Hola, me llamo Juan.",'
        '"rewrite": "Hola, soy Juan.",'
        '"score": 85,'
        '"tone": "Neutral",'
        '"explanation": "Good.",'
        '"rubric": {"grammar": 80, "vocabulary": 85, "complexity": 90},'
        '"grammar_suggestions": [],'
        '"new_words": []'
        ',"sentence_mapping": [{"source_sentence": 0, "corrected_sentences": [0]}]'
        '}'
    )


@pytest.mark.asyncio
async def test_generate_structured_returns_parsed_model(schema):
    json_text = _valid_feedback_json()
    with patch.object(genai, "Client", return_value=_make_client_mock(json_text)):
        result = await generate_structured(
            "system prompt", "user prompt", schema, timeout=5.0
        )

    assert result.corrected == "Hola, me llamo Juan."
    assert result.score == 85
    assert result.is_mock is False


@pytest.mark.asyncio
async def test_generate_structured_retries_on_429(schema):
    """A 429 should trigger one retry; success on the second call returns normally."""
    first = MagicMock()
    first.aio.models.generate_content = MagicMock(return_value=asyncio.Future())
    first.aio.models.generate_content.return_value.set_exception(
        genai.errors.APIError(code=429, response_json={"code": 429, "status": "RESOURCE_EXHAUSTED"})
    )

    second = _make_client_mock(_valid_feedback_json())

    with patch.object(genai, "Client", side_effect=[first, second]):
        result = await generate_structured("sys", "user", schema, timeout=5.0)

    assert result.score == 85
    assert first.aio.models.generate_content.call_count == 1
    assert second.aio.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_quota_exhausted_after_retry(schema):
    """Two 429s in a row should raise ai_quota_exhausted."""
    client = MagicMock()
    client.aio.models.generate_content = MagicMock(return_value=asyncio.Future())
    client.aio.models.generate_content.return_value.set_exception(
        genai.errors.APIError(code=429, response_json={"code": 429, "status": "RESOURCE_EXHAUSTED"})
    )

    with patch.object(genai, "Client", return_value=client):
        with pytest.raises(GeminiError) as exc_info:
            await generate_structured("sys", "user", schema, timeout=5.0)

    assert exc_info.value.code == "ai_quota_exhausted"


@pytest.mark.asyncio
async def test_generate_structured_5xx_after_retry(schema):
    """A 5xx that persists after one retry should raise ai_unavailable."""
    client = MagicMock()
    client.aio.models.generate_content = MagicMock(return_value=asyncio.Future())
    client.aio.models.generate_content.return_value.set_exception(
        genai.errors.APIError(code=503, response_json={"code": 503, "status": "UNAVAILABLE"})
    )

    with patch.object(genai, "Client", return_value=client):
        with pytest.raises(GeminiError) as exc_info:
            await generate_structured("sys", "user", schema, timeout=5.0)

    assert exc_info.value.code == "ai_unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
async def test_generate_structured_client_errors_are_unconfigured(schema, status_code):
    """Bad key, permission, or model-name errors are not transient and are not retried."""
    client = MagicMock()
    client.aio.models.generate_content = MagicMock(return_value=asyncio.Future())
    client.aio.models.generate_content.return_value.set_exception(
        genai.errors.APIError(code=status_code, response_json={"code": status_code, "status": "ERROR"})
    )

    with patch.object(genai, "Client", return_value=client):
        with pytest.raises(GeminiError) as exc_info:
            await generate_structured("sys", "user", schema, timeout=5.0)

    assert exc_info.value.code == "ai_unconfigured"
    assert client.aio.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_timeout(schema):
    """A timeout should raise ai_timeout."""
    client = MagicMock()
    client.aio.models.generate_content = MagicMock(return_value=asyncio.Future())
    # Never resolve the future -> wait_for times out.
    with patch.object(genai, "Client", return_value=client):
        with pytest.raises(GeminiError) as exc_info:
            await generate_structured("sys", "user", schema, timeout=0.01)

    assert exc_info.value.code == "ai_timeout"


@pytest.mark.asyncio
async def test_generate_structured_schema_mismatch(schema):
    """A response that does not match the schema should raise ai_schema_invalid."""
    bad_json = '{"unexpected": "value"}'
    with patch.object(genai, "Client", return_value=_make_client_mock(bad_json)):
        with pytest.raises(GeminiError) as exc_info:
            await generate_structured("sys", "user", schema, timeout=5.0)

    assert exc_info.value.code == "ai_schema_invalid"


@pytest.mark.asyncio
async def test_mock_generate_structured_flags_is_mock(schema):
    result = await mock_generate_structured("sys", "Hello world", schema)

    assert result.is_mock is True
    assert "[Mock Corrected]" in result.corrected
    assert result.score == 75


@pytest.mark.asyncio
async def test_missing_api_key_raises_unconfigured(schema, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    # Reload module-level constant by re-importing is overkill; patch the module attr.
    import ai.gemini as gemini_module
    monkeypatch.setattr(gemini_module, "GEMINI_API_KEY", "")

    with pytest.raises(GeminiError) as exc_info:
        await generate_structured("sys", "user", schema, timeout=5.0)

    assert exc_info.value.code == "ai_unconfigured"


def test_gemini_schema_requires_suggestions_words_and_sentence_mapping():
    """Optional arrays came back empty from the live model; the response schema requires them."""
    from ai.schemas import GeminiJournalFeedback

    required = GeminiJournalFeedback.model_json_schema()["required"]
    assert "grammar_suggestions" in required
    assert "new_words" in required
    assert "sentence_mapping" in required
    assert JournalFeedback(
        corrected="", rewrite="", score=0, tone="", explanation="",
        rubric={"grammar": 0, "vocabulary": 0, "complexity": 0},
    ).grammar_suggestions == []

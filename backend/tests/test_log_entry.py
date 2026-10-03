"""
Tests for the real-Gemini /log-entry path.

All AI provider calls are mocked so these tests run without a real API key.
They verify that:
- the language policy actually reaches the prompt,
- the journal feedback path is stateless (no cross-user text leaks),
- failures are honest (no mock fallback, entry kept, error code stored),
- mock feedback is flagged when AI_PROVIDER=mock.
"""
import asyncio
from unittest.mock import patch, AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from lang_policy import resolve_effective
from prompt_builder import build_messages, build_user_message
from server import app, AI_PROVIDER
from ai.schemas import JournalFeedback


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def sample_feedback(text="", is_mock=False):
    return JournalFeedback(
        corrected=f"Corrected {text}",
        rewrite=f"Rewrite {text}",
        score=80,
        tone="Neutral",
        explanation="Sample explanation.",
        rubric={"grammar": 80, "vocabulary": 80, "complexity": 80},
        grammar_suggestions=[],
        new_words=[],
        is_mock=is_mock,
    )


def test_policy_prompt_respects_immersion_levels():
    """The system prompt must switch explanation language across immersion 0-3."""
    base_profile = {
        "native_lang": "en",
        "default_target_lang": "es",
        "interface_lang": "en",
        "strictness": "medium",
        "formality": "neutral",
    }
    expectations = {
        0: "English only",
        1: "English only",
        2: "both English and Spanish",
        3: "Spanish only",
    }

    for level, expected_phrase in expectations.items():
        profile = {**base_profile, "immersion_level": level}
        effective = resolve_effective(profile)
        system_prompt, user_payload = build_messages(
            "El sábado yo fui a la playa.", effective
        )

        assert expected_phrase in system_prompt, (
            f"Level {level} should mention '{expected_phrase}'"
        )
        assert '"translation"' not in system_prompt, (
            f"Level {level} prompt must not ask for a translation field"
        )
        assert user_payload["proficiency_estimate"] in {
            "beginner",
            "elementary",
            "intermediate",
            "advanced",
        }


def test_user_message_does_not_ask_for_translation():
    effective = resolve_effective(
        {
            "native_lang": "en",
            "default_target_lang": "es",
            "immersion_level": 2,
        }
    )
    message = build_user_message("Hola mundo", effective)
    assert "translation" not in message.lower()
    assert "Translation needed" not in message


def test_log_entry_saves_real_feedback(client):
    from ai.gemini import GeminiError

    returned_feedback = sample_feedback("Hola")

    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)):
        with patch("server.save_entry", return_value={"id": "entry-123"}) as mock_save:
            with patch("server.generate_structured", new=AsyncMock(return_value=returned_feedback)):
                response = client.post(
                    "/log-entry",
                    json={"text": "Hola me llamo Juan"},
                    headers={"X-User-ID": "user-1"},
                )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "entry-123"
    assert body["corrected"] == "Corrected Hola"
    assert body["is_mock"] is False

    mock_save.assert_called_once()
    saved = mock_save.call_args[0][0]
    assert saved["original_text"] == "Hola me llamo Juan"
    assert saved["analysis_status"] == "ok"
    assert saved["analysis_model"] == "gemini-3.8-flash"
    assert saved["analysis_error_code"] is None


def test_log_entry_honest_failure_keeps_entry(client):
    from ai.gemini import GeminiError

    error = GeminiError("ai_timeout", "Timed out")

    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)):
        with patch("server.save_entry", return_value={"id": "failed-entry-123"}) as mock_save:
            with patch("server.generate_structured", new=AsyncMock(side_effect=error)):
                response = client.post(
                    "/log-entry",
                    json={"text": "Hola me llamo Juan"},
                    headers={"X-User-ID": "user-1"},
                )

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["code"] == "ai_timeout"
    assert body["detail"]["entry_id"] == "failed-entry-123"

    saved = mock_save.call_args[0][0]
    assert saved["original_text"] == "Hola me llamo Juan"
    assert saved["analysis_status"] == "failed"
    assert saved["analysis_error_code"] == "ai_timeout"
    assert saved.get("corrected") is None


def test_log_entry_db_failure_returns_500(client):
    returned_feedback = sample_feedback("Hola")

    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)):
        with patch("server.save_entry", side_effect=Exception("database down")):
            with patch("server.generate_structured", new=AsyncMock(return_value=returned_feedback)):
                response = client.post(
                    "/log-entry",
                    json={"text": "Hola me llamo Juan"},
                    headers={"X-User-ID": "user-1"},
                )

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_log_entry_no_cross_user_text_leak(async_client):
    """Concurrent requests from two users must not share entry text in prompts."""
    prompts = []

    async def fake_profile_settings(user_id):
        return {
            "native_lang": "en" if user_id == "user-a" else "ja",
            "default_target_lang": "es" if user_id == "user-a" else "en",
            "interface_lang": "en" if user_id == "user-a" else "ja",
            "explanation_mode": "bilingual",
            "immersion_level": 2,
            "strictness": "medium",
            "formality": "neutral",
        }

    async def fake_generate(system_prompt, user_prompt, schema, timeout=30.0):
        prompts.append((system_prompt, user_prompt))
        return sample_feedback("")

    with patch("server.fetch_user_profile_settings", new=fake_profile_settings):
        with patch("server.save_entry", return_value={"id": "id"}):
            with patch("server.generate_structured", new=fake_generate):
                responses = await asyncio.gather(
                    async_client.post(
                        "/log-entry",
                        json={"text": "Text from user A"},
                        headers={"X-User-ID": "user-a"},
                    ),
                    async_client.post(
                        "/log-entry",
                        json={"text": "Text from user B"},
                        headers={"X-User-ID": "user-b"},
                    ),
                )

    assert all(r.status_code == 201 for r in responses)
    assert len(prompts) == 2

    system_a, user_a = prompts[0]
    system_b, user_b = prompts[1]

    assert "Text from user A" in user_a
    assert "Text from user B" not in user_a
    assert "Text from user B" in user_b
    assert "Text from user A" not in user_b
    # The shared system prompt must not contain either user's text either.
    assert "Text from user A" not in system_a
    assert "Text from user B" not in system_a


@pytest.mark.asyncio
async def test_retry_analysis_endpoint(async_client):
    """POST /entries/{id}/analyze retries analysis and updates the row."""
    returned_feedback = sample_feedback("retry")

    with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)):
        with patch(
            "server.fetch_single_entry",
            return_value={
                "id": "entry-1",
                "content": "Hola mundo",
                "target_language": "es",
                "language": "es",
            },
        ):
            with patch(
                "server.update_entry_analysis",
                return_value={"id": "entry-1"},
            ) as mock_update:
                with patch(
                    "server.generate_structured",
                    new=AsyncMock(return_value=returned_feedback),
                ):
                    response = await async_client.post(
                        "/entries/entry-1/analyze",
                        headers={"X-User-ID": "user-1"},
                    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "entry-1"
    assert body["corrected"] == "Corrected retry"
    assert body["is_mock"] is False

    update_call = mock_update.call_args[0][2]
    assert update_call["analysis_status"] == "ok"
    assert update_call["analysis_model"] == "gemini-3.8-flash"
    assert update_call["analysis_error_code"] is None


def test_log_entry_mock_provider_flags_response(client):
    """When AI_PROVIDER=mock the response is flagged and the model is 'mock'."""
    with patch("server.AI_PROVIDER", "mock"):
        with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)):
            with patch("server.save_entry", return_value={"id": "mock-entry-1"}) as mock_save:
                response = client.post(
                    "/log-entry",
                    json={"text": "Hola"},
                    headers={"X-User-ID": "user-1"},
                )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "mock-entry-1"
    assert body["is_mock"] is True

    saved = mock_save.call_args[0][0]
    assert saved["analysis_status"] == "ok"
    assert saved["analysis_model"] == "mock"

"""Tests for Lara translation adapter and entry translate API."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai.lara import LARA_PRIVACY_KWARGS, LaraUnavailableError, translate_texts
from app.services.entry_translation_service import split_sentences


@pytest.mark.asyncio
async def test_lara_translate_passes_privacy_flags():
    mock_result = MagicMock()
    mock_result.translation = ["Hello world."]

    mock_translator = MagicMock()
    mock_translator.translate.return_value = mock_result

    with patch("ai.lara._build_translator", return_value=mock_translator):
        with patch.dict("os.environ", {"LARA_TRANSLATE_ID": "id", "LARA_TRANSLATE_SECRET": "secret"}):
            out = await translate_texts(["Hola mundo."], source_lang="es", target_lang="en")

    assert out == ["Hello world."]
    mock_translator.translate.assert_called_once()
    _, kwargs = mock_translator.translate.call_args
    assert kwargs["no_trace"] is True
    assert kwargs["adapt_to"] == []
    assert kwargs["target"] == "en-US"


def test_lara_privacy_kwargs_frozen():
    assert LARA_PRIVACY_KWARGS["no_trace"] is True
    assert LARA_PRIVACY_KWARGS["adapt_to"] == []


def test_split_sentences():
    text = "Primera oración. Segunda oración!"
    parts = split_sentences(text)
    assert len(parts) == 2


@pytest.mark.asyncio
async def test_gemini_fallback_when_lara_missing():
    from app.services import entry_translation_service as svc

    entry = {
        "content": "Hola.",
        "language": "es",
        "meaning_translations_cache": {},
        "ai_feedback": {},
    }

    with patch("app.services.entry_translation_service.fetch_single_entry", return_value=entry):
        with patch(
            "app.services.entry_translation_service.translate_texts",
            side_effect=LaraUnavailableError("no creds"),
        ):
            with patch(
                "app.services.entry_translation_service.translate_sentences_gemini",
                return_value=["Hi."],
            ):
                with patch("app.services.entry_translation_service.create_supabase_client") as mock_sb:
                    mock_sb.return_value.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
                    result = await svc.translate_entry_part(
                        "entry-1", "user-1", "original", "en"
                    )

    assert result["provider"] == "gemini"
    assert result["status"] == "ok"
    assert "Gemini" in (result.get("provider_label") or "")


@pytest.mark.asyncio
async def test_cache_hit_skips_providers():
    from app.services import entry_translation_service as svc

    cache = {
        "original:en": {
            "sentences": ["Cached."],
            "text": "Cached.",
            "provider": "lara",
            "status": "ok",
            "provider_label": "Translated by Lara",
        }
    }
    entry = {
        "content": "Hola.",
        "language": "es",
        "meaning_translations_cache": cache,
        "ai_feedback": {},
    }

    with patch("app.services.entry_translation_service.fetch_single_entry", return_value=entry):
        with patch("app.services.entry_translation_service.translate_texts") as mock_lara:
            result = await svc.translate_entry_part("e1", "u1", "original", "en")
            mock_lara.assert_not_called()

    assert result["cached"] is True
    assert result["text"] == "Cached."


@pytest.fixture
def client():
    from server import app

    return TestClient(app)


@patch("app.routers.entry_translation.translate_entry_part")
def test_translate_endpoint_owner_only(mock_translate, client):
    mock_translate.side_effect = PermissionError()

    response = client.post(
        "/entries/bad-id/translate",
        json={"part": "original", "target_lang": "en"},
        headers={"X-User-ID": "user-1"},
    )
    assert response.status_code == 404


@patch("app.routers.support_events.create_supabase_client")
def test_support_event_recorded(mock_sb, client):
    mock_sb.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "evt-1"}]
    )

    response = client.post(
        "/events",
        json={
            "kind": "reveal_meaning",
            "entry_id": "entry-1",
            "immersion_level": 1,
            "l2": "es",
        },
        headers={"X-User-ID": "user-1"},
    )
    assert response.status_code == 201
    mock_sb.return_value.table.assert_called_with("support_events")

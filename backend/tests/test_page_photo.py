"""The page-photo vision call: image parts, medium resolution, and the prompt contract."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from google import genai
from google.genai import types

from ai.gemini import generate_structured
from ai.page_photo import PageTranscription, build_page_photo_prompts, read_page_photo

PAGE_JSON = '{"readable": true, "transcription": "Hola.", "candidates": [{"surface": "atadas", "lemma": "atar"}]}'


def _client(text):
    client = MagicMock()
    client.aio.models.generate_content = MagicMock(return_value=asyncio.Future())
    response = MagicMock()
    response.candidates = [MagicMock()]
    response.candidates[0].content.parts = [MagicMock(text=text)]
    client.aio.models.generate_content.return_value.set_result(response)
    return client


@pytest.mark.asyncio
async def test_images_travel_as_inline_parts_at_medium_resolution():
    client = _client(PAGE_JSON)
    with patch.object(genai, "Client", return_value=client):
        result = await generate_structured(
            "sys", "read this", PageTranscription, images=[(b"\xff\xd8\xff-bytes", "image/jpeg")]
        )

    call = client.aio.models.generate_content.call_args.kwargs
    parts = call["contents"][0].parts
    assert parts[0].text == "read this"
    assert parts[1].inline_data.data == b"\xff\xd8\xff-bytes" and parts[1].inline_data.mime_type == "image/jpeg"
    assert call["config"].media_resolution == types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
    assert result.candidates[0].lemma == "atar"


@pytest.mark.asyncio
async def test_text_only_calls_keep_the_default_resolution():
    client = _client(PAGE_JSON)
    with patch.object(genai, "Client", return_value=client):
        await generate_structured("sys", "user", PageTranscription)

    call = client.aio.models.generate_content.call_args.kwargs
    assert len(call["contents"][0].parts) == 1
    assert call["config"].media_resolution is None


def test_the_prompt_names_the_language_and_the_learners_level_and_skips_proper_nouns():
    system_prompt, user_prompt = build_page_photo_prompts("es", "B1")

    assert "B1" in system_prompt and "proper nouns" in system_prompt and "readable to false" in system_prompt
    assert "Spanish" in user_prompt


@pytest.mark.asyncio
async def test_read_page_photo_uses_flash_lite_without_thinking(monkeypatch):
    provider = MagicMock(side_effect=lambda *args, **kwargs: asyncio.sleep(0, PageTranscription(
        readable=True, transcription="Hola.", candidates=[])))
    monkeypatch.setattr("ai.page_photo.generate_structured", provider)

    await read_page_photo(b"img", "image/png", "es", "A2")

    kwargs = provider.call_args.kwargs
    assert kwargs["model"] == "gemini-3.5-flash-lite" and kwargs["use_thinking"] is False
    assert kwargs["images"] == [(b"img", "image/png")]

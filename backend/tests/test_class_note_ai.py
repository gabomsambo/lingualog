"""One-call extraction and tolerant normalization for class notes."""

from unittest.mock import AsyncMock

import pytest

from ai import class_note


@pytest.mark.asyncio
async def test_class_note_extraction_uses_flash_lite_once_with_cefr_context(monkeypatch):
    provider = AsyncMock(return_value=class_note.ClassNoteExtraction(
        words=[{"term": "la casa", "gloss": "the house"}],
        grammar_focus="estar + gerundio",
        phrases=["Estoy estudiando"],
        tasks=[{"title": f"Task {index}", "prompt": f"Write task {index}"} for index in range(3)],
    ))
    monkeypatch.setattr(class_note, "generate_structured", provider)

    result = await class_note.extract_class_note("la casa\nestar + gerundio", "es", "A1")

    provider.assert_awaited_once()
    args = provider.await_args.args
    kwargs = provider.await_args.kwargs
    assert kwargs["model"] == "gemini-3.5-flash-lite"
    assert kwargs["use_thinking"] is False
    assert "25–50 words" in args[1]
    assert "present tense" in args[1]
    assert result["grammar_focus"] == "estar + gerundio"
    assert len(result["tasks"]) == 3
    assert all(task["length_hint"] == "25–50 words" for task in result["tasks"])


def test_normalizer_accepts_missing_optional_fields_and_keeps_three_tasks():
    result = class_note.normalize_class_note_extraction(
        {"words": [{"word": "casa", "meaning": "house"}]}, "es", "A2"
    )

    assert result["words"][0]["term"] == "casa"
    assert result["words"][0]["gloss"] == "house"
    assert result["grammar_focus"] is None
    assert result["phrases"] == []
    assert len(result["tasks"]) == 3
    assert all(task["length_hint"] == "60–100 words" for task in result["tasks"])


def test_normalizer_deduplicates_and_caps_a_twenty_word_list():
    raw = {"words": [{"term": f"palabra-{index}", "gloss": "word"} for index in range(20)]}

    result = class_note.normalize_class_note_extraction(raw, "es", "B1")

    assert len(result["words"]) == 20
    assert result["words"][-1]["term"] == "palabra-19"


def test_class_note_text_limit_is_checked_before_the_model_call(monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr(class_note, "generate_structured", provider)

    with pytest.raises(ValueError, match="characters or fewer"):
        import asyncio
        asyncio.run(class_note.extract_class_note("x" * (class_note.MAX_CLASS_NOTE_CHARS + 1), "es", "A1"))

    provider.assert_not_awaited()

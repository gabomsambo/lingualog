"""Vocabulary card prompts use the resolved policy and a mocked provider."""

from unittest.mock import AsyncMock

import pytest

from ai.word_card import WordCard, generate_word_card
from learning_policy import resolve_policy


CARD = {
    "lemma": "banco",
    "surface": "banco",
    "is_phrase": False,
    "part_of_speech": "noun",
    "gender": "m",
    "sense_in_context": "A bench in a public park.",
    "gloss_l1": "park bench",
    "other_senses": [
        {"meaning": "A financial institution.", "example": "Voy al banco."},
    ],
    "register": "neutral",
    "cefr": "A1",
    "frequency_band": "top1k",
    "examples": ["Me senté en el banco.", "El banco es de madera."],
    "example_translations": ["I sat on the bench.", "The bench is made of wood."],
    "collocations": ["banco del parque", "banco de madera", "sentarse en un banco"],
    "word_family": ["banquito"],
    "common_mistake": "Use the context to distinguish bench from bank.",
    "memory_hook": "Picture a park bench.",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "vocab_def", "expected", "forbidden"),
    [
        (0, "l1", "simple English", "learner's-dictionary Spanish"),
        (1, "l1_plus_l2", "retaining the Spanish term", "empty string"),
        (2, "l2_plus_l1", "short English gloss for an optional reveal", "no English"),
        (3, "l2", "no English", "short English gloss"),
    ],
)
async def test_card_prompt_and_output_follow_policy(
    monkeypatch,
    level,
    vocab_def,
    expected,
    forbidden,
):
    policy = resolve_policy(
        None,
        "es",
        {"immersion_level": level},
        settings={"native_lang": "en"},
        language_profile={"immersion_level": level, "proficiency": "B1"},
    )
    provider = AsyncMock(return_value=WordCard.model_validate(CARD))
    monkeypatch.setattr("ai.word_card.generate_structured", provider)

    result = await generate_word_card(
        "banco",
        "Me senté en un banco del parque.",
        policy,
    )

    system_prompt, user_prompt, schema = provider.await_args.args[:3]
    assert policy.vocab_def == vocab_def
    assert expected in system_prompt
    assert forbidden not in system_prompt
    assert "The learner's proficiency is B1" in system_prompt
    assert "Target language: Spanish" in user_prompt
    assert "Me senté en un banco del parque." in user_prompt
    assert schema is WordCard
    assert provider.await_args.kwargs["model"] == "gemini-3.5-flash-lite"
    assert provider.await_args.kwargs["use_thinking"] is False
    assert result.lemma == "banco"
    assert result.other_senses[0].example == "Voy al banco."


def test_word_card_schema_requires_ui_arrays():
    required = WordCard.model_json_schema()["required"]
    assert {"other_senses", "examples", "example_translations", "collocations", "word_family"} <= set(required)

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
    definition_language = "English" if level < 2 else "Spanish"

    async def mocked_model_output(_system_prompt, _user_prompt, schema, **_kwargs):
        output = dict(CARD)
        output["other_senses"] = [dict(CARD["other_senses"][0])]
        if definition_language == "Spanish":
            output.update(
                sense_in_context="Asiento de un parque público.",
                other_senses=[{"meaning": "Una entidad financiera.", "example": "Voy al banco."}],
                common_mistake="No confundas un asiento con una entidad financiera.",
                memory_hook="Imagina un banco en el parque.",
            )
        if level == 3:
            output["gloss_l1"] = ""
            output["example_translations"] = []
        return schema.model_validate(output)

    monkeypatch.setenv("AI_PROVIDER", "mock")
    provider = AsyncMock(side_effect=mocked_model_output)
    monkeypatch.setattr("ai.word_card.generate_structured", provider)

    result = await generate_word_card(
        "banco",
        "Me senté en un banco del parque.",
        policy,
    )

    system_prompt, user_prompt, schema = provider.await_args.args[:3]
    assert policy.vocab_def == vocab_def
    assert definition_language in system_prompt
    assert expected in system_prompt
    assert forbidden not in system_prompt
    assert "The learner's proficiency is B1" in system_prompt
    assert "Target language: Spanish" in user_prompt
    assert "Me senté en un banco del parque." in user_prompt
    assert issubclass(schema, WordCard)
    schema_json = schema.model_json_schema()
    assert f"written in {definition_language}" in schema_json["properties"]["sense_in_context"]["description"]
    other_senses_schema = next(
        value for name, value in schema_json["$defs"].items() if name.startswith("OtherSense_")
    )
    assert f"written in {definition_language}" in other_senses_schema["properties"]["meaning"]["description"]
    assert provider.await_args.kwargs["model"] == "gemini-3.5-flash-lite"
    assert provider.await_args.kwargs["use_thinking"] is False
    assert result.lemma == "banco"
    assert result.other_senses[0].example == "Voy al banco."
    assert result.sense_in_context == (
        "A bench in a public park." if definition_language == "English" else "Asiento de un parque público."
    )


def test_word_card_schema_requires_ui_arrays():
    required = WordCard.model_json_schema()["required"]
    assert {"other_senses", "examples", "example_translations", "collocations", "word_family"} <= set(required)

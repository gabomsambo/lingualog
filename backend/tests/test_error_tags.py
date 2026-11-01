"""Closed grammar error tags and the single-call prompt contract."""

import pytest
from pydantic import ValidationError

from ai.error_tags import ERROR_TYPES_BY_FAMILY, error_types_for_language
from ai.gemini import mock_generate_structured
from ai.schemas import GeminiJournalFeedback, GrammarSuggestion
from lang_policy import resolve_effective
from models import Suggestion
from prompt_builder import build_messages


def test_error_type_is_required_and_closed():
    with pytest.raises(ValidationError):
        GrammarSuggestion(original="casa", corrected="la casa")

    suggestion = GrammarSuggestion(
        original="La casa es pequeño.",
        corrected="La casa es pequeña.",
        error_type="gender_agreement",
    )
    assert suggestion.error_type == "gender_agreement"
    with pytest.raises(ValidationError):
        GrammarSuggestion(original="x", corrected="y", error_type="anything")

    suggestion_schema = GeminiJournalFeedback.model_json_schema()["$defs"]["GrammarSuggestion"]
    assert "error_type" in suggestion_schema["required"]
    assert set(suggestion_schema["properties"]["error_type"]["enum"]) >= {
        "ser_estar", "gustar", "por_para", "other",
    }


def test_language_families_have_closed_tag_lists_and_spanish_has_its_core_tags():
    assert len(ERROR_TYPES_BY_FAMILY) >= 6
    assert error_types_for_language("es-MX") == ERROR_TYPES_BY_FAMILY["spanish"]
    assert {
        "gender_agreement", "number_agreement", "ser_estar", "gustar", "verb_conjugation",
        "tense_choice", "article", "preposition", "por_para", "word_order", "accent_spelling",
        "vocabulary_choice", "other",
    } == set(error_types_for_language("es"))
    assert "ser_estar" not in error_types_for_language("fr")


def test_api_suggestion_keeps_new_tags_and_accepts_legacy_feedback_without_them():
    tagged = Suggestion(
        original="Estoy estudiante.",
        corrected="Soy estudiante.",
        note="Use ser for identity.",
        error_type="ser_estar",
    )
    legacy = Suggestion(original="Tengo frío.", corrected="Tengo frío.", note="")

    assert tagged.model_dump()["error_type"] == "ser_estar"
    assert legacy.model_dump()["error_type"] is None


def test_production_prompt_lists_only_the_target_familys_allowed_tags():
    effective = resolve_effective(
        {"native_lang": "en", "default_target_lang": "es", "interface_lang": "en"},
        {"target_language": "es"},
    )
    system_prompt, _ = build_messages("Ayer voy al cine.", effective)

    assert "For each grammar suggestion choose one English error_type" in system_prompt
    assert "ser_estar" in system_prompt
    assert "gustar" in system_prompt


@pytest.mark.asyncio
async def test_mock_feedback_emits_a_required_error_type():
    feedback = await mock_generate_structured(
        "prompt",
        "Tengo un perro.",
        GeminiJournalFeedback,
        entry_text="Tengo un perro.",
    )

    assert feedback.grammar_suggestions[0].error_type == "other"

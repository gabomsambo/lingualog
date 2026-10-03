"""Resolver, override precedence, snapshot round-trip, and per-level prompt rules."""

from learning_policy import (
    LEVELS,
    MINIMAL_CORRECTION_RULE,
    LearningPolicy,
    resolve_policy,
)
from prompt_builder import build_messages
from database import shape_entry_for_api
from app.models import JournalEntry
import uuid
from datetime import datetime, timezone


def _settings(l2="es", immersion=1, explanation_mode=None, native="en"):
    settings = {
        "native_lang": native,
        "default_target_lang": l2,
        "interface_lang": "en",
        "strictness": "medium",
        "formality": "neutral",
        "immersion_level": immersion,
    }
    if explanation_mode is not None:
        settings["explanation_mode"] = explanation_mode
    return settings


def _resolve(l2="es", immersion=1, overrides=None, explanation_mode=None, profile=None, proficiency=None, native="en"):
    settings = _settings(l2, immersion, explanation_mode, native=native)
    language_profile = {"l2": l2, "immersion_level": immersion, "proficiency": proficiency or "B1"}
    if profile is not None:
        language_profile = profile
    return resolve_policy(
        "user-1",
        l2,
        overrides,
        settings=settings,
        language_profile=language_profile,
    )


class TestLevelMapping:
    def test_each_level_sets_the_flags(self):
        expected = {
            0: ("l1", "open", "l1_open", "l1", "recognition_l1", "L2_to_L1", "native_only"),
            1: ("l1_with_l2_terms", "tap", "l1_tap", "l1_plus_l2", "recognition_and_recall", "on_demand", "smart"),
            2: ("l2_then_l1", "tap_hidden", "l2_tooltips", "l2_plus_l1", "cloze_l1_hint", "on_demand", "bilingual"),
            3: ("l2", "rescue_only", "l2_tooltips", "l2", "l2_only", "omit", "target_only"),
        }
        for level, flags in expected.items():
            policy = _resolve(immersion=level, explanation_mode="level")
            assert policy.v == 1
            assert policy.immersion_level == level
            assert (
                policy.explanation,
                policy.meaning,
                policy.rewrite_gloss,
                policy.vocab_def,
                policy.quiz,
                policy.translation_policy,
                policy.explanation_mode,
            ) == flags
            assert policy.explanation_source == "immersion_level"

    def test_same_user_different_languages(self):
        spanish = resolve_policy(
            "user-1",
            "es",
            None,
            settings=_settings("es", 3, "level"),
            language_profile={"l2": "es", "immersion_level": 3, "proficiency": "C1"},
        )
        japanese = resolve_policy(
            "user-1",
            "ja",
            None,
            settings=_settings("es", 3, "level"),
            language_profile={"l2": "ja", "immersion_level": 0, "proficiency": "A1"},
        )
        assert spanish.l2 == "es"
        assert spanish.immersion_level == 3
        assert spanish.proficiency == "C1"
        assert spanish.explanation == "l2"
        assert japanese.l2 == "ja"
        assert japanese.immersion_level == 0
        assert japanese.proficiency == "A1"
        assert japanese.explanation == "l1"
        assert japanese.meaning == "open"

    def test_proficiency_does_not_follow_immersion(self):
        beginner_immersive = _resolve(immersion=3, explanation_mode="level", proficiency="A1")
        advanced_native_first = _resolve(immersion=0, explanation_mode="level", proficiency="C2")
        assert beginner_immersive.proficiency == "A1"
        assert beginner_immersive.explanation == "l2"
        assert advanced_native_first.proficiency == "C2"
        assert advanced_native_first.explanation == "l1"

    def test_profile_beats_account_wide_immersion(self):
        policy = resolve_policy(
            "user-1",
            "es",
            None,
            settings=_settings("es", immersion=1, explanation_mode="level"),
            language_profile={"l2": "es", "immersion_level": 3, "proficiency": "B2"},
        )
        assert policy.immersion_level == 3
        assert policy.immersion_source == "language_profile"
        assert policy.proficiency == "B2"


class TestOverridePrecedence:
    def test_saved_explanation_mode_overrides_the_level(self):
        policy = _resolve(immersion=0, explanation_mode="target_only")
        assert policy.immersion_level == 0
        assert policy.meaning == "open"
        assert policy.explanation == "l2"
        assert policy.explanation_mode == "target_only"
        assert policy.explanation_source == "saved_explanation_mode"

    def test_follow_level_is_not_an_explanation_override(self):
        policy = _resolve(immersion=0, explanation_mode="level")
        assert policy.explanation == "l1"
        assert policy.explanation_source == "immersion_level"

    def test_per_entry_immersion_beats_saved_explanation_mode(self):
        policy = _resolve(
            immersion=2,
            explanation_mode="bilingual",
            overrides={"immersion_level": 0},
        )
        assert policy.immersion_level == 0
        assert policy.immersion_source == "request"
        assert policy.explanation == "l1"
        assert policy.explanation_source == "request_immersion_level"
        assert policy.meaning == "open"

    def test_per_entry_explanation_mode_beats_the_slider(self):
        policy = _resolve(
            immersion=0,
            explanation_mode="native_only",
            overrides={"immersion_level": 3, "explanation_mode": "bilingual"},
        )
        assert policy.immersion_level == 3
        assert policy.meaning == "rescue_only"
        assert policy.quiz == "l2_only"
        assert policy.explanation == "l2_then_l1"
        assert policy.explanation_mode == "bilingual"
        assert policy.explanation_source == "request_explanation_mode"

    def test_missing_explanation_mode_lets_the_level_decide(self):
        policy = resolve_policy(
            None,
            "fr",
            None,
            settings={
                "native_lang": "en",
                "default_target_lang": "fr",
                "immersion_level": 3,
            },
            language_profile=None,
        )
        assert policy.explanation_mode == "target_only"
        assert policy.explanation_source == "immersion_level"
        assert policy.proficiency == "A2"
        assert policy.immersion_source == "user_settings"


class TestSnapshotRoundTrip:
    def test_dict_round_trip_keeps_version_and_flags(self):
        policy = _resolve(l2="ja", immersion=2, explanation_mode="level", proficiency="A2")
        restored = LearningPolicy.from_dict(policy.to_dict())
        assert restored == policy
        assert restored.to_dict()["v"] == 1
        assert restored.l2 == "ja"
        assert restored.quiz == LEVELS[2]["quiz"]

    def test_entry_api_shape_exposes_snapshot_and_rewrite(self):
        policy = _resolve(immersion=1, explanation_mode="level")
        now = datetime.now(timezone.utc).isoformat()
        entry_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        shaped = shape_entry_for_api(
            {
                "id": entry_id,
                "user_id": user_id,
                "title": "Playa",
                "language": "es",
                "original_text": "El agua estaba muy frío.",
                "corrected": "El agua estaba muy fría.",
                "rewrite": "El agua estaba helada.",
                "score": 70,
                "tone": "Neutral",
                "translation": "",
                "explanation": "Agreement.",
                "rubric": {"grammar": 70, "vocabulary": 70, "complexity": 70},
                "grammar_suggestions": [],
                "new_words": [],
                "analysis_status": "ok",
                "policy_snapshot": policy.to_dict(),
                "created_at": now,
                "updated_at": now,
            }
        )
        model = JournalEntry(**shaped)
        dumped = model.model_dump(mode="json", by_alias=True)
        assert dumped["policy_snapshot"]["v"] == 1
        assert dumped["policy_snapshot"]["explanation"] == "l1_with_l2_terms"
        assert dumped["corrected"] == "El agua estaba muy fría."
        assert dumped["rewrite"] == "El agua estaba helada."
        assert dumped["rewritten"] == "El agua estaba helada."
        assert dumped["analysis_status"] == "ok"
        assert dumped["ai_feedback"]["corrected"] == dumped["corrected"]


class TestPromptRules:
    def test_each_level_states_its_note_language_and_the_correction_rule(self):
        phrases = {
            0: ("in English only", "leave `note_l2` empty"),
            1: ("name each grammar point", "Leave `note_l2` empty"),
            2: ("one-line English gloss", "`note_l2`"),
            3: ("in Spanish only", "leave `note_l1` empty"),
        }
        for level, (first, second) in phrases.items():
            policy = _resolve(immersion=level, explanation_mode="level", proficiency="B1")
            system_prompt, _payload = build_messages("Hola", policy)
            assert first in system_prompt
            assert second in system_prompt
            assert MINIMAL_CORRECTION_RULE in system_prompt
            assert "grammatical gender" in system_prompt
            assert "No translation of the entry is provided" in system_prompt
            assert "B1" in system_prompt
            assert "Lara" not in system_prompt

    def test_japanese_level_three_stays_in_japanese(self):
        policy = _resolve(l2="ja", immersion=3, explanation_mode="level", native="en")
        system_prompt, _payload = build_messages("昨日、映画を見ました。", policy)
        assert "in Japanese only" in system_prompt
        assert "Never use English" in system_prompt

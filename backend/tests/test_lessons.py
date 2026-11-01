"""Recurring lesson offers and sentence clozes stay deterministic and model-free."""

from datetime import datetime, timedelta, timezone

from app.services import lesson_service
from tests.fake_supabase import FakeSupabase

USER = "user-lesson-test"
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def entry(
    entry_id, created_at, tag="ser_estar", original="Soy profesor.", corrected="Soy profesor."
):
    original_phrase = "es profesor" if tag == "ser_estar" and original.startswith("Estoy") else "profesor"
    corrected_phrase = "está cansado" if tag == "ser_estar" and corrected.startswith("Está") else "profesor"
    return {
        "id": entry_id,
        "user_id": USER,
        "target_language": "es",
        "analysis_status": "ok",
        "created_at": created_at.isoformat(),
        "original_text": original,
        "corrected": corrected,
        "sentence_mapping": [{"source_sentence": 0, "corrected_sentences": [0]}],
        "sentence_mapping_status": "valid",
        "grammar_suggestions": [{
            "original": original_phrase,
            "corrected": corrected_phrase,
            "error_type": tag,
        }],
    }


def store_with(*entries):
    store = FakeSupabase()
    store.tables["journal_entries"] = list(entries)
    return store


def test_offer_waits_for_tag_in_two_distinct_recent_entries():
    old = entry("old", NOW - timedelta(days=2))
    current = entry("current", NOW)
    current["grammar_suggestions"].append(dict(current["grammar_suggestions"][0]))
    store = store_with(current)

    assert lesson_service.offer_for_entry(store, USER, "current", NOW) is None

    store.tables["journal_entries"].append(old)
    offer = lesson_service.offer_for_entry(store, USER, "current", NOW)

    assert offer["tag"] == "ser_estar"
    assert offer["count"] == 2
    assert offer["lesson"]["id"] == "ser-estar-identity"
    assert len(store.rows("lesson_offers")) == 1


def test_offer_excludes_lexical_tags_other_languages_and_mock_feedback():
    current = entry("current", NOW)
    current["grammar_suggestions"] = [
        {"original": "casa", "corrected": "hogar", "error_type": "vocabulary_choice"},
        {"original": "x", "corrected": "y", "error_type": "other"},
    ]
    previous = entry("previous", NOW - timedelta(days=1))
    previous["grammar_suggestions"] = list(current["grammar_suggestions"])
    store = store_with(previous, current)
    assert lesson_service.offer_for_entry(store, USER, "current", NOW) is None

    french = entry("fr", NOW)
    french["target_language"] = "fr"
    assert lesson_service.offer_for_entry(store_with(french), USER, "fr", NOW) is None

    mocked = entry("mock", NOW)
    mocked["analysis_status"] = "mock"
    assert lesson_service.offer_for_entry(store_with(mocked), USER, "mock", NOW) is None


def test_offer_counts_only_the_latest_five_entries():
    rows = [entry("old", NOW - timedelta(days=20), tag="gustar")]
    rows += [entry(f"new-{index}", NOW - timedelta(days=6 - index)) for index in range(1, 6)]
    current = entry("current", NOW, tag="gustar")
    rows.append(current)

    assert lesson_service.offer_for_entry(store_with(*rows), USER, "current", NOW) is None


def test_general_preposition_errors_do_not_get_a_specific_personal_a_lesson():
    previous = entry("previous", NOW - timedelta(days=1), tag="preposition")
    current = entry("current", NOW, tag="preposition")
    for row in (previous, current):
        row["grammar_suggestions"] = [{
            "original": "de casa",
            "corrected": "desde casa",
            "error_type": "preposition",
        }]

    assert lesson_service.offer_for_entry(store_with(previous, current), USER, "current", NOW) is None


def test_offer_is_repeatable_for_same_entry_until_snoozed_and_not_for_others():
    store = store_with(entry("previous", NOW - timedelta(days=1)), entry("current", NOW))
    first = lesson_service.offer_for_entry(store, USER, "current", NOW)
    again = lesson_service.offer_for_entry(store, USER, "current", NOW + timedelta(seconds=5))
    assert first and again == first
    assert len(store.rows("lesson_offers")) == 1

    store.tables["journal_entries"].append(entry("later", NOW + timedelta(hours=1)))
    assert lesson_service.offer_for_entry(
        store, USER, "later", NOW + timedelta(hours=1)
    ) is None

    lesson_service.snooze(store, USER, "es", "ser_estar", NOW)
    assert lesson_service.offer_for_entry(store, USER, "current", NOW) is None


def test_snooze_and_recent_seen_state_suppress_repeat_offers():
    previous = entry("previous", NOW - timedelta(days=1))
    current = entry("current", NOW)
    store = store_with(previous, current)
    assert lesson_service.offer_for_entry(store, USER, "current", NOW)
    until = lesson_service.snooze(store, USER, "es", "ser_estar", NOW)
    assert datetime.fromisoformat(until) == NOW + timedelta(days=lesson_service.SNOOZE_DAYS)

    later_entry = entry("later", NOW + timedelta(days=1))
    store.tables["journal_entries"].append(later_entry)
    assert lesson_service.offer_for_entry(
        store, USER, "later", NOW + timedelta(days=1)
    ) is None

    # Once the snooze expires, a recently viewed lesson still stays quiet.
    state = store.rows("lesson_offers")[0]
    state["snoozed_until"] = (NOW + timedelta(days=8)).isoformat()
    assert lesson_service.mark_seen(store, USER, "es", "ser_estar", NOW + timedelta(days=8))
    latest = entry("latest", NOW + timedelta(days=9))
    store.tables["journal_entries"].append(latest)
    assert lesson_service.offer_for_entry(
        store, USER, "latest", NOW + timedelta(days=9)
    ) is None


def test_drill_builds_three_clozes_from_corrected_learner_sentences():
    rows = [
        entry(
            f"entry-{index}", NOW - timedelta(days=4 - index),
            tag="gender_agreement",
            original=source,
            corrected=corrected,
        )
        for index, (source, corrected) in enumerate([
            ("Mi casa es blanco.", "Mi casa es blanca."),
            ("El mesa es grande.", "La mesa es grande."),
            ("La perro pequeño corre.", "El perro pequeño corre."),
        ], start=1)
    ]
    for row, original_phrase, corrected_phrase in zip(
        rows, ("blanco", "El mesa", "La perro"), ("blanca", "La mesa", "El perro")
    ):
        row["grammar_suggestions"] = [{
            "original": original_phrase,
            "corrected": corrected_phrase,
            "error_type": "gender_agreement",
        }]
    current_id = rows[-1]["id"]
    store = store_with(*rows)
    store.tables["lesson_offers"] = [{
        "id": "offer-1", "user_id": USER, "l2": "es", "tag": "gender_agreement",
        "offered_at": NOW.isoformat(),
    }]

    items = lesson_service.drill_for_entry(
        store, USER, "es", "gender_agreement", current_id
    )

    assert len(items) == 3
    assert [item["answer"] for item in items] == ["El perro", "La mesa", "blanca"]
    assert "blanco" not in items[0]["before"] + items[0]["answer"] + items[0]["after"]


def test_lesson_content_is_original_and_flagged_for_native_speaker_review():
    content = lesson_service._LESSON_DATA
    assert content["needs_native_speaker_review"] is True
    assert content["review_status"] == "needs native-speaker review"
    assert 12 <= len(content["lessons"]) <= 15
    assert all(len(lesson["examples"]) == 3 and lesson["source_note"] for lesson in content["lessons"])

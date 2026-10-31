"""The word bank's pure rules: which words to offer, what counts as a use, and when a word is Mastered."""

from datetime import datetime, timedelta, timezone

import pytest

import review_scheduler as rs
from ai.schemas import GeminiJournalFeedback, JournalFeedback, TargetWordUse
from learning_policy import LEVELS, resolve_policy
from prompt_builder import TARGET_WORD_RULES, build_messages, build_user_message
from word_bank import (
    BankWord,
    bank_hint,
    clean_target_word_uses,
    is_mastered,
    pick_bank,
    summarize_uses,
    surface_forms,
    use_days,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
SCHEDULER = rs.make_scheduler(0.9, fuzz=False)


def word(word_id, status="learning", lemma=None, saved_days_ago=1, **card):
    return {
        "id": word_id, "status": status, "lemma": lemma or word_id, "term": lemma or word_id,
        "language": "es", "created_at": (NOW - timedelta(days=saved_days_ago)).isoformat(),
        "sense": "to make use of", "card": {"sense_in_context": "to make use of", "gloss_l1": "use", **card},
    }


def reviewed_card(days_overdue=2, stability=3.0, **extra):
    due = NOW - timedelta(days=days_overdue)
    return {
        "state": 2, "stability": stability, "difficulty": 5.0, "reps": 3, "suspended_at": None,
        "last_review": (due - timedelta(days=int(stability))).isoformat(), "due": due.isoformat(), **extra,
    }


def item(w, card=None, days=0, used=False, last_used=None):
    return BankWord(w, card, surface_forms(w), days, used or days > 0, last_used)


def ids(chosen):
    return [(entry.word["id"], reason) for entry, reason in chosen]


# --- Which words the bank offers ---------------------------------------------------------


def test_due_words_come_before_fresh_ones_and_at_risk_before_due():
    items = [
        item(word("fresh", "new", saved_days_ago=0)),
        item(word("due"), reviewed_card(days_overdue=0.2, stability=30.0)),
        item(word("risky"), reviewed_card(days_overdue=20, stability=3.0)),
    ]
    assert ids(pick_bank(items, NOW, SCHEDULER)) == [
        ("risky", "at_risk"), ("due", "due"), ("fresh", "never_used"),
    ]


def test_never_used_words_are_offered_newest_first_and_used_ones_are_not():
    items = [
        item(word("older", "new", saved_days_ago=9)),
        item(word("newest", "new", saved_days_ago=0)),
        item(word("done", "new", saved_days_ago=1), used=True),
    ]
    assert ids(pick_bank(items, NOW, SCHEDULER)) == [("newest", "never_used"), ("older", "never_used")]


def test_known_words_still_short_of_two_days_of_use_fill_the_bank_least_used_first():
    stable = {"state": 2, "stability": 40.0, "reps": 5, "due": (NOW + timedelta(days=30)).isoformat(),
              "suspended_at": NOW.isoformat()}
    items = [
        item(word("once", "known"), stable, days=1, last_used=NOW - timedelta(days=3)),
        item(word("never", "known"), stable, days=0),
        item(word("twice", "known"), stable, days=2),
    ]
    assert ids(pick_bank(items, NOW, SCHEDULER)) == [("never", "to_master"), ("once", "to_master")]


def test_known_by_tap_without_a_stable_card_is_not_offered():
    assert pick_bank([item(word("tapped", "known"))], NOW, SCHEDULER) == []


@pytest.mark.parametrize("status", ["mastered", "ignored"])
def test_finished_words_are_never_offered(status):
    assert pick_bank([item(word("w", status))], NOW, SCHEDULER) == []


def test_count_and_exclude_shape_the_offer_and_shuffle_skips_whats_on_screen():
    items = [item(word(f"w{i}", "new", saved_days_ago=i)) for i in range(10)]
    first = pick_bank(items, NOW, SCHEDULER, count=5)
    assert [e.word["id"] for e, _ in first] == ["w0", "w1", "w2", "w3", "w4"]
    again = pick_bank(items, NOW, SCHEDULER, count=5, exclude=[e.word["id"] for e, _ in first])
    assert [e.word["id"] for e, _ in again] == ["w5", "w6", "w7", "w8", "w9"]
    assert len(pick_bank(items, NOW, SCHEDULER, count=99)) == 8


def test_a_learning_word_never_reviewed_is_a_fresh_word_not_a_due_one():
    brand_new = {"state": 1, "reps": 0, "suspended_at": None, "due": NOW.isoformat()}
    assert ids(pick_bank([item(word("w"), brand_new)], NOW, SCHEDULER)) == [("w", "never_used")]


# --- Chips per policy ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "quiz, mode, hint",
    [
        ("recognition_l1", "shown", "use"),
        ("recognition_and_recall", "shown", "use"),
        ("cloze_l1_hint", "tap", "use"),
        ("l2_only", "tap", "to make use of"),
    ],
)
def test_the_gloss_follows_the_policy_quiz_flag(quiz, mode, hint):
    assert bank_hint(word("aprovechar"), quiz) == (hint, mode)


def test_levels_map_to_the_same_chips_as_the_policy_table():
    modes = [bank_hint(word("w"), LEVELS[level]["quiz"])[1] for level in range(4)]
    assert modes == ["shown", "shown", "tap", "tap"]


def test_surface_forms_keep_the_lemma_and_forms_met_without_repeats():
    w = word("madrugar", card_surface="x")
    w["card"]["surface"] = "madrugué"
    assert surface_forms(w, ["madrugaba", "Madrugar", ""]) == ("madrugar", "madrugué", "madrugaba")


# --- Mastered -----------------------------------------------------------------------------


def test_use_days_counts_different_utc_days_not_uses():
    stamps = ["2026-10-30T08:00:00+00:00", "2026-10-30T23:59:00Z", "2026-10-31T00:01:00+00:00", None]
    assert use_days(stamps) == 2


@pytest.mark.parametrize(
    "status, stability, days, expected",
    [
        ("known", 21.0, 2, True),
        ("learning", 30.0, 3, True),
        ("known", 20.9, 2, False),
        ("known", 40.0, 1, False),
        ("known", None, 5, False),
        ("new", 40.0, 5, False),
        ("mastered", 40.0, 5, False),
        ("ignored", 40.0, 5, False),
    ],
)
def test_mastered_needs_stable_recognition_and_correct_use_on_two_days(status, stability, days, expected):
    assert is_mastered(status, stability, days) is expected


# --- What counts as a use -----------------------------------------------------------------

TARGETS = [
    {"word_id": "w1", "lemma": "aprovechar", "term": "aprovechar", "forms": []},
    {"word_id": "w2", "lemma": "madrugar", "term": "madrugar", "forms": []},
    {"word_id": "w3", "lemma": "rato", "term": "rato", "forms": []},
    {"word_id": "w4", "lemma": "sobremesa", "term": "sobremesa", "forms": []},
]
TEXT = "Ayer madrugué para correr. Aproveché de la tarde. De sobremesa comí un helado."


def use(term, status, form="", fix="", note=""):
    return TargetWordUse(term=term, status=status, form_in_text=form, fix=fix, note=note)


def test_checked_uses_keep_request_order_and_the_sentence_they_were_written_in():
    cleaned = clean_target_word_uses(
        [
            use("rato", "not_used"),
            use("madrugar", "used_correctly", "madrugué"),
            use("aprovechar", "used_with_error", "Aproveché de la tarde", "Aproveché la tarde", "No lleva «de»."),
            use("sobremesa", "unclear", "sobremesa", note="¿Querías decir «después de comer»?"),
        ],
        TARGETS, TEXT, "es",
    )
    assert [(u["term"], u["status"]) for u in cleaned] == [
        ("aprovechar", "used_with_error"), ("madrugar", "used_correctly"),
        ("rato", "not_used"), ("sobremesa", "unclear"),
    ]
    madrugar = cleaned[1]
    assert madrugar["sentence"] == "Ayer madrugué para correr."
    assert madrugar["fix"] == "" and madrugar["note"] == ""
    assert cleaned[0]["fix"] == "Aproveché la tarde" and cleaned[0]["note"] == "No lleva «de»."
    assert cleaned[2]["form_in_text"] == "" and cleaned[2]["sentence"] == ""
    assert cleaned[3]["note"].startswith("¿Querías")


def test_a_use_the_entry_does_not_contain_is_dropped_not_stored():
    cleaned = clean_target_word_uses(
        [use("rato", "used_correctly", "un rato"), use("madrugar", "used_with_error", "madrugo", "madrugué")],
        TARGETS, TEXT, "es",
    )
    assert cleaned == []


def test_claims_about_words_that_were_not_requested_or_repeated_are_dropped():
    cleaned = clean_target_word_uses(
        [
            use("hablar", "used_correctly", "madrugué"),
            use("madrugar", "used_correctly", "madrugué"),
            use("madrugar", "not_used"),
        ],
        TARGETS, TEXT, "es",
    )
    assert [(u["word_id"], u["status"]) for u in cleaned] == [("w2", "used_correctly")]


def test_accents_and_case_in_the_term_do_not_hide_a_claim_and_nfd_text_still_matches():
    decomposed = "Ayer madrugué para correr."
    cleaned = clean_target_word_uses([use("MADRUGAR", "used_correctly", "madrugué")], TARGETS, decomposed, "es")
    assert [u["word_id"] for u in cleaned] == ["w2"]


def test_an_unclear_use_is_neither_correct_nor_an_error():
    cleaned = clean_target_word_uses([use("sobremesa", "unclear", "sobremesa", note="¿?")], TARGETS, TEXT, "es")
    assert summarize_uses(cleaned) == {
        "used_correctly": 0, "used_with_error": 0, "not_used": 0, "unclear": 1,
    }


def test_summary_counts_each_status():
    assert summarize_uses([{"status": s} for s in ["used_correctly"] * 3 + ["used_with_error", "not_used"]]) == {
        "used_correctly": 3, "used_with_error": 1, "not_used": 1, "unclear": 0,
    }


# --- Prompt and schema ---------------------------------------------------------------------


def test_target_word_uses_is_a_required_array_in_the_gemini_schema_but_optional_for_the_server():
    assert "target_word_uses" in GeminiJournalFeedback.model_json_schema()["required"]
    assert JournalFeedback.model_fields["target_word_uses"].is_required() is False


def test_the_rules_and_the_list_reach_the_prompt_only_when_words_were_chosen():
    effective = resolve_policy(None, "es", {"immersion_level": 2}, settings=None, language_profile=None)
    plain, _ = build_messages("Hola", effective)
    assert "**TARGET WORDS:**" not in plain and "target_word_uses" in plain
    system, _ = build_messages("Hola", effective, ["madrugar", "rato"])
    assert system.endswith(TARGET_WORD_RULES)
    for status in ("used_correctly", "used_with_error", "not_used", "unclear"):
        assert status in system
    assert "Never mark such a use wrong" in system
    message = build_user_message("Hola", effective, ["madrugar", "rato"])
    assert "TARGET WORDS (" in message and "- madrugar" in message and "- rato" in message
    assert "TARGET WORDS (" not in build_user_message("Hola", effective)
    assert "TARGET WORDS (" not in build_user_message("Hola", effective, [" ", ""])

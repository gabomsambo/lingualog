"""Vocabulary and review progress (§4.9), and the language grouping fix in the journal stats."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server
import review_scheduler as rs
from app.services import stats_service, vocab_service

USER = "00000000-0000-0000-0000-00000000000a"
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
HEADERS = {"X-User-ID": USER}


def iso(days=0, hours=0):
    return (NOW + timedelta(days=days, hours=hours)).isoformat()


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.limit_value = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args):
        return self

    def gte(self, *_args):
        return self

    def order(self, column, desc=False, **_kwargs):
        self.rows = sorted(self.rows, key=lambda row: row.get(column) or "", reverse=desc)
        return self

    def limit(self, count):
        self.limit_value = count
        return self

    def execute(self):
        rows = self.rows if self.limit_value is None else self.rows[:self.limit_value]
        return SimpleNamespace(data=rows, count=len(rows))


class FakeDb:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _name):
        return FakeQuery(self.rows)


# --- The journal stats fix ----------------------------------------------------


async def test_language_breakdown_groups_by_target_language_not_tone():
    db = FakeDb([
        {"target_language": "es", "tone": "Friendly", "original_text": "uno dos tres"},
        {"target_language": "es", "tone": "Grumpy", "original_text": "cuatro"},
        {"target_language": "fr", "tone": "Friendly", "original_text": "cinq six"},
    ])
    stats, total = await stats_service.get_language_breakdown(db, USER)
    assert total == 6
    by_language = {row.language: row for row in stats}
    assert set(by_language) == {"es", "fr"}
    assert by_language["es"].count == 4
    assert by_language["fr"].count == 2
    assert by_language["es"].percentage == pytest.approx(66.7, abs=0.1)


@pytest.mark.asyncio
async def test_error_patterns_count_recent_tags_and_treat_legacy_as_other():
    rows = [
        {"target_language": "es", "created_at": iso(), "grammar_suggestions": [
            {"error_type": "ser_estar"}, {"error_type": "gender_agreement"},
        ]},
        {"target_language": "es", "created_at": iso(hours=-1), "grammar_suggestions": [
            {"error_type": "ser_estar"}, {"error_type": "article"},
        ]},
        {"target_language": "es", "created_at": iso(hours=-2), "grammar_suggestions": [
            {"error_type": "ser_estar"}, {"error_type": "gender_agreement"},
            {"note": "legacy suggestion without a tag"},
        ]},
        {"target_language": "fr", "created_at": iso(hours=-3), "grammar_suggestions": [
            {"error_type": "preposition"}, {"error_type": "not_in_schema"},
        ]},
        {"target_language": "de", "created_at": iso(hours=-4), "grammar_suggestions": []},
    ]

    result = await stats_service.get_error_patterns_service(FakeDb(rows), USER)

    assert result.window_entries == 5
    by_language = {row.language: row for row in result.languages}
    assert [(tag.error_type, tag.count) for tag in by_language["es"].top_tags] == [
        ("ser_estar", 3),
        ("gender_agreement", 2),
        ("article", 1),
    ]
    assert {tag.error_type for tag in by_language["fr"].top_tags} == {"other", "preposition"}
    assert "de" not in by_language


@pytest.mark.asyncio
async def test_error_patterns_only_uses_the_named_recent_entry_window():
    rows = [
        {
            "target_language": "es",
            "created_at": iso(hours=-index),
            "grammar_suggestions": [{"error_type": "ser_estar"}],
        }
        for index in range(stats_service.ERROR_PATTERN_WINDOW_ENTRIES)
    ]
    rows.append({
        "target_language": "es",
        "created_at": iso(hours=-100),
        "grammar_suggestions": [{"error_type": "gender_agreement"}],
    })

    result = await stats_service.get_error_patterns_service(FakeDb(rows), USER)

    assert result.window_entries == stats_service.ERROR_PATTERN_WINDOW_ENTRIES
    assert [tag.model_dump() for tag in result.languages[0].top_tags] == [
        {"error_type": "ser_estar", "count": stats_service.ERROR_PATTERN_WINDOW_ENTRIES},
    ]


def test_error_patterns_endpoint_requires_a_user_and_returns_recent_tags(monkeypatch):
    import database

    db = FakeDb([{
        "target_language": "es",
        "created_at": iso(),
        "grammar_suggestions": [{"error_type": "por_para"}],
    }])
    monkeypatch.setattr(database, "create_supabase_client", lambda: db)
    client = TestClient(server.app, raise_server_exceptions=False)

    assert client.get("/user/stats/error-patterns").status_code == 401
    response = client.get("/user/stats/error-patterns", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "window_entries": 1,
        "languages": [{"language": "es", "top_tags": [{"error_type": "por_para", "count": 1}]}],
    }


# --- Pure progress helpers ----------------------------------------------------


def test_notebook_summary_counts_states_and_keeps_ignored_out_of_the_total():
    words = [
        {"status": "new"}, {"status": "new"}, {"status": "learning"},
        {"status": "known"}, {"status": "mastered"}, {"status": "ignored"},
    ]
    summary = stats_service.notebook_summary(words)
    assert summary == {
        "new": 2, "learning": 1, "known": 1, "mastered": 1, "ignored": 1, "total": 5,
    }


def test_notebook_trend_counts_words_saved_by_each_day():
    words = [
        {"status": "new", "created_at": iso(days=-2)},
        {"status": "known", "created_at": iso(days=-1)},
        {"status": "ignored", "created_at": iso(days=-2)},
        {"status": "new", "created_at": iso(days=1)},
    ]
    trend = stats_service.notebook_trend(words, NOW, days=3)
    assert [row["date"] for row in trend] == ["2026-11-08", "2026-11-09", "2026-11-10"]
    assert [row["count"] for row in trend] == [1, 2, 2]


def test_encounter_summary_counts_kinds_reviews_and_active_words():
    words = [
        {"id": "w1", "status": "learning"},
        {"id": "w2", "status": "new"},
        {"id": "w3", "status": "ignored"},
    ]
    encounters = [
        {"word_id": "w1", "kind": "lookup"},
        {"word_id": "w1", "kind": "entry_text"},
        {"word_id": "w1", "kind": "used_ok"},
        {"word_id": "w2", "kind": "lookup"},
        {"word_id": "w3", "kind": "used_ok"},
        {"word_id": None, "kind": "lookup"},
    ]
    cards = [{"id": "c1", "word_id": "w1"}]
    logs = [{"card_id": "c1", "rating": 3}, {"card_id": "c1", "rating": 1}]
    summary = stats_service.encounter_summary(words, encounters, cards, logs)
    assert summary["by_kind"]["lookup"] == 2
    assert summary["by_kind"]["entry_text"] == 1
    assert summary["by_kind"]["used_ok"] == 1
    assert summary["reviews"] == 2
    assert summary["active_words"] == 1
    # w1 met 5 times (3 encounters + 2 reviews), w2 once: mean 3.0 over the two studied words.
    assert summary["per_word"] == 3.0
    assert (summary["guide_min"], summary["guide_max"]) == (10, 12)


def test_true_retention_prefers_the_last_month():
    older = [{"rating": 1, "reviewed_at": iso(days=-60)}, {"rating": 1, "reviewed_at": iso(days=-59)}]
    recent = [{"rating": 3, "reviewed_at": iso(days=-2)}, {"rating": 1, "reviewed_at": iso(days=-1)}]
    assert stats_service.true_retention(older + recent, NOW) == 0.5
    assert stats_service.true_retention(older, NOW) == 0.0
    assert stats_service.true_retention([], NOW) is None


def test_review_summary_counts_due_forecast_and_at_risk():
    cards = [
        # Due two days ago and barely stable: overdue and likely forgotten.
        {"id": "c1", "word_id": "w1", "language": "es", "card_type": "recognition", "state": 2,
         "reps": 3, "stability": 0.5, "difficulty": 5.0, "due": iso(days=-2),
         "last_review": iso(days=-3), "suspended_at": None},
        # Due in two days: not today, but inside the forecast.
        {"id": "c2", "word_id": "w2", "language": "es", "card_type": "recognition", "state": 2,
         "reps": 3, "stability": 30.0, "difficulty": 5.0, "due": iso(days=2),
         "last_review": iso(days=-3), "suspended_at": None},
        # Never reviewed: a new word, due from creation and dealt as new.
        {"id": "c3", "word_id": "w3", "language": "es", "card_type": "recognition", "state": 1,
         "reps": 0, "stability": None, "difficulty": None, "due": iso(),
         "last_review": None, "suspended_at": None},
        # Suspended: never offered.
        {"id": "c4", "word_id": "w4", "language": "es", "card_type": "recognition", "state": 2,
         "reps": 3, "stability": 30.0, "difficulty": 5.0, "due": iso(days=-2),
         "last_review": iso(days=-3), "suspended_at": iso(days=-1)},
    ]
    logs = [{"rating": 3, "reviewed_at": iso(days=-1), "duration_ms": 60000}]
    schedulers = {"es": rs.make_scheduler(0.9, None, fuzz=False)}
    summary = stats_service.review_summary(cards, logs, NOW, schedulers)
    assert summary["due_today"] == 2
    assert summary["new_today"] == 1
    assert summary["at_risk"] == 1
    assert summary["reviews_last_7_days"] == 1
    assert summary["minutes_last_7_days"] == 1.0
    assert summary["true_retention"] == 1.0
    assert len(summary["forecast"]) == 7
    assert summary["forecast"][0]["date"] == "2026-11-10"
    assert summary["forecast"][2]["count"] == 1


def test_week_summary_flags_a_review_heavy_week():
    encounters = [{"kind": "read", "created_at": iso(days=-1)}]
    logs = [{"rating": 3, "reviewed_at": iso(days=-1), "duration_ms": 30 * 60000}] * 25
    summary = stats_service.week_summary(2, encounters, logs, NOW)
    assert summary["reading"] == 1
    assert summary["journal"] == 2
    assert summary["reviews"] == 25
    assert summary["over_budget"] is True
    calm = stats_service.week_summary(8, [], [{"rating": 3, "reviewed_at": iso(), "duration_ms": 60000}], NOW)
    assert calm["over_budget"] is False


# --- The composed payload ------------------------------------------------------


def install_vocabulary(monkeypatch, words=(), encounters=(), cards=(), logs=(), profiles=()):
    monkeypatch.setattr(vocab_service, "load_words", lambda user_id, language=None: list(words))
    monkeypatch.setattr(vocab_service, "load_encounters", lambda user_id, language=None: list(encounters))
    monkeypatch.setattr(vocab_service, "load_cards", lambda user_id, language=None: list(cards))
    monkeypatch.setattr(vocab_service, "load_review_logs", lambda user_id, language=None: list(logs))
    monkeypatch.setattr(vocab_service, "load_profiles", lambda user_id: list(profiles))
    monkeypatch.setattr(vocab_service, "load_fsrs_parameters", lambda user_id: [])
    monkeypatch.setattr(vocab_service, "count_entries_since", lambda user_id, since: 3)
    monkeypatch.setattr(vocab_service, "placement_available", lambda language: language == "es")


def test_vocab_progress_composes_the_page_payload(monkeypatch):
    install_vocabulary(
        monkeypatch,
        words=[
            {"id": "w1", "status": "learning", "created_at": iso(days=-5)},
            {"id": "w2", "status": "new", "created_at": iso(days=-1)},
        ],
        encounters=[{"word_id": "w1", "kind": "lookup", "created_at": iso(days=-2)}],
        cards=[{"id": "c1", "word_id": "w1", "language": "es", "card_type": "recognition", "state": 2,
                "reps": 2, "stability": 40.0, "difficulty": 5.0, "due": iso(days=-1),
                "last_review": iso(days=-5), "suspended_at": None}],
        logs=[{"card_id": "c1", "rating": 3, "reviewed_at": iso(days=-1), "duration_ms": 45000}],
        profiles=[{"l2": "es", "desired_retention": 0.9, "placement": {"estimate": 2200}}],
    )
    payload = stats_service.get_vocab_progress(USER, "es", now=NOW)
    assert payload["language"] == "es"
    assert payload["notebook"]["total"] == 2
    assert len(payload["trend"]) == 30
    assert payload["active_words"] == 0
    assert payload["encounters"]["by_kind"]["lookup"] == 1
    assert payload["review"]["due_today"] == 1
    assert payload["review"]["true_retention"] == 1.0
    assert payload["week"]["journal"] == 3
    assert payload["placement"] == {"estimate": 2200}
    assert payload["placement_available"] is True


def test_progress_endpoint_requires_a_user_and_returns_the_payload(monkeypatch):
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.get("/vocabulary/progress").status_code == 401

    monkeypatch.setattr(
        stats_service, "get_vocab_progress",
        lambda user_id, language=None: {"language": language, "notebook": {"total": 1}},
    )
    response = client.get("/vocabulary/progress?language=es", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"language": "es", "notebook": {"total": 1}}

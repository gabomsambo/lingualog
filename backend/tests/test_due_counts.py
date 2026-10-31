"""One definition of "due": never-reviewed cards the session serves must count everywhere.

The vocabulary V1 due-count bug: `GET /review/session` dealt a brand-new card while
`GET /vocabulary/progress`, the Vocabulary list and the dashboard said nothing was due.
"""

from datetime import datetime, timedelta, timezone

import review_scheduler as rs
from app.services import review_service, stats_service, vocab_service

USER = "00000000-0000-0000-0000-00000000000c"
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def iso(days=0):
    return (NOW + timedelta(days=days)).isoformat()


def card(card_id: str, word_id: str, **overrides):
    row = {
        "id": card_id, "word_id": word_id, "language": "es", "card_type": "recognition",
        "state": 2, "reps": 3, "stability": 20.0, "difficulty": 5.0, "due": iso(days=-1),
        "last_review": iso(days=-2), "suspended_at": None,
    }
    row.update(overrides)
    return row


# The two cards of the bug: one reviewed and due, one never reviewed (due from creation).
REVIEWED = card("c-reviewed", "w-reviewed")
NEW = card("c-new", "w-new", state=1, reps=0, stability=None, difficulty=None,
           due=iso(), last_review=None)


def test_never_reviewed_due_cards_count_the_same_everywhere(monkeypatch):
    scheduler = rs.make_scheduler(0.9, None, fuzz=False)
    cards = [REVIEWED, NEW]

    # Review deals both cards.
    plan = rs.plan_session(
        cards, NOW, scheduler, daily_new_words=10, reviewed_new_today=0, reviews_today=0
    )
    assert {row["word_id"] for row in plan.cards} == {"w-reviewed", "w-new"}

    # Statistics counts both as due today, new ones as their own count.
    summary = stats_service.review_summary(cards, [], NOW, {"es": scheduler})
    assert summary["due_today"] == 2
    assert summary["new_today"] == 1

    # The Vocabulary "Due for review" list counts both words.
    monkeypatch.setattr(vocab_service, "load_words", lambda user_id, language=None: [
        {"id": "w-reviewed", "status": "learning"}, {"id": "w-new", "status": "learning"},
    ])
    monkeypatch.setattr(vocab_service, "load_encounters", lambda user_id, language=None: [])
    monkeypatch.setattr(vocab_service, "load_cards", lambda user_id, language=None: cards)
    monkeypatch.setattr(vocab_service, "load_entry_summaries", lambda user_id, entry_ids: {})
    monkeypatch.setattr(vocab_service, "load_books", lambda user_id, book_ids: {})
    monkeypatch.setattr(vocab_service, "books_available", lambda: False)
    lists = vocab_service.get_lists(USER, "es", now=NOW)
    counts = {row["id"]: row["count"] for row in lists["smart"]}
    assert counts["due"] == 2

    # The dashboard count is what the session deals, with new cards shown apart.
    dashboard = review_service._counts(plan)
    assert dashboard["total"] == len(plan.cards) == 2
    assert dashboard["new"] == 1


def test_a_suspended_card_is_due_nowhere():
    scheduler = rs.make_scheduler(0.9, None, fuzz=False)
    suspended = card("c-off", "w-off", suspended_at=iso(days=-1))

    plan = rs.plan_session(
        [suspended], NOW, scheduler, daily_new_words=10, reviewed_new_today=0, reviews_today=0
    )
    assert plan.cards == []
    assert stats_service.review_summary([suspended], [], NOW, {"es": scheduler})["due_today"] == 0
    assert vocab_service._is_due(suspended, NOW) is False

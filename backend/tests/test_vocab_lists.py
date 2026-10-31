"""Notebook lists (tags plus smart lists) and the vocabulary filters."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import server
from app.services import vocab_service

USER = "00000000-0000-0000-0000-00000000000a"
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
HEADERS = {"X-User-ID": USER}


def iso(days=0):
    return (NOW + timedelta(days=days)).isoformat()


def word(word_id, **extra):
    row = {
        "id": word_id, "user_id": USER, "language": "es", "lemma": word_id, "term": word_id,
        "status": "new", "tags": [], "entry_id": None, "book_id": None,
        "example_sentence": "", "created_at": iso(days=-3),
    }
    row.update(extra)
    return row


def card(card_id, word_id, **extra):
    row = {
        "id": card_id, "word_id": word_id, "language": "es", "card_type": "recognition",
        "state": 1, "step": None, "stability": None, "difficulty": None, "due": iso(),
        "last_review": None, "reps": 0, "lapses": 0, "suspended_at": None,
    }
    row.update(extra)
    return row


def install(monkeypatch, words=(), encounters=(), cards=(), entries=None, books_available=False, books=None):
    monkeypatch.setattr(vocab_service, "load_words", lambda user_id, language=None: list(words))
    monkeypatch.setattr(vocab_service, "load_encounters", lambda user_id, language=None: list(encounters))
    monkeypatch.setattr(vocab_service, "load_cards", lambda user_id, language=None: list(cards))
    monkeypatch.setattr(
        vocab_service, "load_entry_summaries", lambda user_id, entry_ids: dict(entries or {})
    )
    monkeypatch.setattr(vocab_service, "books_available", lambda: books_available)
    monkeypatch.setattr(vocab_service, "load_books", lambda user_id, book_ids: dict(books or {}))


# --- Lists --------------------------------------------------------------------


def test_lists_count_smart_lists_tags_entries_and_books(monkeypatch):
    install(
        monkeypatch,
        words=[
            word("w1", status="learning", tags=["travel"], entry_id="e1"),
            word("w2", tags=["travel", "food"]),
            word("w3", status="known"),
        ],
        encounters=[
            {"word_id": "w1", "kind": "entry_text"},
            {"word_id": "w3", "kind": "used_ok"},
            {"word_id": "w3", "kind": "read", "book_id": "b1"},
        ],
        cards=[
            card("c1", "w1", reps=2, due=iso(days=-1), state=2, last_review=iso(days=-3)),
            card("c2", "w2", reps=2, due=iso(days=3), state=2, last_review=iso(days=-3)),
        ],
        entries={"e1": {"id": "e1", "title": "Un día en Madrid", "created_at": iso(days=-4)}},
        books_available=True,
        books={"b1": {"id": "b1", "title": "El principito"}},
    )
    lists = vocab_service.get_lists(USER, "es", now=NOW)
    assert lists["total"] == 3
    assert lists["smart"] == [{"id": "due", "count": 1}, {"id": "never_used", "count": 1}]
    assert lists["tags"] == [
        {"id": "tag:food", "name": "food", "count": 1},
        {"id": "tag:travel", "name": "travel", "count": 2},
    ]
    assert lists["entries"] == [{
        "id": "entry:e1", "entry_id": "e1", "title": "Un día en Madrid",
        "date": iso(days=-4)[:10], "count": 1,
    }]
    assert lists["books"] == [{"id": "book:b1", "book_id": "b1", "title": "El principito", "count": 1}]


def test_by_book_list_is_absent_without_the_books_table(monkeypatch):
    install(monkeypatch, words=[word("w1", book_id="b1")], books_available=False)
    assert vocab_service.get_lists(USER, now=NOW)["books"] is None


def test_words_are_found_by_their_reading_book():
    items = [word("w1"), word("w2")]
    encounters = [
        {"word_id": "w1", "kind": "read", "book_id": "b1"},
        {"word_id": "w2", "kind": "lookup", "book_id": "b2"},
    ]
    selected = vocab_service.filter_items(items, encounters, [], {"book_id": "b1"}, now=NOW)
    assert [row["id"] for row in selected] == ["w1"]
    assert vocab_service.source_of(items[0], vocab_service.book_of_word(encounters)) == "book"
    assert vocab_service.source_of(items[1], vocab_service.book_of_word(encounters)) == "book"


def test_never_used_ignores_writing_evidence():
    items = [word("w1"), word("w2"), word("w3")]
    encounters = [
        {"word_id": "w1", "kind": "entry_text"},
        {"word_id": "w2", "kind": "entry_fix"},
        {"word_id": "w3", "kind": "lookup"},
    ]
    selected = vocab_service.filter_items(items, encounters, [], {"list": "never_used"}, now=NOW)
    assert [row["id"] for row in selected] == ["w2", "w3"]


def test_due_list_counts_answered_and_new_cards_that_are_due():
    items = [word("w1"), word("w2"), word("w3"), word("w4")]
    cards = [
        card("c1", "w1", reps=1, due=iso(days=-1)),
        card("c2", "w2", reps=1, due=iso(days=2)),
        card("c3", "w3", reps=0, due=iso(days=-1)),
        card("c4", "w4", reps=1, due=iso(days=-1), suspended_at=iso()),
    ]
    selected = vocab_service.filter_items(items, [], cards, {"list": "due"}, now=NOW)
    assert [row["id"] for row in selected] == ["w1", "w3"]


def test_a_saved_sentence_that_is_just_the_word_shows_no_quote():
    bare = word("w1", lemma="madrugar", term="madrugar", example_sentence="madrugar")
    assert vocab_service.scrub_example_sentences([bare])[0]["example_sentence"] == ""
    kept = word("w2", lemma="mesa", term="mesa", example_sentence="La mesa está lista.")
    assert vocab_service.scrub_example_sentences([kept])[0]["example_sentence"] == "La mesa está lista."


def test_the_first_sentence_skips_a_word_quoted_to_itself():
    bare = word("w1", lemma="madrugar", term="madrugar", example_sentence="madrugar")
    encounters = [{"sentence": "Tuve que madrugar mucho.", "surface": "madrugar",
                   "kind": "lookup", "created_at": iso(days=-1)}]
    assert vocab_service._first_sentence(bare, encounters) == "Tuve que madrugar mucho."
    assert vocab_service._first_sentence(bare, []) == ""


def test_filters_combine_tags_source_status_and_entry():
    items = [
        word("w1", tags=["travel"], entry_id="e1", status="learning"),
        word("w2", tags=["travel"], entry_id="e2", status="learning"),
        word("w3", tags=["food"], status="new"),
    ]
    assert [r["id"] for r in vocab_service.filter_items(items, [], [], {"tag": "travel"})] == ["w1", "w2"]
    assert [r["id"] for r in vocab_service.filter_items(items, [], [], {"entry_id": "e2"})] == ["w2"]
    assert [r["id"] for r in vocab_service.filter_items(items, [], [], {"source": "entry"})] == ["w1", "w2"]
    assert [r["id"] for r in vocab_service.filter_items(items, [], [], {"source": "lookup"})] == ["w3"]
    combined = vocab_service.filter_items(items, [], [], {"tag": "travel", "status": "learning", "source": "entry"})
    assert [r["id"] for r in combined] == ["w1", "w2"]


def test_selector_validates_values():
    assert vocab_service.selector_from("due", "travel") == {"list": "due", "tag": "travel"}
    with pytest.raises(ValueError):
        vocab_service.selector_from("someday")
    with pytest.raises(ValueError):
        vocab_service.selector_from(status="saved")
    with pytest.raises(ValueError):
        vocab_service.selector_from(source="book_session")


# --- The routes ----------------------------------------------------------------


def test_lists_route_hands_back_the_lists(monkeypatch):
    monkeypatch.setattr(
        vocab_service, "get_lists", lambda user_id, language=None: {"smart": [], "tags": [], "entries": [], "books": None}
    )
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.get("/vocabulary/lists").status_code == 401
    response = client.get("/vocabulary/lists?language=es", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["books"] is None


def test_vocabulary_route_applies_the_list_filter(monkeypatch):
    monkeypatch.setattr(
        server.review_service, "attach_review_state", lambda user_id, items: items
    )
    called = {}

    def fetch_items(user_id, language, selector):
        called.update(selector)
        return [{"id": "w1"}]

    monkeypatch.setattr(vocab_service, "fetch_items", fetch_items)
    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.get("/vocabulary?list=never_used&tag=travel", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == [{"id": "w1"}]
    assert called == {"list": "never_used", "tag": "travel"}


def test_vocabulary_route_rejects_an_unknown_list(monkeypatch):
    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.get("/vocabulary?list=someday", headers=HEADERS)
    assert response.status_code == 400

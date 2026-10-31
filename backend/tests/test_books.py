"""Book mode: books, mark-only capture, end-of-session cards, glossary, progress, page photos."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import database
import server
from ai.gemini import GeminiError
from ai.page_photo import PageTranscription, PageWord
from ai.word_card import WordCard
from app.services import book_service, review_service
from learning_policy import resolve_policy
from tests.fake_supabase import FakeSupabase
from tests.test_word_card import CARD

USER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"
HEADERS = {"X-User-ID": USER}
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    for module in (database, book_service, review_service):
        monkeypatch.setattr(module, "create_supabase_client", lambda: fake)
    policy = resolve_policy(
        None, "es", {"immersion_level": 1}, settings={"native_lang": "en"},
        language_profile={"immersion_level": 1, "proficiency": "B1"},
    )
    monkeypatch.setattr(book_service, "resolve_policy", lambda *_: policy)
    monkeypatch.setattr(server, "resolve_policy", lambda *_: policy)
    return fake


@pytest.fixture
def client(db):
    return TestClient(server.app)


def card_for(lemma, sense="meaning"):
    return WordCard.model_validate({**CARD, "lemma": lemma, "sense_in_context": sense})


def make_book(client, **fields):
    body = {"title": "La sombra del viento", "author": "Carlos Ruiz Zafón", "language": "es", **fields}
    return client.post("/books", headers=HEADERS, json=body).json()


def start(client, book, page_from=None):
    return client.post(f"/books/{book['id']}/sessions", headers=HEADERS, json={"page_from": page_from}).json()


def mark(client, book, session, word, page=None, sentence=None, headers=HEADERS):
    return client.post(
        f"/books/{book['id']}/sessions/{session['id']}/marks",
        headers=headers, json={"word": word, "page": page, "sentence": sentence},
    )


def test_books_belong_to_their_owner(client):
    book = make_book(client)
    stranger = {"X-User-ID": OTHER}

    assert client.get(f"/books/{book['id']}", headers=stranger).status_code == 404
    assert client.patch(f"/books/{book['id']}", headers=stranger, json={"status": "finished"}).status_code == 404
    assert client.delete(f"/books/{book['id']}", headers=stranger).status_code == 404
    assert client.get("/books", headers=stranger).json() == []
    assert [b["id"] for b in client.get("/books", headers=HEADERS).json()] == [book["id"]]
    assert client.get("/books").status_code == 401


def test_book_needs_a_language_code_and_a_title(client):
    assert client.post("/books", headers=HEADERS, json={"title": "x", "language": "spanish!"}).status_code == 400
    assert client.post("/books", headers=HEADERS, json={"title": "", "language": "es"}).status_code == 422


def test_starting_twice_resumes_the_open_session(client):
    book = make_book(client)
    first = start(client, book, page_from=37)
    second = start(client, book)

    assert second["id"] == first["id"]
    assert client.get(f"/books/{book['id']}", headers=HEADERS).json()["session"]["id"] == first["id"]


def test_marking_makes_no_model_call_and_counts_a_word_again_on_a_later_page(client, monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr(book_service, "generate_word_card", provider)
    book = make_book(client)
    session = start(client, book)

    first = mark(client, book, session, "Estremecí.", page=37, sentence="Me estremecí al oírlo.")
    again = mark(client, book, session, "estremecí", page=52)
    double_tap = mark(client, book, session, "estremecí", page=52)

    assert first.status_code == 201
    assert first.json()["surface"] == "Estremecí"
    assert first.json()["times_marked"] == 1
    assert again.json()["times_marked"] == 2
    assert double_tap.status_code == 200 and double_tap.json()["times_marked"] == 2
    provider.assert_not_awaited()


def test_a_mark_is_a_reading_encounter_with_its_sentence_and_page(client, db):
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "atar", page=12, sentence="Quiso atar los cabos.")

    (row,) = db.rows("word_encounters")
    assert (row["kind"], row["source_type"], row["source_id"]) == ("read", "book_session", session["id"])
    assert (row["book_id"], row["page"], row["card"], row["card_status"]) == (book["id"], 12, None, "pending")
    assert row["sentence"] == "Quiso atar los cabos."


def test_other_learners_cannot_mark_in_your_session(client):
    book = make_book(client)
    session = start(client, book)

    assert mark(client, book, session, "atar", headers={"X-User-ID": OTHER}).status_code == 404


def test_a_mark_can_be_undone_only_while_reading(client, db):
    book = make_book(client)
    session = start(client, book)
    marked = mark(client, book, session, "atar", page=3).json()
    url = f"/books/{book['id']}/sessions/{session['id']}/marks/{marked['id']}"

    assert client.delete(url, headers={"X-User-ID": OTHER}).status_code == 404
    assert client.delete(url, headers=HEADERS).status_code == 204
    assert db.rows("word_encounters") == []

    client.post(f"/books/{book['id']}/sessions/{session['id']}/end", headers=HEADERS, json={})
    assert client.delete(url, headers=HEADERS).status_code == 409
    assert mark(client, book, session, "atar").status_code == 409


def test_ending_a_session_fixes_its_pages_and_words_per_page(client):
    book = make_book(client)
    session = start(client, book, page_from=10)
    for word, page in (("atar", 10), ("cinta", 12), ("atar", 15)):
        mark(client, book, session, word, page=page)

    ended = client.post(
        f"/books/{book['id']}/sessions/{session['id']}/end", headers=HEADERS, json={"page_to": 16}
    ).json()

    assert (ended["page_from"], ended["page_to"], ended["pages_read"], ended["words_marked"]) == (10, 16, 7, 3)
    assert ended["words_per_page"] == 0.4
    assert ended["band"] == "comfortable"
    assert client.get(f"/books/{book['id']}", headers=HEADERS).json()["session"] is None


def test_a_session_without_pages_has_no_words_per_page(client):
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "atar")

    ended = client.post(f"/books/{book['id']}/sessions/{session['id']}/end", headers=HEADERS, json={}).json()

    assert ended["pages_read"] is None and ended["words_per_page"] is None and ended["band"] is None


def test_cards_are_built_in_one_batch_with_recurring_words_first(client, db, monkeypatch):
    lemmas = {"cinta": "cinta", "llevaba": "llevar", "atadas": "atar", "atar": "atar"}
    provider = AsyncMock(side_effect=lambda surface, sentence, policy: card_for(lemmas[surface]))
    monkeypatch.setattr(book_service, "generate_word_card", provider)
    monkeypatch.setattr(book_service, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    earlier = start(client, book)
    mark(client, book, earlier, "atadas", page=3, sentence="Tenía las manos atadas.")
    client.post(f"/books/{book['id']}/sessions/{earlier['id']}/end", headers=HEADERS, json={})
    client.post(f"/books/{book['id']}/sessions/{earlier['id']}/cards", headers=HEADERS)
    session = start(client, book)
    mark(client, book, session, "cinta", page=20)
    mark(client, book, session, "llevaba", page=21)
    mark(client, book, session, "atar", page=22, sentence="Quiso atar los cabos.")

    response = client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS)

    items = response.json()["items"]
    assert [item["lemma"] for item in items][0] == "atar"
    assert items[0]["recurring"] and items[0]["times_marked"] == 2
    assert not items[1]["recurring"]
    assert {item["lemma"] for item in items} == {"atar", "cinta", "llevar"}
    assert all(item["card"] and item["encounter_id"] for item in items)
    assert response.json()["failed"] == 0
    assert provider.await_count == 4


def test_the_choice_shows_the_latest_sentence_that_was_kept(client, monkeypatch):
    provider = AsyncMock(return_value=card_for("cinta"))
    monkeypatch.setattr(book_service, "generate_word_card", provider)
    monkeypatch.setattr(book_service, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "cinta", page=2, sentence="Una cinta roja.")
    mark(client, book, session, "cinta", page=3)

    item = client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS).json()["items"][0]

    assert item["sentence"] == "Una cinta roja."
    assert provider.await_args.args[1] == "Una cinta roja."


def test_a_failed_card_stores_no_error_and_can_be_retried(client, db, monkeypatch):
    provider = AsyncMock(side_effect=GeminiError("ai_quota_exhausted", "no credits left"))
    monkeypatch.setattr(book_service, "generate_word_card", provider)
    monkeypatch.setattr(book_service, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "cinta", page=2, sentence="Una cinta roja.")

    first = client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS).json()

    assert first["failed"] == 1
    assert first["items"][0]["card"] is None and first["items"][0]["card_status"] == "failed"
    assert "no credits" not in str(db.rows("word_encounters"))
    assert db.rows("word_encounters")[0]["card"] is None

    provider.side_effect = lambda *_: card_for("cinta")
    second = client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS).json()
    assert second["failed"] == 0 and second["items"][0]["card_status"] == "ok"


def test_a_word_already_in_the_notebook_leaves_the_choices(client, db, monkeypatch):
    monkeypatch.setattr(book_service, "generate_word_card", AsyncMock(return_value=card_for("atar")))
    monkeypatch.setattr(book_service, "fetch_lookup_cache", lambda *_: None)
    db.table("user_vocabulary").insert(
        {"id": "word-1", "user_id": USER, "term": "atar", "lemma": "atar", "language": "es", "status": "learning"}
    ).execute()
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "atadas", page=2, sentence="Manos atadas.")

    triage = client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS).json()

    assert triage["items"] == []
    assert db.rows("word_encounters")[0]["word_id"] == "word-1"


def test_skipping_hides_marks_from_the_choices_but_keeps_them_in_the_glossary(client, monkeypatch):
    monkeypatch.setattr(book_service, "generate_word_card", AsyncMock(return_value=card_for("cinta", "a ribbon")))
    monkeypatch.setattr(book_service, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "cinta", page=4, sentence="Una cinta roja.")
    item = client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS).json()["items"][0]

    skipped = client.post(
        f"/books/{book['id']}/marks/skip", headers=HEADERS, json={"encounter_ids": item["encounter_ids"]}
    )
    stranger = client.post(
        f"/books/{book['id']}/marks/skip", headers={"X-User-ID": OTHER}, json={"encounter_ids": item["encounter_ids"]}
    )

    assert skipped.json() == {"skipped": 1}
    assert stranger.status_code == 404
    assert client.get(f"/books/{book['id']}/sessions/{session['id']}/triage", headers=HEADERS).json()["items"] == []
    (word,) = client.get(f"/books/{book['id']}/glossary", headers=HEADERS).json()["words"]
    assert (word["lemma"], word["meaning"], word["pages"], word["skipped"]) == ("cinta", "a ribbon", [4], True)


def test_glossary_groups_surfaces_under_one_word_with_sentences_and_pages(client, monkeypatch):
    monkeypatch.setattr(book_service, "generate_word_card", AsyncMock(return_value=card_for("atar", "to tie")))
    monkeypatch.setattr(book_service, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "atadas", page=3, sentence="Tenía las manos atadas.")
    client.post(f"/books/{book['id']}/sessions/{session['id']}/cards", headers=HEADERS)
    mark(client, book, session, "atadas", page=9, sentence="Las dejó atadas.")

    glossary = client.get(f"/books/{book['id']}/glossary", headers=HEADERS).json()

    (word,) = glossary["words"]
    assert word["lemma"] == "atar" and word["times_marked"] == 2 and word["pages"] == [3, 9]
    assert word["meaning"] == "to tie" and word["gloss"]
    assert [s["page"] for s in word["sentences"]] == [9, 3]
    assert glossary["book"]["title"] == "La sombra del viento"


def test_progress_charts_words_per_page_and_flags_a_book_that_stays_hard(client):
    book = make_book(client)
    for marks, last_page in ((30, 2), (20, 2), (10, 2)):
        session = start(client, book, page_from=1)
        for index in range(marks):
            mark(client, book, session, f"palabra{index}", page=1 + index % 2)
        client.post(f"/books/{book['id']}/sessions/{session['id']}/end", headers=HEADERS, json={"page_to": last_page})

    progress = client.get(f"/books/{book['id']}/progress", headers=HEADERS).json()

    assert [s["words_per_page"] for s in progress["sessions"]] == [15.0, 10.0, 5.0]
    assert progress["trend"] == "falling" and progress["latest_band"] == "comfortable"
    assert progress["stays_hard"] is False and progress["estimate"] is True
    assert progress["pages"][0]["band"] in {"study", "comfortable"}


def test_a_book_stays_hard_after_three_hard_sessions(client):
    book = make_book(client)
    for _ in range(3):
        session = start(client, book, page_from=1)
        for index in range(60):
            mark(client, book, session, f"w{index}", page=1)
        client.post(f"/books/{book['id']}/sessions/{session['id']}/end", headers=HEADERS, json={"page_to": 2})

    assert client.get(f"/books/{book['id']}/progress", headers=HEADERS).json()["stays_hard"] is True


def test_recent_book_words_are_the_saved_words_marked_this_week(client, db):
    book = make_book(client)
    session = start(client, book)
    for word in ("cinta", "atar", "mesa"):
        mark(client, book, session, word, page=1)
    db.rows("word_encounters")[1]["word_id"] = "word-atar"
    db.rows("word_encounters")[2]["word_id"] = "word-mesa"
    db.rows("word_encounters")[2]["created_at"] = "2020-01-01T00:00:00+00:00"

    assert book_service.recent_book_word_ids(USER, book["id"]) == {"word-atar"}
    assert book_service.recent_book_word_ids(OTHER, book["id"]) == set()


def test_deleting_a_book_keeps_saved_words_and_drops_unsaved_marks(client, db):
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "cinta", page=1)
    mark(client, book, session, "atar", page=1)
    db.rows("word_encounters")[1]["word_id"] = "word-1"

    assert client.delete(f"/books/{book['id']}", headers=HEADERS).status_code == 204

    assert [row["lemma"] for row in db.rows("word_encounters")] == ["atar"]
    assert db.rows("books") == []


# --- Lookup from a reading session ("I need this now") -------------------------


def lookup(client, book, session, text="cinta", page=7, language="es", headers=HEADERS):
    return client.post(
        "/lookup", headers=headers,
        json={"text": text, "sentence": "Una cinta roja.", "language": language,
              "source": "book_session", "source_id": session["id"], "page": page},
    )


def test_i_need_this_now_shows_the_card_and_counts_as_a_mark(client, db, monkeypatch):
    monkeypatch.setattr(server, "generate_word_card", AsyncMock(return_value=card_for("cinta", "a ribbon")))
    monkeypatch.setattr(server, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)

    response = lookup(client, book, session)

    assert response.status_code == 200 and response.json()["card"]["sense_in_context"] == "a ribbon"
    (row,) = db.rows("word_encounters")
    assert (row["kind"], row["source_type"], row["book_id"], row["page"]) == ("read", "book_session", book["id"], 7)


def test_a_lookup_completes_the_mark_already_made_instead_of_doubling_it(client, db, monkeypatch):
    monkeypatch.setattr(server, "generate_word_card", AsyncMock(return_value=card_for("cinta")))
    monkeypatch.setattr(server, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)
    mark(client, book, session, "cinta", page=7, sentence="La cinta del pelo.")

    lookup(client, book, session)

    (row,) = db.rows("word_encounters")
    assert row["card_status"] == "ok" and row["card"] and row["sentence"] == "La cinta del pelo."


def test_a_lookup_must_use_your_session_and_the_books_language(client, monkeypatch):
    monkeypatch.setattr(server, "generate_word_card", AsyncMock(return_value=card_for("cinta")))
    monkeypatch.setattr(server, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)

    assert lookup(client, book, session, headers={"X-User-ID": OTHER}).status_code == 404
    assert lookup(client, book, session, language="fr").status_code == 400
    assert client.post(
        "/lookup", headers=HEADERS, json={"text": "cinta", "language": "es", "source": "book_session"}
    ).status_code == 404


def test_a_lookup_against_an_ended_session_is_refused(client, db, monkeypatch):
    generator = AsyncMock(return_value=card_for("cinta"))
    monkeypatch.setattr(server, "generate_word_card", generator)
    monkeypatch.setattr(server, "fetch_lookup_cache", lambda *_: None)
    book = make_book(client)
    session = start(client, book)
    client.post(f"/books/{book['id']}/sessions/{session['id']}/end", headers=HEADERS, json={})

    response = lookup(client, book, session)

    assert response.status_code == 409 and response.json()["detail"]["code"] == "session_ended"
    assert db.rows("word_encounters") == []
    generator.assert_not_awaited()


# --- Page photo ---------------------------------------------------------------


PAGE = PageTranscription(
    readable=True,
    transcription="Tenía las manos atadas con una cinta. Estremecí al verla.",
    candidates=[PageWord(surface="atadas", lemma="atar"), PageWord(surface="estremecí", lemma="estremecerse"),
                PageWord(surface="cinta", lemma="cinta")],
)


def photo(client, book, body=JPEG, headers=HEADERS):
    return client.post(
        f"/books/{book['id']}/page-photo", headers={**headers, "Content-Type": "application/octet-stream"}, content=body
    )


def test_a_page_photo_returns_text_and_highlights_but_stores_neither(client, db, monkeypatch):
    reader = AsyncMock(return_value=PAGE)
    monkeypatch.setattr(book_service, "read_page_photo", reader)
    db.table("user_vocabulary").insert(
        {"user_id": USER, "term": "cinta", "lemma": "cinta", "language": "es", "status": "known"}
    ).execute()
    book = make_book(client)

    response = photo(client, book)

    body = response.json()
    assert response.status_code == 200 and body["readable"]
    assert body["transcription"].startswith("Tenía las manos")
    assert {c["lemma"]: c["status"] for c in body["candidates"]} == {"atar": None, "estremecerse": None, "cinta": "known"}
    assert body["estimate"] == {"unknown_estimate": 2, "page_words": 10, "band": "comfortable"}
    assert reader.await_args.args[1:] == ("image/jpeg", "es", "B1")
    stored = str({name: rows for name, rows in db.tables.items() if name != "user_vocabulary"})
    assert "Tenía las manos" not in stored and "\\xff" not in stored
    assert [row["book_id"] for row in db.rows("page_photo_events")] == [book["id"]]


def test_a_page_photo_must_be_a_small_image(client, monkeypatch):
    reader = AsyncMock(return_value=PAGE)
    monkeypatch.setattr(book_service, "read_page_photo", reader)
    book = make_book(client)

    assert photo(client, book, body=b"not an image at all").status_code == 415
    assert photo(client, book, body=JPEG + b"0" * book_service.MAX_PHOTO_BYTES).status_code == 413
    assert photo(client, book, headers={"X-User-ID": OTHER}).status_code == 404
    reader.assert_not_awaited()


def test_a_failed_photo_still_counts_against_the_limit(client, db, monkeypatch):
    monkeypatch.setattr(book_service, "read_page_photo", AsyncMock(side_effect=GeminiError("ai_unavailable", "down")))
    book = make_book(client)

    response = photo(client, book)

    assert response.status_code == 503 and response.json()["detail"]["code"] == "ai_unavailable"
    assert len(db.rows("page_photo_events")) == 1


def test_an_unreadable_photo_says_so_and_still_counts(client, db, monkeypatch):
    blank = PageTranscription(readable=False, transcription="", candidates=[])
    monkeypatch.setattr(book_service, "read_page_photo", AsyncMock(return_value=blank))
    book = make_book(client)

    body = photo(client, book).json()

    assert body["readable"] is False and body["candidates"] == [] and body["estimate"] is None
    assert len(db.rows("page_photo_events")) == 1


def test_photos_are_rate_limited_per_learner(client, db, monkeypatch):
    monkeypatch.setattr(book_service, "read_page_photo", AsyncMock(return_value=PAGE))
    book = make_book(client)
    for _ in range(book_service.PHOTOS_PER_MINUTE):
        assert photo(client, book).status_code == 200

    limited = photo(client, book)

    assert limited.status_code == 429 and limited.json()["detail"]["code"] == "photo_rate_limited"
    assert len(db.rows("page_photo_events")) == book_service.PHOTOS_PER_MINUTE
    db.rows("page_photo_events").clear()
    monkeypatch.setattr(book_service, "PHOTOS_PER_MINUTE", 10_000)
    monkeypatch.setattr(book_service, "PHOTOS_PER_DAY", 2)
    assert photo(client, book).status_code == 200 and photo(client, book).status_code == 200
    assert photo(client, book).json()["detail"]["code"] == "photo_daily_limit"


def test_the_plus_quota_hook_defaults_to_allowed_and_can_refuse(client, monkeypatch):
    reader = AsyncMock(return_value=PAGE)
    monkeypatch.setattr(book_service, "read_page_photo", reader)
    book = make_book(client)
    assert book_service.page_photo_quota_allows(USER) is True

    monkeypatch.setattr(book_service, "page_photo_quota_allows", lambda _user_id: False)
    refused = photo(client, book)

    assert refused.status_code == 403 and refused.json()["detail"]["code"] == "photo_quota_reached"
    reader.assert_not_awaited()

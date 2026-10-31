"""The PostgREST requests behind the word bank, captured instead of sent."""

from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
from postgrest import SyncPostgrestClient

import database
from app.services import word_bank_service

USER = "00000000-0000-0000-0000-00000000000a"


class Capture:
    def __init__(self, rows=None):
        self.requests, self.rows = [], rows if rows is not None else []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=self.rows)

    def client(self) -> SyncPostgrestClient:
        return SyncPostgrestClient(
            "http://db.test/rest/v1", headers={}, http_client=httpx.Client(transport=httpx.MockTransport(self.handler))
        )

    def query(self, index=-1):
        return dict(parse_qsl(urlsplit(str(self.requests[index].url)).query))


@pytest.fixture
def capture(monkeypatch):
    seen = Capture()
    client = seen.client()
    monkeypatch.setattr(database, "create_supabase_client", lambda: client)
    monkeypatch.setattr(word_bank_service, "create_supabase_client", lambda: client)
    return seen


def test_lookup_cache_never_returns_an_encounter_that_only_records_a_use(capture):
    database.fetch_lookup_cache(USER, "es", "madrugué", "Ayer madrugué.", "l1")
    assert capture.query()["card"] == "not.is.null"
    assert capture.query()["card_status"] == "eq.ok"


def test_entry_encounters_are_read_and_deleted_by_owner_entry_kind_and_word(capture):
    kinds, words = ["used_ok", "used_error"], ["w1", "w2"]
    database.fetch_entry_encounters(USER, "e1", kinds, words)
    read = capture.query()
    assert (read["user_id"], read["source_type"], read["source_id"]) == (f"eq.{USER}", "eq.entry", "eq.e1")
    assert read["kind"] == "in.(used_ok,used_error)" and read["word_id"] == "in.(w1,w2)"

    database.delete_entry_encounters(USER, "e1", kinds, words)
    assert capture.requests[-1].method == "DELETE"
    assert capture.query()["user_id"] == f"eq.{USER}" and capture.query()["kind"] == "in.(used_ok,used_error)"

    database.delete_entry_encounters(USER, "e1", kinds)
    assert "word_id" not in capture.query()


def test_encounters_are_inserted_in_one_request_for_the_owner(capture):
    database.save_word_encounters([{"word_id": "w1", "kind": "used_ok"}, {"word_id": "w2", "kind": "used_error"}], USER)
    request = capture.requests[-1]
    assert request.method == "POST"
    body = httpx.Response(200, content=request.content).json()
    assert [row["user_id"] for row in body] == [USER, USER]
    assert database.save_word_encounters([], USER) == []
    assert len(capture.requests) == 1


def test_the_bank_reads_only_the_learners_offerable_words_in_one_language(capture):
    word_bank_service.load_notebook_words(USER, "es")
    query = capture.query()
    assert (query["user_id"], query["language"]) == (f"eq.{USER}", "eq.es")
    assert query["status"] == "in.(new,learning,known)"
    assert "card" in query["select"] and "created_at" in query["select"]


def test_signals_and_cards_are_read_in_chunks_so_a_big_notebook_fits_in_a_url(capture):
    ids = [f"w{i}" for i in range(250)]
    word_bank_service.load_word_signals(USER, ids)
    word_bank_service.load_recognition_cards_any(USER, ids)
    assert len(capture.requests) == 6
    assert all(len(capture.query(i)["word_id"].split(",")) <= 100 for i in range(6))
    assert all(capture.query(i)["user_id"] == f"eq.{USER}" for i in range(6))
    assert "suspended_at" not in capture.query(5)

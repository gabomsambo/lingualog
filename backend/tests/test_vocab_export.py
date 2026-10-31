"""CSV and Anki (.apkg) export with the sentence the word was met in and its source."""

import csv
import hashlib
import io
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import server
import vocab_export
from app.services import vocab_service

USER = "00000000-0000-0000-0000-00000000000a"
HEADERS = {"X-User-ID": USER}


def sample_rows():
    return [{
        "word_id": "w1", "word": "aprovechar", "language": "es",
        "meaning": "to make use of", "gloss": "make use of",
        "sentence": "Voy a aprovechar el día.", "source": "entry",
        "source_reference": "Journal entry · 2026-10-12", "status": "learning",
        "tags": ["travel"], "note": 'note, with "quotes"', "created_at": "2026-10-12T10:00:00+00:00",
        "surfaces": ["aprovechar"],
    }]


def open_apkg(payload: bytes):
    archive = zipfile.ZipFile(io.BytesIO(payload))
    handle, path = tempfile.mkstemp(suffix=".anki2")
    os.close(handle)
    with open(path, "wb") as sink:
        sink.write(archive.read("collection.anki2"))
    conn = sqlite3.connect(path)
    conn.execute("select 1")  # force the file open before it is cleaned up
    return archive, conn


# --- Pure builders ------------------------------------------------------------


def test_csv_keeps_sentence_source_and_quotes_messy_fields():
    text = vocab_export.rows_to_csv(sample_rows())
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == list(vocab_export.CSV_COLUMNS)
    assert rows[1][0] == "aprovechar"
    assert rows[1][4] == "Voy a aprovechar el día."
    assert rows[1][5] == "entry"
    assert rows[1][6] == "Journal entry · 2026-10-12"
    assert rows[1][9] == 'note, with "quotes"'
    assert rows[1][8] == "travel"


def test_sentence_highlight_marks_the_word_and_escapes_html():
    marked = vocab_export.highlight_sentence("Voy a aprovechar el día.", ["aprovechar"], "es")
    assert marked == "Voy a <b>aprovechar</b> el día."
    assert vocab_export.highlight_sentence("Sin la palabra.", ["aprovechar"], "es") == "Sin la palabra."
    assert vocab_export.highlight_sentence("hola <mundo>", ["mundo"], "es") == "hola &lt;<b>mundo</b>&gt;"
    assert vocab_export.highlight_sentence("", ["aprovechar"], "es") == ""


def test_apkg_holds_one_recognition_card_with_sentence_and_source():
    payload = vocab_export.rows_to_apkg(sample_rows())
    archive, conn = open_apkg(payload)
    assert sorted(archive.namelist()) == ["collection.anki2", "media"]
    assert archive.read("media") == b"{}"

    assert conn.execute("select ver from col").fetchone()[0] == 11
    decks = conn.execute("select decks from col").fetchone()[0]
    assert "LinguaLog::es" in decks
    models = conn.execute("select models from col").fetchone()[0]
    assert "LinguaLog Word" in models

    fields, sfld, checksum, tags = conn.execute(
        "select flds, sfld, csum, tags from notes"
    ).fetchone()
    assert fields.split("\x1f") == [
        "aprovechar",
        "Voy a <b>aprovechar</b> el día.",
        "to make use of",
        "make use of",
        "Journal entry · 2026-10-12",
    ]
    assert sfld == "aprovechar"
    assert checksum == int(hashlib.sha1(b"aprovechar").hexdigest()[:8], 16)
    assert " lang_es " in tags and " status_learning " in tags and " travel " in tags

    nid, did, due, card_type, queue = conn.execute(
        "select nid, did, due, type, queue from cards"
    ).fetchone()
    assert nid == conn.execute("select id from notes").fetchone()[0]
    assert str(did) in decks
    assert (due, card_type, queue) == (1, 0, 0)


def test_note_guid_is_stable_across_exports():
    first = open_apkg(vocab_export.rows_to_apkg(sample_rows()))[1]
    second = open_apkg(vocab_export.rows_to_apkg(sample_rows()))[1]
    assert first.execute("select guid from notes").fetchone() == \
        second.execute("select guid from notes").fetchone()


def test_empty_export_still_produces_a_valid_package():
    payload = vocab_export.rows_to_apkg([])
    archive, conn = open_apkg(payload)
    assert conn.execute("select count(*) from notes").fetchone()[0] == 0
    assert conn.execute("select count(*) from cards").fetchone()[0] == 0
    assert vocab_export.rows_to_csv([]).splitlines() == [",".join(vocab_export.CSV_COLUMNS)]


# --- Export rows --------------------------------------------------------------


def test_export_rows_pick_the_sentence_and_name_the_source(monkeypatch):
    monkeypatch.setattr(
        vocab_service, "load_words",
        lambda user_id, language=None: [
            {"id": "w1", "language": "es", "lemma": "mesa", "term": "mesa", "status": "new",
             "tags": [], "entry_id": "e1", "book_id": None, "note": "",
             "example_sentence": "", "created_at": "2026-10-01T09:00:00+00:00",
             "card": {"surface": "mesa", "sense_in_context": "table", "gloss_l1": "table"}},
            {"id": "w2", "language": "es", "lemma": "silla", "term": "silla", "status": "known",
             "tags": ["home"], "entry_id": None, "book_id": None, "note": "mine",
             "example_sentence": "La silla es azul.", "created_at": "2026-10-02T09:00:00+00:00",
             "card": {"surface": "silla", "sense_in_context": "chair", "gloss_l1": "chair"}},
            {"id": "w3", "language": "es", "lemma": "capítulo", "term": "capítulo", "status": "learning",
             "tags": [], "entry_id": None, "book_id": None, "note": "",
             "example_sentence": "", "created_at": "2026-10-03T09:00:00+00:00",
             "card": {"surface": "capítulo", "sense_in_context": "chapter", "gloss_l1": "chapter"}},
        ],
    )
    monkeypatch.setattr(
        vocab_service, "load_encounters",
        lambda user_id, language=None: [
            {"word_id": "w1", "sentence": "La mesa está lista.", "surface": "mesa",
             "kind": "lookup", "created_at": "2026-10-01T08:00:00+00:00"},
            {"word_id": "w3", "sentence": "Leí un capítulo entero.", "surface": "capítulo",
             "kind": "read", "book_id": "b1", "created_at": "2026-10-03T08:00:00+00:00"},
        ],
    )
    monkeypatch.setattr(
        vocab_service, "load_entry_summaries",
        lambda user_id, entry_ids: {"e1": {"id": "e1", "title": "Mi día", "created_at": "2026-10-01T09:00:00+00:00"}},
    )
    monkeypatch.setattr(vocab_service, "books_available", lambda: True)
    monkeypatch.setattr(vocab_service, "load_books", lambda user_id, book_ids: {"b1": {"id": "b1", "title": "El principito"}})

    rows = vocab_service.export_rows(USER, "es")
    assert rows[0]["sentence"] == "La mesa está lista."
    assert rows[0]["source"] == "entry"
    assert rows[0]["source_reference"] == "Journal entry · Mi día"
    assert rows[0]["surfaces"] == ["mesa"]
    assert rows[1]["sentence"] == "La silla es azul."
    assert rows[1]["source"] == "lookup"
    assert rows[1]["source_reference"] == "Lookup"
    assert rows[2]["sentence"] == "Leí un capítulo entero."
    assert rows[2]["source"] == "book"
    assert rows[2]["source_reference"] == "Book · El principito"


# --- The route ----------------------------------------------------------------


def test_export_route_downloads_csv_and_apkg(monkeypatch):
    monkeypatch.setattr(
        vocab_service, "export_rows", lambda user_id, language=None, selector=None: sample_rows()
    )
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.get("/vocabulary/export").status_code == 401

    response = client.get("/vocabulary/export?format=csv", headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "lingualog-vocabulary.csv" in response.headers["content-disposition"]
    assert response.text.splitlines()[1].startswith("aprovechar,")

    response = client.get("/vocabulary/export?format=apkg", headers=HEADERS)
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    assert "lingualog-vocabulary.apkg" in response.headers["content-disposition"]


def test_export_route_validates_the_selector(monkeypatch):
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.get("/vocabulary/export?list=someday", headers=HEADERS).status_code == 400

"""Export the word notebook as CSV or as an Anki deck (.apkg).

Pure builders: rows in, file bytes out, no database and no model calls. The Anki
package is the classic schema-11 `collection.anki2` plus an empty `media` file, the
same shape Anki's own importer accepts. Every card keeps the sentence the word was
met in and where it came from.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import tempfile
import time
import zipfile
from typing import Any, Iterable, Mapping, Sequence

from review_cards import find_form

CSV_COLUMNS = (
    "word",
    "language",
    "meaning",
    "gloss",
    "sentence",
    "source",
    "source_reference",
    "status",
    "tags",
    "note",
    "created_at",
)

DECK_PREFIX = "LinguaLog"
MODEL_NAME = "LinguaLog Word"
FIELD_NAMES = ("Word", "Sentence", "Meaning", "Gloss", "Source")
MEDIA_FILE = "media"
COLLECTION_FILE = "collection.anki2"

_QFMT = "{{#Sentence}}{{Sentence}}{{/Sentence}}{{^Sentence}}{{Word}}{{/Sentence}}"
_AFMT = (
    "{{FrontSide}}\n<hr id=answer>\n"
    '<div class="word">{{Word}}</div>\n'
    '<div class="meaning">{{Meaning}}{{#Gloss}} · {{Gloss}}{{/Gloss}}</div>\n'
    '{{#Source}}<div class="source">{{Source}}</div>{{/Source}}'
)
_CSS = (
    ".card { font-family: Georgia, serif; font-size: 18px; text-align: left; "
    "color: #1f2430; background: #ffffff; }\n"
    ".word { font-size: 24px; font-weight: 600; margin-bottom: 8px; }\n"
    ".meaning { margin-bottom: 8px; }\n"
    ".source { color: #6b7280; font-size: 13px; }\n"
    "b { color: #7c3aed; }"
)

FIELD_SQL = "\x1f"
_TAG_NOISE = re.compile(r"\s+")
_CHECKSUM_STRIP = re.compile(r"<[^>]+>")


def _csv_safe(value: Any) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def rows_to_csv(rows: Iterable[Mapping[str, Any]]) -> str:
    """RFC 4180 CSV of the exported words, one row per word."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([
            _csv_safe(row.get("word")),
            _csv_safe(row.get("language")),
            _csv_safe(row.get("meaning")),
            _csv_safe(row.get("gloss")),
            _csv_safe(row.get("sentence")),
            _csv_safe(row.get("source")),
            _csv_safe(row.get("source_reference")),
            _csv_safe(row.get("status")),
            _csv_safe("; ".join(row.get("tags") or [])),
            _csv_safe(row.get("note")),
            _csv_safe(row.get("created_at")),
        ])
    return buffer.getvalue()


def highlight_sentence(sentence: str, surfaces: Sequence[str], language: str) -> str:
    """The sentence as HTML with the word in bold. Falls back to the plain sentence."""
    if not sentence:
        return ""
    span = find_form(sentence, surfaces, language)
    if not span:
        return html.escape(sentence)
    start, end = span
    return (
        html.escape(sentence[:start])
        + "<b>" + html.escape(sentence[start:end]) + "</b>"
        + html.escape(sentence[end:])
    )


def _stable_id(name: str, floor: int = 2) -> int:
    return floor + int(hashlib.md5(name.encode("utf-8")).hexdigest()[:12], 16)


def _note_guid(row: Mapping[str, Any]) -> str:
    seed = row.get("word_id") or f"{row.get('language')}:{row.get('word')}:{row.get('sentence')}"
    return hashlib.md5(f"lingualog:{seed}".encode("utf-8")).hexdigest()[:16]


def _tags_text(row: Mapping[str, Any]) -> str:
    tags = [f"lang_{row.get('language') or 'xx'}", f"status_{row.get('status') or 'new'}"]
    tags += [_TAG_NOISE.sub("_", (tag or "").strip()) for tag in row.get("tags") or []]
    cleaned = [tag for tag in tags if tag and tag != "_"]
    return "".join(f" {tag} " for tag in dict.fromkeys(cleaned))


def _deck_name(language: str) -> str:
    return f"{DECK_PREFIX}::{language or 'other'}"


def _build_collection(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """One schema-11 collection holding every exported word as a recognition card."""
    now_ms = int(time.time() * 1000)
    now_s = now_ms // 1000
    model_id = _stable_id(f"model:{MODEL_NAME}")
    deck_ids = {_deck_name(str(row.get("language") or "")) for row in rows}
    deck_ids = {name: _stable_id(f"deck:{name}") for name in deck_ids} if deck_ids else {}

    model = {
        "id": model_id,
        "name": MODEL_NAME,
        "type": 0,
        "mod": now_s,
        "usn": -1,
        "sortf": 0,
        "did": next(iter(deck_ids.values()), _stable_id(f"deck:{DECK_PREFIX}")),
        "tmpls": [{
            "name": "Recognition",
            "ord": 0,
            "qfmt": _QFMT,
            "afmt": _AFMT,
            "did": None,
            "bqfmt": "",
            "bafmt": "",
            "bfont": "",
            "bsize": 12,
        }],
        "flds": [
            {"name": name, "ord": ord, "sticky": False, "rtl": False, "rtlWas": False,
             "font": "Arial", "size": 20, "media": []}
            for ord, name in enumerate(FIELD_NAMES)
        ],
        "css": _CSS,
        "latexPre": "\\documentclass[12pt]{article}\\begin{document}",
        "latexPost": "\\end{document}",
        "req": [[0, "any", [0]]],
        "tags": [],
        "vers": [],
    }
    default_deck = {
        "id": 1, "name": "Default", "mod": now_s, "usn": 0,
        "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0], "timeToday": [0, 0],
        "collapsed": False, "browserCollapsed": True, "desc": "", "dyn": 0, "conf": 1,
        "extendNew": 0, "extendRev": 0,
    }
    decks = {"1": default_deck}
    for name, deck_id in deck_ids.items():
        decks[str(deck_id)] = {
            **default_deck,
            "id": deck_id,
            "name": name,
            "desc": "Exported from LinguaLog",
        }
    dconf = {
        "1": {
            "id": 1, "name": "Default", "mod": 0, "usn": 0, "maxTaken": 60, "autoplay": True,
            "timer": 0, "replayq": True,
            "new": {"bury": True, "delays": [1, 10], "initialFactor": 2500, "ints": [1, 4, 0],
                    "order": 1, "perDay": 20, "separate": True},
            "rev": {"bury": True, "ease4": 1.3, "fuzz": 0.05, "ivlFct": 1, "maxIvl": 36500,
                    "minSpace": 1, "perDay": 200, "hardFactor": 1.2},
            "lapse": {"delays": [10], "leechAction": 0, "leechFails": 8, "minInt": 1, "mult": 0},
            "dyn": False,
        }
    }
    conf = {
        "nextPos": len(rows) + 1, "estTimes": True, "activeDecks": [1], "sortType": "noteFld",
        "timeLim": 0, "sortBackwards": False, "addToCur": True, "curDeck": 1, "newBury": True,
        "newSpread": 0, "dueCounts": True, "curModel": str(model_id), "collapseTime": 1200,
    }

    handle, path = tempfile.mkstemp(suffix=".anki2")
    os.close(handle)
    try:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT INTO col (id, crt, mod, scm, ver, dty, usn, ls, conf, models, decks, dconf, tags)"
                " VALUES (1, ?, ?, ?, 11, 0, 0, 0, ?, ?, ?, ?, '{}')",
                (now_s, now_ms, now_ms, json.dumps(conf), json.dumps({str(model_id): model}),
                 json.dumps(decks), json.dumps(dconf)),
            )
            for index, row in enumerate(rows):
                language = str(row.get("language") or "")
                fields = [
                    html.escape(str(row.get("word") or "")),
                    highlight_sentence(str(row.get("sentence") or ""), row.get("surfaces") or [], language),
                    html.escape(str(row.get("meaning") or "")),
                    html.escape(str(row.get("gloss") or "")),
                    html.escape(str(row.get("source_reference") or "")),
                ]
                note_id = now_ms + index * 2
                plain_first = _CHECKSUM_STRIP.sub("", fields[0]).strip()
                checksum = int(hashlib.sha1(plain_first.encode("utf-8")).hexdigest()[:8], 16)
                conn.execute(
                    "INSERT INTO notes (id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data)"
                    " VALUES (?, ?, ?, ?, -1, ?, ?, ?, ?, 0, '')",
                    (note_id, _note_guid(row), model_id, now_s, _tags_text(row),
                     FIELD_SQL.join(fields), fields[0], checksum),
                )
                conn.execute(
                    "INSERT INTO cards (id, nid, did, mod, usn, type, queue, due, ivl, factor,"
                    " reps, lapses, left, odue, odid, flags, data)"
                    " VALUES (?, ?, ?, ?, -1, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, '')",
                    (note_id + 1, note_id, deck_ids[_deck_name(language)], now_s, index + 1),
                )
            conn.commit()
        finally:
            conn.close()
        with open(path, "rb") as handle:
            return handle.read()
    finally:
        os.unlink(path)


_SCHEMA = """
CREATE TABLE col (id integer primary key, crt integer, mod integer, scm integer, ver integer,
  dty integer, usn integer, ls integer, conf text, models text, decks text, dconf text, tags text);
CREATE TABLE notes (id integer primary key, guid text, mid integer, mod integer, usn integer,
  tags text, flds text, sfld text, csum integer, flags integer, data text);
CREATE TABLE cards (id integer primary key, nid integer, did integer, mod integer, usn integer,
  type integer, queue integer, due integer, ivl integer, factor integer, reps integer,
  lapses integer, left integer, odue integer, odid integer, flags integer, data text);
CREATE TABLE revlog (id integer primary key, cid integer, usn integer, ease integer, ivl integer,
  lastIvl integer, factor integer, time integer, type integer);
CREATE TABLE graves (id integer primary key, nid integer, did integer, usn integer, type integer);
"""


def rows_to_apkg(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """An .apkg of the exported words: one recognition card per word, deck per language."""
    collection = _build_collection(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(COLLECTION_FILE, collection)
        archive.writestr(MEDIA_FILE, "{}")
    return buffer.getvalue()

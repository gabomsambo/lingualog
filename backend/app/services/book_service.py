"""Book mode: books, reading sessions, marks, end-of-session cards, glossary and progress.

A mark is a ``word_encounters`` row (kind ``read``, source ``book_session``), so reading shares
the "seen N times" count and the notebook with lookups. A mark has no card until the session
ends, when the cards are built in one batch. Nothing here stores book text beyond the sentence
of a marked word, and a page photo is only ever held in memory.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ai.gemini import GeminiError
from ai.page_photo import PageTranscription, read_page_photo
from ai.word_card import card_policy_snapshot, generate_word_card
from app.services import review_service
from book_coverage import (
    HAVE_STATUSES,
    RECURRING_MARKS,
    band_for,
    page_estimate,
    pages_read,
    stays_hard,
    words_per_page,
)
from database import (
    USER_VOCABULARY_TABLE,
    create_supabase_client,
    fetch_lookup_cache,
    fetch_vocabulary_item_by_term,
    link_word_encounters,
)
from learning_policy import resolve_policy

logger = logging.getLogger(__name__)

BOOKS_TABLE = "books"
SESSIONS_TABLE = "reading_sessions"
ENCOUNTERS_TABLE = "word_encounters"
PHOTO_EVENTS_TABLE = "page_photo_events"

CARD_BUILD_CONCURRENCY = 4
ID_CHUNK = 100
WRITING_WORDS_LIMIT = 12
# Page photo limits. Per learner, on top of the Plus quota hook below.
MAX_PHOTO_BYTES = 4 * 1024 * 1024
PHOTOS_PER_MINUTE = 6
PHOTOS_PER_DAY = 40
_EDGE_PUNCTUATION = " \t\n\r.,;:!?¿¡\"'«»“”‘’()[]{}—–-…*"


class BookNotFound(LookupError):
    """The book does not exist or belongs to someone else."""


class SessionNotFound(LookupError):
    """The reading session does not exist, or is not this book's, or belongs to someone else."""


class SessionClosed(RuntimeError):
    """The session has ended, so no more words can be marked in it."""


class PhotoRefused(RuntimeError):
    """A page photo was refused before any model call. ``code`` is safe to show the learner."""

    def __init__(self, code: str, status_code: int):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_word(text: str) -> str:
    """The form marks are grouped by: no edge punctuation, one space, casefolded."""
    return re.sub(r"\s+", " ", (text or "").strip(_EDGE_PUNCTUATION)).casefold()


def _table(name: str):
    return create_supabase_client().table(name)


def _chunks(values: list, size: int = ID_CHUNK):
    for start in range(0, len(values), size):
        yield values[start:start + size]


# --- Books -------------------------------------------------------------------


def get_book(user_id: str, book_id: str) -> dict:
    response = _table(BOOKS_TABLE).select("*").eq("id", book_id).eq("user_id", user_id).limit(1).execute()
    if not response.data:
        raise BookNotFound(book_id)
    return response.data[0]


def create_book(user_id: str, title: str, author: Optional[str], language: str) -> dict:
    review_service.validate_language(language)
    row = {"user_id": user_id, "title": title.strip(), "author": (author or "").strip() or None, "language": language}
    return _table(BOOKS_TABLE).insert(row).execute().data[0]


def update_book(user_id: str, book_id: str, changes: dict) -> dict:
    get_book(user_id, book_id)
    if not changes:
        return get_book(user_id, book_id)
    changes = {**changes, "updated_at": _now().isoformat()}
    response = _table(BOOKS_TABLE).update(changes).eq("id", book_id).eq("user_id", user_id).execute()
    if not response.data:
        raise BookNotFound(book_id)
    return response.data[0]


def delete_book(user_id: str, book_id: str) -> None:
    """Delete a book and its sessions. Marks that never became words go with it; saved words stay."""
    get_book(user_id, book_id)
    _table(ENCOUNTERS_TABLE).delete().eq("user_id", user_id).eq("book_id", book_id).is_("word_id", "null").execute()
    _table(BOOKS_TABLE).delete().eq("id", book_id).eq("user_id", user_id).execute()


def _sessions_for(user_id: str, book_ids: list[str]) -> list[dict]:
    rows: list[dict] = []
    for chunk in _chunks(book_ids):
        rows += (
            _table(SESSIONS_TABLE).select("*").eq("user_id", user_id).in_("book_id", chunk)
            .order("started_at").execute().data or []
        )
    return rows


def session_summary(session: dict, marks_so_far: Optional[int] = None) -> dict:
    marked = session["words_marked"] if session.get("ended_at") else (marks_so_far or 0)
    pages = session.get("pages_read")
    rate = words_per_page(marked, pages) if session.get("ended_at") else None
    return {
        "id": session["id"],
        "started_at": session["started_at"],
        "ended_at": session.get("ended_at"),
        "page_from": session.get("page_from"),
        "page_to": session.get("page_to"),
        "pages_read": pages,
        "words_marked": marked,
        "words_per_page": rate,
        "band": band_for(rate),
    }


def list_books(user_id: str, language: Optional[str] = None) -> list[dict]:
    query = _table(BOOKS_TABLE).select("*").eq("user_id", user_id)
    if language:
        query = query.eq("language", language)
    books = query.order("updated_at", desc=True).execute().data or []
    sessions = _sessions_for(user_id, [book["id"] for book in books])
    by_book: dict[str, list[dict]] = defaultdict(list)
    for session in sessions:
        by_book[session["book_id"]].append(session)
    result = []
    for book in books:
        own = by_book[book["id"]]
        ended = [session_summary(session) for session in own if session.get("ended_at")]
        open_session = next((session for session in own if not session.get("ended_at")), None)
        rates = [session["words_per_page"] for session in ended]
        result.append({
            **book,
            "sessions": len(ended),
            "words_marked": sum(session["words_marked"] for session in ended),
            "open_session_id": open_session["id"] if open_session else None,
            "rate_series": [rate for rate in rates if rate is not None],
            "last_band": band_for(next((rate for rate in reversed(rates) if rate is not None), None)),
        })
    return result


# --- Sessions and marks -------------------------------------------------------


def get_session(user_id: str, book_id: str, session_id: str) -> dict:
    response = (
        _table(SESSIONS_TABLE).select("*").eq("id", session_id).eq("book_id", book_id)
        .eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        raise SessionNotFound(session_id)
    return response.data[0]


def fetch_session_for_user(user_id: str, session_id: str) -> Optional[dict]:
    """A session by id alone, for lookups that only know the session."""
    response = _table(SESSIONS_TABLE).select("*").eq("id", session_id).eq("user_id", user_id).limit(1).execute()
    return response.data[0] if response.data else None


def get_open_session(user_id: str, book_id: str) -> Optional[dict]:
    response = (
        _table(SESSIONS_TABLE).select("*").eq("user_id", user_id).eq("book_id", book_id)
        .is_("ended_at", "null").limit(1).execute()
    )
    return response.data[0] if response.data else None


def open_session(user_id: str, book_id: str, page_from: Optional[int]) -> dict:
    """Start a session, or resume the book's open one."""
    get_book(user_id, book_id)
    existing = get_open_session(user_id, book_id)
    if existing:
        return existing
    try:
        row = {"user_id": user_id, "book_id": book_id, "page_from": page_from}
        return _table(SESSIONS_TABLE).insert(row).execute().data[0]
    except Exception:
        # A second tab won the race for the one open session.
        existing = get_open_session(user_id, book_id)
        if existing:
            return existing
        raise


def session_marks(user_id: str, session_id: str) -> list[dict]:
    return (
        _table(ENCOUNTERS_TABLE).select("*").eq("user_id", user_id).eq("source_id", session_id)
        .eq("source_type", "book_session").order("created_at").execute().data or []
    )


def book_marks(user_id: str, book_id: str) -> list[dict]:
    return (
        _table(ENCOUNTERS_TABLE).select("*").eq("user_id", user_id).eq("book_id", book_id)
        .eq("kind", "read").order("created_at").execute().data or []
    )


def _surface_lemmas(marks: list[dict]) -> dict[str, str]:
    """What each marked surface resolved to, so later marks of it join the same word."""
    return {
        normalize_word(mark["surface"]): mark["lemma"]
        for mark in marks
        if mark.get("card_status") == "ok" and mark.get("card")
    }


def _group_key(mark: dict, resolved: dict[str, str]) -> str:
    return resolved.get(normalize_word(mark["surface"]), mark["lemma"])


def _groups(marks: list[dict]) -> dict[str, list[dict]]:
    resolved = _surface_lemmas(marks)
    groups: dict[str, list[dict]] = defaultdict(list)
    for mark in marks:
        groups[_group_key(mark, resolved)].append(mark)
    return groups


def _latest_with_sentence(marks: list[dict]) -> dict:
    """The most recent mark that kept its sentence, else the most recent mark."""
    return next((mark for mark in reversed(marks) if mark.get("sentence")), marks[-1])


def find_mark(user_id: str, session_id: str, surface: str, page: Optional[int]) -> Optional[dict]:
    """The mark of this word on this page in this session, if the learner already made it."""
    wanted = normalize_word(surface)
    for mark in session_marks(user_id, session_id):
        if normalize_word(mark["surface"]) == wanted and mark.get("page") == page:
            return mark
    return None


def mark_view(mark: dict, times_marked: int) -> dict:
    return {
        "id": mark["id"],
        "surface": mark["surface"],
        "sentence": mark.get("sentence"),
        "page": mark.get("page"),
        "created_at": mark["created_at"],
        "times_marked": times_marked,
        "in_notebook": bool(mark.get("word_id")),
    }


def add_mark(user_id: str, book: dict, session: dict, word: str, sentence: Optional[str], page: Optional[int]) -> dict:
    """Mark a word without stopping. The same word on the same page is not marked twice."""
    if session.get("ended_at"):
        raise SessionClosed(session["id"])
    surface = word.strip(_EDGE_PUNCTUATION) or word.strip()
    existing_marks = book_marks(user_id, book["id"])
    resolved = _surface_lemmas(existing_marks)
    lemma = resolved.get(normalize_word(surface), normalize_word(surface))
    duplicate = next(
        (
            mark for mark in existing_marks
            if mark.get("source_id") == session["id"]
            and normalize_word(mark["surface"]) == normalize_word(surface)
            and mark.get("page") == page
        ),
        None,
    )
    if duplicate:
        mark, created = duplicate, False
    else:
        saved = fetch_vocabulary_item_by_term(user_id, lemma, book["language"])
        row = {
            "user_id": user_id,
            "word_id": saved["id"] if saved else None,
            "language": book["language"],
            "lemma": lemma,
            "surface": surface,
            "sentence": (sentence or "").strip() or None,
            "kind": "read",
            "source_type": "book_session",
            "source_id": session["id"],
            "book_id": book["id"],
            "page": page,
            "card_status": "pending",
        }
        mark, created = _table(ENCOUNTERS_TABLE).insert(row).execute().data[0], True
        existing_marks.append(mark)
    times = len(_groups(existing_marks).get(_group_key(mark, _surface_lemmas(existing_marks)), [mark]))
    return {**mark_view(mark, times), "created": created}


def book_detail(user_id: str, book_id: str) -> dict:
    """The book and its open session, if any, with the session's marks newest first."""
    book = get_book(user_id, book_id)
    session = get_open_session(user_id, book_id)
    if not session:
        return {"book": book, "session": None}
    marks = session_marks(user_id, session["id"])
    all_marks = book_marks(user_id, book_id)
    resolved = _surface_lemmas(all_marks)
    groups = _groups(all_marks)
    view = [mark_view(mark, len(groups[_group_key(mark, resolved)])) for mark in reversed(marks)]
    return {"book": book, "session": {**session_summary(session, len(marks)), "marks": view}}


def remove_mark(user_id: str, book_id: str, session_id: str, mark_id: str) -> bool:
    session = get_session(user_id, book_id, session_id)
    if session.get("ended_at"):
        raise SessionClosed(session_id)
    response = (
        _table(ENCOUNTERS_TABLE).delete().eq("id", mark_id).eq("user_id", user_id)
        .eq("source_id", session_id).eq("kind", "read").execute()
    )
    return bool(response.data)


_CARD_FIELDS = ("lemma", "sense", "card", "card_policy", "card_status", "word_id")


def record_book_lookup(
    user_id: str, session: dict, surface: str, page: Optional[int], encounter: dict
) -> dict:
    """Store a lookup made from a session. A mark already made of this word on this page gets the card."""
    book_fields = {"book_id": session["book_id"], "page": page}
    existing = find_mark(user_id, session["id"], surface, page)
    if existing and not existing.get("card"):
        changes = {key: value for key, value in encounter.items() if key in _CARD_FIELDS}
        if not existing.get("sentence"):
            changes["sentence"] = encounter.get("sentence")
        updated = _table(ENCOUNTERS_TABLE).update(changes).eq("id", existing["id"]).eq("user_id", user_id).execute()
        return updated.data[0]
    return _table(ENCOUNTERS_TABLE).insert({**encounter, **book_fields, "user_id": user_id}).execute().data[0]


def end_session(user_id: str, book_id: str, session_id: str, page_to: Optional[int]) -> dict:
    """Close a session and fix its counts. The page range widens to cover every marked page."""
    session = get_session(user_id, book_id, session_id)
    if session.get("ended_at"):
        return session_summary(session)
    marks = session_marks(user_id, session_id)
    pages = [mark["page"] for mark in marks if mark.get("page")]
    ends_from = [value for value in [session.get("page_from"), *pages] if value]
    ends_to = [value for value in [page_to, *pages] if value]
    page_from_final = min(ends_from) if ends_from else None
    page_to_final = max(ends_to) if ends_to else None
    changes = {
        "ended_at": _now().isoformat(),
        "page_from": page_from_final,
        "page_to": page_to_final,
        "words_marked": len(marks),
        "pages_read": pages_read(page_from_final, page_to_final),
    }
    updated = (
        _table(SESSIONS_TABLE).update(changes).eq("id", session_id).eq("user_id", user_id)
        .is_("ended_at", "null").execute()
    )
    _table(BOOKS_TABLE).update({"updated_at": _now().isoformat()}).eq("id", book_id).eq("user_id", user_id).execute()
    return session_summary(updated.data[0] if updated.data else {**session, **changes})


# --- End of session: cards, triage --------------------------------------------


def _update_marks(user_id: str, mark_ids: list[str], changes: dict) -> None:
    for chunk in _chunks(mark_ids):
        _table(ENCOUNTERS_TABLE).update(changes).eq("user_id", user_id).in_("id", chunk).execute()


async def _build_group_card(user_id: str, book: dict, policy, snapshot: dict, group: list[dict]) -> bool:
    """Build one card for a group of marks of the same word. False when the model failed."""
    latest = _latest_with_sentence(group)
    sentence = latest.get("sentence") or latest["surface"]
    cached = fetch_lookup_cache(user_id, book["language"], latest["surface"], sentence, snapshot.get("vocab_def"))
    if cached and cached.get("card"):
        fields = {
            "lemma": cached.get("lemma") or latest["lemma"],
            "sense": cached.get("sense"),
            "card": cached["card"],
            "card_policy": cached.get("card_policy") or snapshot,
            "card_status": "ok",
        }
    else:
        try:
            card = await generate_word_card(latest["surface"], sentence, policy)
        except GeminiError as exc:
            logger.error("Book card failed (%s): %s", exc.code, exc.message)
            _update_marks(user_id, [mark["id"] for mark in group], {"card_status": "failed"})
            return False
        fields = {
            "lemma": card.lemma,
            "sense": card.sense_in_context,
            "card": card.model_dump(by_alias=True),
            "card_policy": snapshot,
            "card_status": "ok",
        }
    saved = fetch_vocabulary_item_by_term(user_id, fields["lemma"], book["language"])
    if saved:
        fields["word_id"] = saved["id"]
    _update_marks(user_id, [mark["id"] for mark in group if mark.get("card_status") != "ok"], fields)
    return True


async def build_session_cards(user_id: str, book: dict, session_id: str) -> dict:
    """Build the cards for this session's marks that have none, then return the triage."""
    marks = session_marks(user_id, session_id)
    pending: dict[str, list[dict]] = defaultdict(list)
    for mark in marks:
        if mark.get("word_id") or mark.get("card_status") == "ok":
            continue
        pending[normalize_word(mark["surface"])].append(mark)
    failed = 0
    if pending:
        policy = resolve_policy(user_id, book["language"])
        snapshot = card_policy_snapshot(policy)
        gate = asyncio.Semaphore(CARD_BUILD_CONCURRENCY)

        async def build(group: list[dict]) -> bool:
            async with gate:
                return await _build_group_card(user_id, book, policy, snapshot, group)

        results = await asyncio.gather(*(build(group) for group in pending.values()))
        failed = results.count(False)
    triage_view = triage(user_id, book["id"], session_id)
    triage_view["failed"] = failed
    return triage_view


def triage(user_id: str, book_id: str, session_id: str) -> dict:
    """The session's unresolved words: recurring first, one-offs after, each with its card."""
    session_rows = session_marks(user_id, session_id)
    all_marks = book_marks(user_id, book_id)
    groups = _groups(all_marks)
    in_session = {mark["id"] for mark in session_rows}
    items = []
    for key, group in groups.items():
        open_marks = [
            mark for mark in group
            if mark["id"] in in_session and not mark.get("word_id") and not mark.get("resolution")
        ]
        if not open_marks:
            continue
        with_card = next((mark for mark in reversed(group) if mark.get("card_status") == "ok" and mark.get("card")), None)
        latest = _latest_with_sentence(open_marks)
        items.append({
            "key": key,
            "lemma": with_card["lemma"] if with_card else key,
            "surface": latest["surface"],
            "sentence": latest.get("sentence"),
            "page": latest.get("page"),
            "times_marked": len(group),
            "recurring": len(group) >= RECURRING_MARKS,
            "card": with_card["card"] if with_card else None,
            "card_status": "ok" if with_card else ("failed" if latest.get("card_status") == "failed" else "pending"),
            "encounter_id": with_card["id"] if with_card else None,
            "encounter_ids": [mark["id"] for mark in open_marks],
        })
    items.sort(key=lambda item: (not item["recurring"], -item["times_marked"], item["lemma"]))
    return {"items": items, "recurring": sum(1 for item in items if item["recurring"])}


def skip_marks(user_id: str, book_id: str, mark_ids: list[str]) -> int:
    """"Skip for now": the marks stay in the glossary but leave the end-of-session choice."""
    owned = 0
    for chunk in _chunks(mark_ids):
        response = (
            _table(ENCOUNTERS_TABLE).update({"resolution": "skipped"}).eq("user_id", user_id)
            .eq("book_id", book_id).is_("word_id", "null").in_("id", chunk).execute()
        )
        owned += len(response.data or [])
    return owned


# --- Glossary, progress, writing ----------------------------------------------


def _notebook_words(user_id: str, marks: list[dict]) -> dict[str, dict]:
    return review_service.load_words(user_id, sorted({mark["word_id"] for mark in marks if mark.get("word_id")}))


def glossary(user_id: str, book_id: str) -> dict:
    """Every word marked in the book with its sentences and pages: the index card in the cover."""
    book = get_book(user_id, book_id)
    marks = book_marks(user_id, book_id)
    words = _notebook_words(user_id, marks)
    entries = []
    for key, group in _groups(marks).items():
        with_card = next((mark for mark in reversed(group) if mark.get("card_status") == "ok" and mark.get("card")), None)
        saved = next((words[mark["word_id"]] for mark in group if mark.get("word_id") in words), None)
        card = (saved or {}).get("card") or (with_card or {}).get("card") or {}
        sentences = []
        for mark in reversed(group):
            if mark.get("sentence") and all(mark["sentence"] != seen["sentence"] for seen in sentences):
                sentences.append({"sentence": mark["sentence"], "page": mark.get("page")})
        entries.append({
            "key": key,
            "lemma": (saved or {}).get("lemma") or (with_card or {}).get("lemma") or key,
            "surfaces": sorted({mark["surface"] for mark in group}, key=str.casefold),
            "times_marked": len(group),
            "pages": sorted({mark["page"] for mark in group if mark.get("page")}),
            "sentences": sentences[:3],
            "meaning": card.get("sense_in_context") or "",
            "gloss": card.get("gloss_l1") or "",
            "has_card": bool(card),
            "status": (saved or {}).get("status"),
            "skipped": all(mark.get("resolution") == "skipped" for mark in group if not mark.get("word_id")) and not saved,
        })
    entries.sort(key=lambda entry: (min(entry["pages"]) if entry["pages"] else 10**9, entry["lemma"].casefold()))
    return {"book": book, "words": entries}


def progress(user_id: str, book_id: str) -> dict:
    """Words per page, session by session, and the marks on each page, as soft-banded estimates."""
    book = get_book(user_id, book_id)
    sessions = _sessions_for(user_id, [book_id])
    ended = [session_summary(session) for session in sessions if session.get("ended_at")]
    rates = [session["words_per_page"] for session in ended]
    known_rates = [rate for rate in rates if rate is not None]
    per_page: dict[int, set[str]] = defaultdict(set)
    marks = book_marks(user_id, book_id)
    resolved = _surface_lemmas(marks)
    for mark in marks:
        if mark.get("page"):
            per_page[mark["page"]].add(_group_key(mark, resolved))
    if len(known_rates) < 2:
        trend = None
    elif known_rates[-1] < known_rates[0]:
        trend = "falling"
    elif known_rates[-1] > known_rates[0]:
        trend = "rising"
    else:
        trend = "flat"
    return {
        "book": book,
        "sessions": ended,
        "pages": [
            {"page": page, "words": len(words), "band": band_for(len(words))}
            for page, words in sorted(per_page.items())
        ],
        "trend": trend,
        "latest_band": band_for(known_rates[-1]) if known_rates else None,
        "stays_hard": stays_hard(rates),
        "estimate": True,
    }


def writing_words(user_id: str, book_id: str, days: int = 7) -> dict:
    """This week's book words, saved ones first, to pre-fill "write about what you read"."""
    book = get_book(user_id, book_id)
    since = (_now() - timedelta(days=days)).isoformat()
    marks = [mark for mark in book_marks(user_id, book_id) if mark["created_at"] >= since]
    words = _notebook_words(user_id, marks)
    chosen = []
    for key, group in _groups(marks).items():
        saved = next((words[mark["word_id"]] for mark in group if mark.get("word_id") in words), None)
        if saved and saved.get("status") in HAVE_STATUSES:
            continue
        with_card = next((mark for mark in reversed(group) if mark.get("card")), None)
        card = (saved or {}).get("card") or (with_card or {}).get("card") or {}
        chosen.append({
            "lemma": (saved or {}).get("lemma") or (with_card or {}).get("lemma") or key,
            "surface": group[-1]["surface"],
            "gloss": card.get("gloss_l1") or card.get("sense_in_context") or "",
            "status": (saved or {}).get("status"),
            "times_marked": len(group),
        })
    chosen.sort(key=lambda word: (word["status"] is None, -word["times_marked"], word["lemma"].casefold()))
    return {"book": {"id": book["id"], "title": book["title"], "language": book["language"]},
            "words": chosen[:WRITING_WORDS_LIMIT]}


# --- Page photos ----------------------------------------------------------------


def page_photo_quota_allows(user_id: str) -> bool:
    """The one hook for a page-photo quota. Plus-tier gating plugs in here; today every learner is allowed."""
    return True


def sniff_image(data: bytes) -> Optional[str]:
    """The mime type of a JPEG, PNG or WebP image from its leading bytes, else None."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _photo_events_since(user_id: str, since: datetime) -> int:
    response = (
        _table(PHOTO_EVENTS_TABLE).select("id", count="exact").eq("user_id", user_id)
        .gte("created_at", since.isoformat()).execute()
    )
    return response.count or len(response.data or [])


def reserve_photo(user_id: str, book_id: str) -> str:
    """Check the limits and log the photo before the model call. Returns the event id."""
    if not page_photo_quota_allows(user_id):
        raise PhotoRefused("photo_quota_reached", 403)
    now = _now()
    if _photo_events_since(user_id, now - timedelta(minutes=1)) >= PHOTOS_PER_MINUTE:
        raise PhotoRefused("photo_rate_limited", 429)
    if _photo_events_since(user_id, now.replace(hour=0, minute=0, second=0, microsecond=0)) >= PHOTOS_PER_DAY:
        raise PhotoRefused("photo_daily_limit", 429)
    return _table(PHOTO_EVENTS_TABLE).insert({"user_id": user_id, "book_id": book_id}).execute().data[0]["id"]


def release_photo(user_id: str, event_id: str) -> None:
    """A photo the model could not read does not count against the learner."""
    _table(PHOTO_EVENTS_TABLE).delete().eq("id", event_id).eq("user_id", user_id).execute()


def notebook_statuses(user_id: str, language: str, lemmas: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in _chunks(sorted(set(lemmas))):
        rows = (
            _table(USER_VOCABULARY_TABLE).select("lemma, status").eq("user_id", user_id)
            .eq("language", language).in_("lemma", chunk).execute().data or []
        )
        result.update({row["lemma"]: row["status"] for row in rows})
    return result


async def read_page(user_id: str, book: dict, image: bytes, mime_type: str) -> dict:
    """Transcribe a photographed page and pre-highlight the words worth marking.

    The image and the transcription are returned to the caller and stored nowhere.
    """
    event_id = reserve_photo(user_id, book["id"])
    try:
        policy = resolve_policy(user_id, book["language"])
        page: PageTranscription = await read_page_photo(image, mime_type, book["language"], policy.proficiency)
    except GeminiError:
        release_photo(user_id, event_id)
        raise
    if not page.readable or not page.transcription.strip():
        release_photo(user_id, event_id)
        return {"readable": False, "transcription": "", "candidates": [], "estimate": None}
    statuses = notebook_statuses(user_id, book["language"], [word.lemma for word in page.candidates])
    candidates = [
        {"surface": word.surface, "lemma": word.lemma, "status": statuses.get(word.lemma)}
        for word in page.candidates
    ]
    page_words = len(re.findall(r"\w+", page.transcription))
    estimate = page_estimate([candidate["status"] for candidate in candidates], page_words)
    return {"readable": True, "transcription": page.transcription, "candidates": candidates, "estimate": estimate}

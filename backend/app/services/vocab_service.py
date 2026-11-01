"""The word notebook's data layer: lists, filters, export rows and placement results.

Everything here reads the V1-V3 tables and computes in plain code. The notebook's lists
are tags plus the smart lists (due, never used, by entry, by book); the by-book list
only appears once the V5 books table exists. No model calls.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from database import (
    USER_VOCABULARY_TABLE,
    create_supabase_client,
    fetch_all_rows,
    list_language_profiles,
    save_language_placement,
)
from placement import estimate_size, has_samples, matching_words, sample_words
from review_scheduler import DEFAULT_DAILY_NEW_WORDS, aware, waiting_cards

CARDS_TABLE = "vocab_cards"
LOGS_TABLE = "vocab_review_logs"
PARAMS_TABLE = "user_fsrs_params"
ENCOUNTERS_TABLE = "word_encounters"
ENTRIES_TABLE = "journal_entries"
BOOKS_TABLE = "books"

# How a word was used in the learner's own writing (V4 refines these with correctness).
USE_KINDS = ("entry_text", "used_ok", "used_error")
SMART_LISTS = ("due", "never_used")
SOURCES = ("entry", "book", "lookup", "class_note")
STATUSES = ("new", "learning", "known", "mastered", "ignored")

ENCOUNTER_FIELDS = "id, word_id, kind, surface, sentence, source_type, source_id, page, book_id, created_at"
CARD_FIELDS = "id, word_id, language, card_type, state, step, stability, difficulty, due, last_review, reps, lapses, suspended_at, created_at, first_reviewed_at"
LOG_FIELDS = "card_id, rating, reviewed_at, duration_ms, source"
WORD_FIELDS = "*"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Loading -----------------------------------------------------------------


def load_words(user_id: str, language: Optional[str] = None) -> List[dict]:
    query = (
        create_supabase_client().table(USER_VOCABULARY_TABLE).select(WORD_FIELDS).eq("user_id", user_id)
    )
    if language:
        query = query.eq("language", language)
    return fetch_all_rows(query)


def load_encounters(user_id: str, language: Optional[str] = None) -> List[dict]:
    query = (
        create_supabase_client().table(ENCOUNTERS_TABLE).select(ENCOUNTER_FIELDS).eq("user_id", user_id)
    )
    if language:
        query = query.eq("language", language)
    return fetch_all_rows(query)


def load_cards(user_id: str, language: Optional[str] = None) -> List[dict]:
    query = create_supabase_client().table(CARDS_TABLE).select(CARD_FIELDS).eq("user_id", user_id)
    if language:
        query = query.eq("language", language)
    return fetch_all_rows(query)


def load_review_logs(user_id: str, language: Optional[str] = None) -> List[dict]:
    query = create_supabase_client().table(LOGS_TABLE).select(LOG_FIELDS).eq("user_id", user_id)
    if language:
        query = query.eq("language", language)
    return fetch_all_rows(query)


def load_fsrs_parameters(user_id: str) -> List[dict]:
    query = create_supabase_client().table(PARAMS_TABLE).select("l2, parameters").eq("user_id", user_id)
    return fetch_all_rows(query)


def load_profiles(user_id: str) -> List[dict]:
    return list_language_profiles(user_id)


def count_entries_since(user_id: str, since: datetime) -> int:
    response = (
        create_supabase_client().table(ENTRIES_TABLE)
        .select("id", count="exact").eq("user_id", user_id).gte("created_at", since.isoformat())
        .execute()
    )
    return response.count or len(response.data or [])


def load_entry_summaries(user_id: str, entry_ids: Sequence[str]) -> Dict[str, dict]:
    ids = [str(entry_id) for entry_id in entry_ids if entry_id]
    if not ids:
        return {}
    rows: List[dict] = []
    for start in range(0, len(ids), 100):
        response = (
            create_supabase_client().table(ENTRIES_TABLE)
            .select("id, title, created_at").eq("user_id", user_id).in_("id", ids[start:start + 100])
            .execute()
        )
        rows += response.data or []
    return {row["id"]: row for row in rows}


def books_available() -> bool:
    """Whether V5's books table exists yet. The by-book list is gated on this."""
    try:
        create_supabase_client().table(BOOKS_TABLE).select("id").limit(1).execute()
        return True
    except Exception:
        return False


def load_books(user_id: str, book_ids: Sequence[str]) -> Dict[str, dict]:
    ids = [str(book_id) for book_id in book_ids if book_id]
    if not ids or not books_available():
        return {}
    rows: List[dict] = []
    for start in range(0, len(ids), 100):
        response = (
            create_supabase_client().table(BOOKS_TABLE)
            .select("id, title").eq("user_id", user_id).in_("id", ids[start:start + 100])
            .execute()
        )
        rows += response.data or []
    return {row["id"]: row for row in rows}


def placement_available(language: Optional[str]) -> bool:
    return bool(language) and has_samples(language)


def save_placement(user_id: str, language: str, result: Dict[str, Any]) -> bool:
    return save_language_placement(user_id, language, result)


# --- Selection ---------------------------------------------------------------


def selector_from(
    list_id: Optional[str] = None,
    tag: Optional[str] = None,
    entry_id: Optional[str] = None,
    book_id: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, str]:
    """Validate and normalize the list/filter query parameters. Raises ValueError."""
    selector: Dict[str, str] = {}
    if list_id:
        if list_id not in SMART_LISTS:
            raise ValueError(f"list must be one of {', '.join(SMART_LISTS)}")
        selector["list"] = list_id
    if tag:
        selector["tag"] = tag.strip()
    if entry_id:
        selector["entry_id"] = str(entry_id)
    if book_id:
        selector["book_id"] = str(book_id)
    if status:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        selector["status"] = status
    if source:
        if source not in SOURCES:
            raise ValueError(f"source must be one of {', '.join(SOURCES)}")
        selector["source"] = source
    return selector


def book_of_word(encounters: Sequence[Mapping[str, Any]]) -> Dict[Any, str]:
    """The book each word was met in. Books live on reading encounters, not on the word."""
    books: Dict[Any, str] = {}
    for encounter in sorted(encounters, key=lambda row: str(row.get("created_at") or "")):
        word_id = encounter.get("word_id")
        book_id = encounter.get("book_id")
        if word_id and book_id and word_id not in books:
            books[word_id] = str(book_id)
    return books


def source_of(
    word: Mapping[str, Any],
    books: Optional[Mapping[Any, str]] = None,
    encounters: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Where the word came from: a book, an entry, a class note, or a lookup."""
    if any(
        row.get("word_id") == word.get("id") and row.get("source_type") == "class_note"
        for row in encounters
    ):
        return "class_note"
    if word.get("book_id") or (books or {}).get(word.get("id")):
        return "book"
    if word.get("entry_id"):
        return "entry"
    return "lookup"


def _due_word_ids(
    cards: Sequence[Mapping[str, Any]], now: datetime, profiles: Sequence[Mapping[str, Any]] = ()
) -> set:
    """Words with a card the review queue deals today, honouring each language's daily new-word limit."""
    limits = {
        row.get("l2"): int(row.get("daily_new_words") or DEFAULT_DAILY_NEW_WORDS)
        for row in profiles if row.get("l2")
    }
    return {card.get("word_id") for card in waiting_cards(cards, now, limits)}


def _used_word_ids(encounters: Sequence[Mapping[str, Any]]) -> set:
    return {
        encounter.get("word_id") for encounter in encounters
        if encounter.get("word_id") and encounter.get("kind") in USE_KINDS
    }


def filter_items(
    items: Sequence[Mapping[str, Any]],
    encounters: Sequence[Mapping[str, Any]],
    cards: Sequence[Mapping[str, Any]],
    selector: Mapping[str, str],
    now: Optional[datetime] = None,
    profiles: Sequence[Mapping[str, Any]] = (),
) -> List[dict]:
    """Apply the list and filter selectors to notebook rows."""
    now = now or _now()
    books = book_of_word(encounters)
    selected: Iterable[Mapping[str, Any]] = list(items)
    if selector.get("status"):
        selected = [word for word in selected if word.get("status") == selector["status"]]
    if selector.get("tag"):
        selected = [word for word in selected if selector["tag"] in (word.get("tags") or [])]
    if selector.get("entry_id"):
        selected = [word for word in selected if str(word.get("entry_id") or "") == selector["entry_id"]]
    if selector.get("book_id"):
        selected = [
            word for word in selected
            if str(word.get("book_id") or books.get(word.get("id")) or "") == selector["book_id"]
        ]
    if selector.get("source"):
        selected = [word for word in selected if source_of(word, books, encounters) == selector["source"]]
    if selector.get("list") == "due":
        due_ids = _due_word_ids(cards, now, profiles)
        selected = [word for word in selected if word.get("id") in due_ids]
    elif selector.get("list") == "never_used":
        used = _used_word_ids(encounters)
        selected = [word for word in selected if word.get("id") not in used]
    return scrub_example_sentences(selected)


def fetch_items(
    user_id: str, language: Optional[str] = None, selector: Optional[Mapping[str, str]] = None
) -> List[dict]:
    words = load_words(user_id, language)
    if not selector:
        return scrub_example_sentences(words)
    return filter_items(
        words, load_encounters(user_id, language), load_cards(user_id, language), selector,
        profiles=load_profiles(user_id) if selector.get("list") == "due" else (),
    )


# --- Lists -------------------------------------------------------------------


def get_lists(
    user_id: str, language: Optional[str] = None, now: Optional[datetime] = None
) -> Dict[str, Any]:
    """The notebook's lists with counts: smart lists, tags, per-entry and per-book."""
    words = load_words(user_id, language)
    encounters = load_encounters(user_id, language)
    cards = load_cards(user_id, language)
    now = now or _now()

    due = _due_word_ids(cards, now, load_profiles(user_id))
    used = _used_word_ids(encounters)
    books_by_word = book_of_word(encounters)

    tags: Counter = Counter()
    entries: Counter = Counter()
    books: Counter = Counter()
    for word in words:
        for tag in word.get("tags") or []:
            tags[tag] += 1
        if word.get("entry_id"):
            entries[str(word["entry_id"])] += 1
        book_id = word.get("book_id") or books_by_word.get(word.get("id"))
        if book_id:
            books[str(book_id)] += 1

    entry_rows = load_entry_summaries(user_id, list(entries))
    book_rows = load_books(user_id, list(books))

    def entry_item(entry_id: str) -> Dict[str, Any]:
        row = entry_rows.get(entry_id) or {}
        return {
            "id": f"entry:{entry_id}",
            "entry_id": entry_id,
            "title": row.get("title"),
            "date": (row.get("created_at") or "")[:10] or None,
            "count": entries[entry_id],
        }

    def book_item(book_id: str) -> Dict[str, Any]:
        row = book_rows.get(book_id) or {}
        return {
            "id": f"book:{book_id}",
            "book_id": book_id,
            "title": row.get("title"),
            "count": books[book_id],
        }

    return {
        "total": len(words),
        "smart": [
            {"id": "due", "count": len(due & {word.get("id") for word in words})},
            {"id": "never_used", "count": len([word for word in words if word.get("id") not in used])},
        ],
        "tags": [
            {"id": f"tag:{tag}", "name": tag, "count": count}
            for tag, count in sorted(tags.items())
        ],
        "entries": sorted(
            (entry_item(entry_id) for entry_id in entries),
            key=lambda item: item.get("date") or "",
            reverse=True,
        ),
        "books": [book_item(book_id) for book_id in sorted(books)] if books_available() else None,
    }


# --- Export rows -------------------------------------------------------------


def _bare_sentence(text: Optional[str], word: Mapping[str, Any]) -> bool:
    """A sentence that is just the word itself: the top-search save left no context."""
    value = (text or "").strip()
    if not value:
        return True
    card = word.get("card") or {}
    forms = (word.get("term"), word.get("lemma"), card.get("surface"))
    return value.casefold() in {str(form).strip().casefold() for form in forms if form and str(form).strip()}


def scrub_example_sentences(items: Sequence[Mapping[str, Any]]) -> List[dict]:
    """Rows whose saved sentence is just the word itself keep no quote to show."""
    rows = []
    for word in items:
        row = dict(word)
        if _bare_sentence(row.get("example_sentence"), word):
            row["example_sentence"] = ""
        rows.append(row)
    return rows


def _first_sentence(word: Mapping[str, Any], encounters: Sequence[Mapping[str, Any]]) -> str:
    if not _bare_sentence(word.get("example_sentence"), word):
        return (word.get("example_sentence") or "").strip()
    for encounter in sorted(encounters, key=lambda row: str(row.get("created_at") or "")):
        text = (encounter.get("sentence") or "").strip()
        if text and text != (encounter.get("surface") or "").strip() and not _bare_sentence(text, word):
            return text
    return ""


def export_rows(
    user_id: str, language: Optional[str] = None, selector: Optional[Mapping[str, str]] = None
) -> List[dict]:
    """Every exported word with its sentence and where it came from."""
    words = fetch_items(user_id, language, selector)
    encounters = load_encounters(user_id, language)
    by_word: Dict[Any, List[dict]] = defaultdict(list)
    for encounter in encounters:
        if encounter.get("word_id"):
            by_word[encounter["word_id"]].append(encounter)
    books_by_word = book_of_word(encounters)

    entry_rows = load_entry_summaries(user_id, [word.get("entry_id") for word in words])
    book_rows = load_books(user_id, [books_by_word.get(word.get("id")) or word.get("book_id") for word in words])

    rows = []
    for word in words:
        card = word.get("card") or {}
        word_encounters = by_word.get(word.get("id"), [])
        book_id = books_by_word.get(word.get("id")) or word.get("book_id")
        source = source_of(word, books_by_word, word_encounters)
        reference = ""
        if source == "entry":
            entry = entry_rows.get(str(word.get("entry_id") or "")) or {}
            label = entry.get("title") or (entry.get("created_at") or "")[:10]
            reference = f"Journal entry · {label}" if label else "Journal entry"
        elif source == "book":
            book = book_rows.get(str(book_id or "")) or {}
            reference = f"Book · {book.get('title')}" if book.get("title") else "Book"
        elif source == "class_note":
            reference = "Class note"
        else:
            reference = "Lookup"

        surfaces = []
        for form in (
            card.get("surface"),
            word.get("term"),
            word.get("lemma"),
            *(encounter.get("surface") for encounter in word_encounters),
        ):
            if form and form.strip() and form.strip() not in surfaces:
                surfaces.append(form.strip())
        rows.append({
            "word_id": word.get("id"),
            "word": word.get("lemma") or word.get("term") or "",
            "language": word.get("language") or "",
            "meaning": card.get("sense_in_context") or word.get("sense") or word.get("definition") or "",
            "gloss": card.get("gloss_l1") or "",
            "sentence": _first_sentence(word, word_encounters),
            "source": source,
            "source_reference": reference,
            "status": word.get("status") or "new",
            "tags": list(word.get("tags") or []),
            "note": word.get("note") or "",
            "created_at": word.get("created_at") or "",
            "surfaces": surfaces,
        })
    return rows


# --- Placement ---------------------------------------------------------------


def placement_result(language: str, known: Iterable[str]) -> Dict[str, Any]:
    """The stored shape of one placement check: an estimate, never a score."""
    tapped = matching_words(language, known)
    return {
        "v": 1,
        "estimate": estimate_size(language, tapped),
        "sample_size": len(sample_words(language)),
        "known": tapped,
        "checked_at": _now().isoformat(),
    }

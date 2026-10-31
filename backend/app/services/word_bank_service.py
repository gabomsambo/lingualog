"""The word bank beside the editor, and what an entry's uses of those words do to the notebook.

Offering the bank makes no model calls. After an entry is analysed, the tutor's checked
``target_word_uses`` become encounters in the learner's own writing (``used_ok`` / ``used_error``),
a correct use of a word whose text stayed hidden earns a "Got it" on its production card, and a
word that is Known and was used correctly on two different days becomes Mastered.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

from app.services import book_service, review_service
from database import (
    USER_VOCABULARY_TABLE,
    create_supabase_client,
    delete_entry_encounters,
    fetch_entry_encounters,
    save_word_encounters,
    update_vocabulary_item,
)
from learning_policy import is_same_language, resolve_policy
from review_scheduler import schedule_review
from word_bank import (
    DEFAULT_BANK_SIZE,
    ENCOUNTER_KIND_FOR_STATUS,
    ENCOUNTER_USED_OK,
    MAX_TARGET_WORDS,
    USE_ENCOUNTER_KINDS,
    USED_CORRECTLY,
    BankWord,
    bank_hint,
    is_mastered,
    pick_bank,
    surface_forms,
    use_days,
)

logger = logging.getLogger(__name__)

CHALLENGE_SOURCE = "challenge_use"
STATUS_MASTERED = "mastered"
NOTEBOOK_COLUMNS = "id, user_id, language, lemma, term, sense, status, card, card_status, created_at"
_OFFERED_STATUSES = ("new", "learning", "known")
# A surface longer than this is a pasted sentence from a manual lookup, not a form of the word.
_MAX_SURFACE_WORDS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- The bank ------------------------------------------------------------------


def load_notebook_words(user_id: str, language: str) -> list[dict]:
    response = (
        create_supabase_client().table(USER_VOCABULARY_TABLE).select(NOTEBOOK_COLUMNS)
        .eq("user_id", user_id).eq("language", language).in_("status", list(_OFFERED_STATUSES))
        .execute()
    )
    return response.data or []


def _chunks(values: Sequence[str]) -> Iterable[list[str]]:
    size = review_service.WORD_ID_CHUNK
    for start in range(0, len(values), size):
        yield list(values[start:start + size])


def load_recognition_cards_any(user_id: str, word_ids: Sequence[str]) -> list[dict]:
    """Recognition cards whether or not they are suspended: a Known word's stability still counts."""
    cards: list[dict] = []
    for chunk in _chunks(word_ids):
        response = (
            create_supabase_client().table(review_service.CARDS_TABLE).select("*")
            .eq("user_id", user_id).eq("card_type", review_service.RECOGNITION).in_("word_id", chunk).execute()
        )
        cards += response.data or []
    return cards


def load_word_signals(user_id: str, word_ids: Sequence[str]) -> list[dict]:
    """The encounters the bank ranks by: forms met and uses in the learner's entries."""
    rows: list[dict] = []
    for chunk in _chunks(word_ids):
        response = (
            create_supabase_client().table("word_encounters").select("word_id, surface, kind, created_at, source_type, source_id")
            .eq("user_id", user_id).in_("word_id", chunk).execute()
        )
        rows += response.data or []
    uses = [row for row in rows if row["kind"] in USE_ENCOUNTER_KINDS]
    orphaned = {id(row) for row in uses} - {id(row) for row in review_service.drop_orphaned_uses(user_id, uses)}
    return [row for row in rows if id(row) not in orphaned]


def _forms_met(signals: Iterable[Mapping[str, Any]]) -> list[str]:
    forms: list[str] = []
    for signal in signals:
        surface = (signal.get("surface") or "").strip()
        if surface and len(surface.split()) <= _MAX_SURFACE_WORDS:
            forms.append(surface)
    return forms


def get_bank(
    user_id: str,
    language: str,
    count: int = DEFAULT_BANK_SIZE,
    exclude: Iterable[str] = (),
    now: Optional[datetime] = None,
    book_id: Optional[str] = None,
) -> dict[str, Any]:
    """Five or six of the learner's words to write with today, each with why it was chosen.

    With ``book_id`` (writing about what was read), this week's words from that book come first.
    """
    review_service.validate_language(language)
    now = now or _now()
    book = prefer = None
    if book_id:
        book = book_service.get_book(user_id, book_id)
        if not is_same_language(book["language"], language):
            raise ValueError("The book is in another language")
        prefer = book_service.recent_book_word_ids(user_id, book_id)
    words = load_notebook_words(user_id, language)
    ids = [word["id"] for word in words]
    cards = {card["word_id"]: card for card in load_recognition_cards_any(user_id, ids)}
    signals: dict[str, list[dict]] = {}
    for signal in load_word_signals(user_id, ids):
        signals.setdefault(signal["word_id"], []).append(signal)

    items = []
    for word in words:
        met = signals.get(word["id"], [])
        used = [s for s in met if s["kind"] in USE_ENCOUNTER_KINDS]
        correct_dates = [s["created_at"] for s in met if s["kind"] == ENCOUNTER_USED_OK]
        stamps = [review_service.aware(s["created_at"]) for s in used]
        items.append(BankWord(
            word=word,
            card=cards.get(word["id"]),
            surfaces=surface_forms(word, _forms_met(met)),
            use_days=use_days(correct_dates),
            used_ever=bool(used),
            last_used=max(stamps) if stamps else None,
        ))

    scheduler = review_service.scheduler_for(user_id, language)
    quiz = resolve_policy(user_id, language).quiz
    chosen = pick_bank(items, now, scheduler, count, exclude, prefer or ())
    payload = []
    for item, reason in chosen:
        hint, hint_mode = bank_hint(item.word, quiz)
        payload.append({
            "word_id": item.word["id"],
            "lemma": item.word.get("lemma") or item.word.get("term") or "",
            "term": item.word.get("term") or item.word.get("lemma") or "",
            "status": item.word.get("status"),
            "reason": reason,
            "forms": list(item.surfaces),
            "hint": hint,
            "hint_mode": hint_mode,
            "use_days": item.use_days,
        })
    return {
        "language": language,
        "words": payload,
        "book": {"id": book["id"], "title": book["title"]} if book else None,
    }


# --- Target words of one entry ---------------------------------------------------


def load_target_words(user_id: str, language: str, word_ids: Sequence[str]) -> list[dict]:
    """The learner's own words behind the ids the editor sent, in the order chosen.

    An id that is not the caller's, belongs to another language or is ignored is silently
    dropped: the client's list is a request, never a source of word text.
    """
    wanted = list(dict.fromkeys(str(word_id) for word_id in word_ids))[:MAX_TARGET_WORDS]
    if not wanted:
        return []
    found = review_service.load_words(user_id, wanted)
    signals: dict[str, list[dict]] = {}
    for signal in load_word_signals(user_id, list(found)):
        signals.setdefault(signal["word_id"], []).append(signal)
    targets = []
    for word_id in wanted:
        word = found.get(word_id)
        if not word or word.get("status") == "ignored" or not is_same_language(word.get("language"), language):
            continue
        targets.append({
            "word_id": word_id,
            "lemma": word.get("lemma") or word.get("term") or "",
            "term": word.get("term") or word.get("lemma") or "",
            "forms": list(surface_forms(word, _forms_met(signals.get(word_id, [])))),
        })
    return targets


# --- Recording uses -----------------------------------------------------------------


def credit_challenge_use(user_id: str, word: Mapping[str, Any], now: datetime) -> bool:
    """A correct use of a word whose text stayed hidden is real productive recall: a "Got it".

    Only the production card is credited, and only once it exists. Writing a word the bank
    displayed is copying, and rating that would corrupt the memory model.
    """
    card = review_service.load_production_card(user_id, word["id"])
    if not card or card.get("suspended_at"):
        return False
    scheduler = review_service.scheduler_for(user_id, word["language"])
    outcome = schedule_review(card, "got_it", now, scheduler)
    updated = review_service.apply_card_review(
        user_id, card["id"], int(card.get("reps") or 0), outcome.card, {**outcome.log, "source": CHALLENGE_SOURCE}
    )
    return bool(updated)


def record_uses(
    user_id: str,
    entry_id: str,
    uses: Sequence[Mapping[str, Any]],
    challenge_ids: Iterable[str] = (),
    entry_created_at: Optional[str] = None,
    now: Optional[datetime] = None,
    replace_word_ids: Iterable[str] = (),
) -> dict[str, dict[str, Any]]:
    """Turn checked uses into encounters, an FSRS credit and a Mastered promotion.

    Re-analysing an entry replaces what it recorded before, so evidence never doubles, and a
    word already credited for this entry is not credited again. Returns the outcome per word.
    """
    now = now or _now()
    challenge = {str(word_id) for word_id in challenge_ids}
    word_ids = list(dict.fromkeys(
        [*(str(word_id) for word_id in replace_word_ids), *(use["word_id"] for use in uses)]
    ))
    if not word_ids:
        return {}
    kinds = list(USE_ENCOUNTER_KINDS)
    credited_before = {
        row["word_id"] for row in fetch_entry_encounters(user_id, entry_id, kinds, word_ids)
        if row["kind"] == ENCOUNTER_USED_OK
    }
    delete_entry_encounters(user_id, entry_id, kinds, word_ids)

    words = review_service.load_words(user_id, word_ids)
    rows = []
    for use in uses:
        kind = ENCOUNTER_KIND_FOR_STATUS.get(use["status"])
        word = words.get(use["word_id"])
        if not kind or not word:
            continue
        row = {
            "word_id": word["id"],
            "language": word["language"],
            "lemma": word.get("lemma") or word.get("term") or use["term"],
            "sense": word.get("sense") or None,
            "surface": use["form_in_text"],
            "sentence": use["sentence"] or None,
            "kind": kind,
            "source_type": "entry",
            "source_id": entry_id,
        }
        if entry_created_at:
            row["created_at"] = entry_created_at
        rows.append(row)
    save_word_encounters(rows, user_id)

    outcomes: dict[str, dict[str, Any]] = {}
    for use in uses:
        word = words.get(use["word_id"])
        if not word or use["status"] != USED_CORRECTLY:
            continue
        status = word.get("status")
        days = review_service.load_use_days(user_id, word["id"])
        recognition = review_service.load_recognition_card(user_id, word["id"])
        became_mastered = is_mastered(status, (recognition or {}).get("stability"), days)
        if became_mastered:
            update_vocabulary_item(word["id"], user_id, {"status": STATUS_MASTERED})
            status = STATUS_MASTERED
        credited = word["id"] in challenge and word["id"] not in credited_before and credit_challenge_use(
            user_id, word, now
        )
        outcomes[word["id"]] = {
            "word_status": status,
            "became_mastered": became_mastered,
            "use_days": days,
            "credited": credited,
        }
    return outcomes


def clear_entry_uses(user_id: str, entry_id: str) -> None:
    """Remove every use an entry recorded, e.g. when the entry is deleted or moves language."""
    delete_entry_encounters(user_id, entry_id, list(USE_ENCOUNTER_KINDS))

"""The word bank: which of the learner's words to offer beside the editor, and what a use is worth.

Pure functions, no database and no model calls. The bank offers a handful of words (due or
at-risk Learning words first, then recently saved words never used, then Known words that still
need a second day of use). After an entry, the tutor's ``target_word_uses`` are checked against
the entry text before anything is kept, and Mastered is decided here: the recognition card is
Known (stability of KNOWN_STABILITY_DAYS) and the word was used correctly in the learner's own
entries on MASTERED_USE_DAYS different days.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Sequence

from app.services.entry_translation_service import split_sentences
from review_cards import GLOSS_ON_TAP, GLOSS_SHOWN, find_form, normalize_answer
from review_scheduler import KNOWN_STABILITY_DAYS, aware, is_at_risk, is_due, retrievability

DEFAULT_BANK_SIZE = 6
MAX_BANK_SIZE = 8
MAX_TARGET_WORDS = 8
MAX_SURFACE_FORMS = 8
MASTERED_USE_DAYS = 2

USED_CORRECTLY = "used_correctly"
USED_WITH_ERROR = "used_with_error"
NOT_USED = "not_used"
UNCLEAR = "unclear"

# word_encounters.kind written for a use of a bank word in the learner's own entry.
ENCOUNTER_USED_OK = "used_ok"
ENCOUNTER_USED_ERROR = "used_error"
USE_ENCOUNTER_KINDS = (ENCOUNTER_USED_OK, ENCOUNTER_USED_ERROR)
ENCOUNTER_KIND_FOR_STATUS = {USED_CORRECTLY: ENCOUNTER_USED_OK, USED_WITH_ERROR: ENCOUNTER_USED_ERROR}

REASON_AT_RISK = "at_risk"
REASON_DUE = "due"
REASON_NEVER_USED = "never_used"
REASON_TO_MASTER = "to_master"
REASON_FROM_BOOK = "from_book"

# Statuses a word can be in and still be offered. Mastered and ignored words are done.
_OFFERED = frozenset({"new", "learning", "known"})
# Statuses from which writing evidence can promote a word to Mastered.
_PROMOTABLE = frozenset({"learning", "known"})


@dataclass(frozen=True)
class BankWord:
    """A notebook word with what the bank needs to rank it."""

    word: Mapping[str, Any]
    card: Optional[Mapping[str, Any]]
    surfaces: tuple[str, ...]
    use_days: int
    used_ever: bool
    last_used: Optional[datetime]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def use_days(created_at_values: Iterable[Any]) -> int:
    """Distinct UTC calendar days among the timestamps of correct uses."""
    days = {aware(value).date() for value in created_at_values if aware(value) is not None}
    return len(days)


def is_mastered(status: Optional[str], recognition_stability: Optional[float], days_used: int) -> bool:
    """Known by the scheduler and used correctly in the learner's own entries on enough days."""
    return (
        status in _PROMOTABLE
        and recognition_stability is not None
        and recognition_stability >= KNOWN_STABILITY_DAYS
        and days_used >= MASTERED_USE_DAYS
    )


def surface_forms(word: Mapping[str, Any], surfaces: Iterable[str] = ()) -> tuple[str, ...]:
    """The forms the learner can be expected to write: the lemma, the saved term and forms already met."""
    card = word.get("card") or {}
    seen: list[str] = []
    for form in (word.get("lemma"), word.get("term"), card.get("surface"), *surfaces):
        text = (form or "").strip()
        if text and text.lower() not in (s.lower() for s in seen):
            seen.append(text)
    return tuple(seen[:MAX_SURFACE_FORMS])


def bank_hint(word: Mapping[str, Any], quiz: str) -> tuple[str, str]:
    """The meaning a bank chip carries and whether it is shown outright or behind a tap.

    The same ``quiz`` flag that decides review decides this: the learner's-language gloss is
    open for the first levels, behind a tap at the balanced level, and at full immersion the
    target-language meaning stays behind a tap.
    """
    card = word.get("card") or {}
    meaning = card.get("sense_in_context") or word.get("sense") or ""
    gloss = card.get("gloss_l1") or ""
    if quiz in GLOSS_SHOWN:
        return gloss or meaning, "shown"
    if quiz in GLOSS_ON_TAP:
        return gloss or meaning, "tap"
    return meaning, "tap"


def _rank(item: BankWord, now: datetime, scheduler: Any) -> Optional[tuple[int, tuple, str]]:
    word, card = item.word, item.card
    status = word.get("status")
    if status not in _OFFERED:
        return None
    if (
        status == "learning"
        and card
        and card.get("reps")
        and card.get("suspended_at") is None
        and is_due(card, now)
    ):
        at_risk = is_at_risk(card, now, scheduler)
        return 0, (0 if at_risk else 1, retrievability(card, now, scheduler)), (
            REASON_AT_RISK if at_risk else REASON_DUE
        )
    if status in ("new", "learning") and not item.used_ever:
        saved = aware(word.get("created_at")) or now
        return 1, (-saved.timestamp(),), REASON_NEVER_USED
    if (
        status == "known"
        and card
        and (card.get("stability") or 0) >= KNOWN_STABILITY_DAYS
        and item.use_days < MASTERED_USE_DAYS
    ):
        last = item.last_used.timestamp() if item.last_used else 0.0
        return 2, (item.use_days, last), REASON_TO_MASTER
    return None


def pick_bank(
    items: Sequence[BankWord],
    now: datetime,
    scheduler: Any,
    count: int = DEFAULT_BANK_SIZE,
    exclude: Iterable[str] = (),
    prefer: Iterable[str] = (),
) -> list[tuple[BankWord, str]]:
    """The words to offer, each with why: the learner's own due words come before fresh ones.

    ``prefer`` names words to write about first, e.g. this week's words from the book being read.
    """
    skipped = {str(word_id) for word_id in exclude}
    wanted = {str(word_id) for word_id in prefer}
    ranked = []
    for item in items:
        if str(item.word["id"]) in skipped:
            continue
        rank = _rank(item, now, scheduler)
        if str(item.word["id"]) in wanted and item.word.get("status") in _OFFERED:
            rank = (-1, (0,), REASON_FROM_BOOK)
        if rank:
            ranked.append((rank[0], rank[1], str(item.word["id"]), rank[2], item))
    ranked.sort(key=lambda row: row[:3])
    return [(row[4], row[3]) for row in ranked[: max(0, min(count, MAX_BANK_SIZE))]]


def sentence_containing(text: str, form: str, language: str) -> str:
    """The sentence of ``text`` that holds ``form``, or the form alone when none is found."""
    for sentence in split_sentences(text):
        if find_form(_nfc(sentence), [_nfc(form)], language):
            return sentence.strip()
    return form


def clean_target_word_uses(
    raw_uses: Iterable[Any],
    targets: Sequence[Mapping[str, Any]],
    entry_text: str,
    language: str,
) -> list[dict[str, Any]]:
    """Keep only the tutor's claims the entry can back up, one per requested word, in request order.

    A claim about a word that was not requested, a second claim about the same word, and a use
    the learner did not actually write are dropped, never stored. An unclear use stays a question:
    it is neither credited nor counted as an error.
    """
    by_name: dict[str, Mapping[str, Any]] = {}
    for target in targets:
        for name in (target.get("lemma"), target.get("term"), *(target.get("forms") or ())):
            if name:
                by_name.setdefault(normalize_answer(name), target)
    text = _nfc(entry_text)
    kept: dict[str, dict[str, Any]] = {}
    for raw in raw_uses:
        data = raw if isinstance(raw, Mapping) else raw.model_dump()
        target = by_name.get(normalize_answer(data.get("term") or ""))
        if target is None or target["word_id"] in kept:
            continue
        status = data.get("status")
        form = (data.get("form_in_text") or "").strip()
        written = bool(form) and bool(find_form(text, [_nfc(form)], language))
        if status in (USED_CORRECTLY, USED_WITH_ERROR) and not written:
            continue
        if status == NOT_USED or not written:
            form = ""
        kept[target["word_id"]] = {
            "word_id": target["word_id"],
            "term": target.get("term") or target.get("lemma") or "",
            "status": status,
            "form_in_text": form,
            "fix": (data.get("fix") or "").strip() if status == USED_WITH_ERROR else "",
            "note": (data.get("note") or "").strip() if status in (USED_WITH_ERROR, UNCLEAR) else "",
            "sentence": sentence_containing(entry_text, form, language) if form else "",
        }
    return [kept[target["word_id"]] for target in targets if target["word_id"] in kept]


def summarize_uses(uses: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """The counts behind "3 used well, 1 to fix, 1 not used"."""
    counts = {USED_CORRECTLY: 0, USED_WITH_ERROR: 0, NOT_USED: 0, UNCLEAR: 0}
    for use in uses:
        if use.get("status") in counts:
            counts[use["status"]] += 1
    return counts

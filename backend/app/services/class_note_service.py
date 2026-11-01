"""Pasted class-note extraction, confirmation, and notebook encounters."""

from __future__ import annotations

import logging
from datetime import datetime, time, timezone
from typing import Any, Optional

from ai.class_note import (
    MAX_CLASS_NOTE_CHARS,
    MAX_CLASS_NOTE_PHRASES,
    MAX_CLASS_NOTE_TASKS,
    MAX_CLASS_NOTE_WORDS,
    extract_class_note,
)
from ai.word_card import card_policy_snapshot
from database import (
    create_supabase_client,
    fetch_vocabulary_item_by_term,
    save_word_encounter,
)
from learning_policy import resolve_policy

logger = logging.getLogger(__name__)

CLASS_NOTES_TABLE = "class_notes"
JOURNAL_ENTRIES_TABLE = "journal_entries"
WORD_ENCOUNTERS_TABLE = "word_encounters"
CLASS_NOTES_PER_DAY = 10
CLASS_NOTE_ENCOUNTER_KIND = "lookup"


class ClassNoteNotFound(LookupError):
    """The class note does not exist or belongs to another learner."""


class ClassNoteRefused(RuntimeError):
    """A class note was refused before an extraction call."""

    def __init__(self, code: str, status_code: int):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def _table(name: str):
    return create_supabase_client().table(name)


def _day_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def class_note_quota_allows(user_id: str) -> bool:
    """The Plus quota hook. Product-tier gating can replace this default allow rule."""
    return True


def _notes_today(user_id: str) -> int:
    response = (
        _table(CLASS_NOTES_TABLE).select("id", count="exact").eq("user_id", user_id)
        .gte("created_at", _day_start().isoformat()).execute()
    )
    return response.count or len(response.data or [])


def _class_note(user_id: str, note_id: str) -> dict:
    response = (
        _table(CLASS_NOTES_TABLE).select("*").eq("id", note_id).eq("user_id", user_id)
        .maybe_single().execute()
    )
    if not response.data:
        raise ClassNoteNotFound(note_id)
    return response.data


def _class_note_words(user_id: str, note: dict) -> list[dict]:
    extracted = note.get("extracted") or {}
    terms = extracted.get("words") or []
    if not terms:
        return []
    encounters = (
        _table(WORD_ENCOUNTERS_TABLE).select("id, word_id, lemma, surface")
        .eq("user_id", user_id).eq("source_type", "class_note").eq("source_id", note["id"])
        .execute().data or []
    )
    by_lemma = {row.get("lemma", "").casefold(): row for row in encounters}
    return [
        {
            **word,
            "word_id": (by_lemma.get((word.get("lemma") or word.get("term") or "").casefold()) or {}).get("word_id"),
            "encounter_id": (by_lemma.get((word.get("lemma") or word.get("term") or "").casefold()) or {}).get("id"),
        }
        for word in terms
    ]


def get_class_note(user_id: str, note_id: str) -> dict:
    note = _class_note(user_id, note_id)
    return {**note, "extracted": {**(note.get("extracted") or {}), "words": _class_note_words(user_id, note)}}


def get_waiting_class_note(user_id: str, language: str) -> Optional[dict]:
    """Return the newest class note for this language that has no linked journal entry."""
    notes = (
        _table(CLASS_NOTES_TABLE).select("*").eq("user_id", user_id).eq("l2", language)
        .order("created_at", desc=True).limit(50).execute().data or []
    )
    if not notes:
        return None
    note_ids = [note["id"] for note in notes]
    attached = (
        _table(JOURNAL_ENTRIES_TABLE).select("class_note_id").eq("user_id", user_id)
        .in_("class_note_id", note_ids).execute().data or []
    )
    attached_ids = {row.get("class_note_id") for row in attached}
    for note in notes:
        if note["id"] not in attached_ids:
            return {
                **note,
                "extracted": {**(note.get("extracted") or {}), "words": _class_note_words(user_id, note)},
            }
    return None


async def create_class_note(user_id: str, language: str, raw_text: str) -> dict:
    text = raw_text.strip()
    if not text:
        raise ValueError("Paste some class material first")
    if len(text) > MAX_CLASS_NOTE_CHARS:
        raise ValueError(f"Pasted text must be {MAX_CLASS_NOTE_CHARS} characters or fewer")
    if not class_note_quota_allows(user_id):
        raise ClassNoteRefused("class_note_quota_reached", 403)
    if _notes_today(user_id) >= CLASS_NOTES_PER_DAY:
        raise ClassNoteRefused("class_note_daily_limit", 429)

    policy = resolve_policy(user_id, language)
    extracted = await extract_class_note(text, language, policy.proficiency)
    row = _table(CLASS_NOTES_TABLE).insert({
        "user_id": user_id,
        "l2": language,
        "raw_text": text,
        "source": "paste",
        "extracted": extracted,
    }).execute().data
    if not row:
        raise RuntimeError("Class note was not saved")
    return row[0]


def _normalize_confirmed(extracted: dict) -> dict:
    words = []
    seen = set()
    for item in extracted.get("words") or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "").strip()[:100]
        lemma = str(item.get("lemma") or term).strip()[:100]
        if not term or not lemma or lemma.casefold() in seen:
            continue
        seen.add(lemma.casefold())
        words.append({
            "term": term,
            "lemma": lemma,
            "gloss": str(item.get("gloss") or "").strip()[:300],
            "part_of_speech": str(item.get("part_of_speech") or "").strip()[:40],
            "example": str(item.get("example") or "").strip()[:500],
            "reading": str(item.get("reading") or "").strip()[:100],
        })
        if len(words) >= MAX_CLASS_NOTE_WORDS:
            break

    phrases = []
    seen_phrases = set()
    for phrase in extracted.get("phrases") or []:
        value = str(phrase or "").strip()[:160]
        if value and value.casefold() not in seen_phrases:
            seen_phrases.add(value.casefold())
            phrases.append(value)
        if len(phrases) >= MAX_CLASS_NOTE_PHRASES:
            break

    tasks = [
        task for task in (extracted.get("tasks") or [])
        if isinstance(task, dict) and str(task.get("prompt") or "").strip()
    ][:MAX_CLASS_NOTE_TASKS]
    return {
        **extracted,
        "words": words,
        "grammar_focus": str(extracted.get("grammar_focus") or "").strip()[:200] or None,
        "phrases": phrases,
        "tasks": tasks,
    }


def _card_for_word(word: dict, policy) -> dict:
    example = word.get("example") or word["term"]
    return {
        "lemma": word["lemma"],
        "surface": word["term"],
        "is_phrase": len(word["term"].split()) > 1,
        "part_of_speech": word.get("part_of_speech") or "",
        "gender": "",
        "sense_in_context": word.get("gloss") or "",
        "gloss_l1": word.get("gloss") or "" if policy.vocab_def in ("l1", "l1_plus_l2") else "",
        "other_senses": [],
        "register": "neutral",
        "cefr": policy.proficiency,
        "frequency_band": "top3k",
        "examples": [example],
        "example_translations": [],
        "collocations": [],
        "word_family": [],
        "common_mistake": "",
        "memory_hook": "",
    }


def _prepare_class_note_encounters(user_id: str, note: dict, extracted: dict) -> None:
    policy = resolve_policy(user_id, note["l2"])
    snapshot = card_policy_snapshot(policy)
    existing_encounters = (
        _table(WORD_ENCOUNTERS_TABLE).select("id, lemma")
        .eq("user_id", user_id).eq("source_type", "class_note").eq("source_id", note["id"])
        .execute().data or []
    )
    encounter_ids = {row.get("lemma", "").casefold(): row["id"] for row in existing_encounters}

    for word in extracted["words"]:
        lemma = word["lemma"]
        existing = fetch_vocabulary_item_by_term(user_id, lemma, note["l2"])
        data = {
            "word_id": existing.get("id") if existing else None,
            "language": note["l2"],
            "lemma": lemma,
            "sense": word.get("gloss") or None,
            "surface": word["term"],
            "sentence": word.get("example") or word["term"],
            "kind": CLASS_NOTE_ENCOUNTER_KIND,
            "source_type": "class_note",
            "source_id": note["id"],
            "card": _card_for_word(word, policy),
            "card_policy": snapshot,
            "card_status": "ok",
        }
        old_id = encounter_ids.get(lemma.casefold())
        if old_id:
            _table(WORD_ENCOUNTERS_TABLE).update(data).eq("id", old_id).eq("user_id", user_id).execute()
        else:
            save_word_encounter(data, user_id)


def confirm_class_note(user_id: str, note_id: str, submitted: dict) -> dict:
    note = _class_note(user_id, note_id)
    linked = (
        _table(JOURNAL_ENTRIES_TABLE).select("id").eq("user_id", user_id)
        .eq("class_note_id", note_id).limit(1).execute().data or []
    )
    if linked:
        raise ClassNoteRefused("class_note_already_used", 409)
    extracted = _normalize_confirmed(submitted)
    response = (
        _table(CLASS_NOTES_TABLE).update({"extracted": extracted})
        .eq("id", note_id).eq("user_id", user_id).execute()
    )
    if not response.data:
        raise ClassNoteNotFound(note_id)
    _prepare_class_note_encounters(user_id, note, extracted)
    return get_class_note(user_id, note_id)


__all__ = [
    "CLASS_NOTES_PER_DAY",
    "ClassNoteNotFound",
    "ClassNoteRefused",
    "class_note_quota_allows",
    "confirm_class_note",
    "create_class_note",
    "get_class_note",
    "get_waiting_class_note",
]

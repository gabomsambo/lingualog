"""Curated Spanish refresher offers and sentence drills, with no model calls."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.entry_translation_service import split_sentences
from review_cards import Candidate, corrected_sentence, find_form, split_around

LESSONS_FILE = Path(__file__).resolve().parents[2] / "content" / "lessons" / "es.json"
OFFER_THRESHOLD = 2
RECENT_ENTRY_WINDOW = 5
DRILL_ENTRY_WINDOW = 50
SNOOZE_DAYS = 7
OFFER_COOLDOWN_DAYS = 7
SEEN_COOLDOWN_DAYS = 30
LESSON_OFFERS_TABLE = "lesson_offers"
SPANISH_CODE = re.compile(r"^es(?:-[A-Z]{2})?$", re.IGNORECASE)
_LESSON_DATA = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
_LESSONS = _LESSON_DATA["lessons"]
_LESSONS_BY_TAG: dict[str, list[dict[str, Any]]] = {}
for _lesson in _LESSONS:
    _LESSONS_BY_TAG.setdefault(_lesson["tag"], []).append(_lesson)
SUPPORTED_TAGS = frozenset(_LESSONS_BY_TAG)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _table(db: Any, name: str):
    return db.table(name)


def _entry_rows(db: Any, user_id: str, l2: str, limit: int) -> list[dict[str, Any]]:
    response = (
        _table(db, "journal_entries").select(
            "id,user_id,target_language,original_text,corrected,grammar_suggestions,analysis_status,"
            "sentence_mapping,sentence_mapping_status,created_at"
        )
        .eq("user_id", user_id)
        .eq("target_language", l2)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def _tags_in_entry(entry: dict[str, Any]) -> set[str]:
    if entry.get("analysis_status") in {"mock", "failed"}:
        return set()
    suggestions = entry.get("grammar_suggestions")
    if not isinstance(suggestions, list):
        return set()
    return {
        suggestion["error_type"]
        for suggestion in suggestions
        if isinstance(suggestion, dict)
        and suggestion.get("error_type") in SUPPORTED_TAGS
    }


def _lesson_for(tag: str, suggestions: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    lessons = _LESSONS_BY_TAG.get(tag, [])
    if not lessons:
        return None
    correction_text = " ".join(
        f"{row.get('original', '')} {row.get('corrected', '')}" for row in suggestions
    )
    if tag == "preposition" and not re.search(
        r"\ba\s+(?:mi|mis|tu|tus|su|sus|el|la|los|las|un|una|unos|unas|[A-ZÁÉÍÓÚÑ])",
        correction_text,
    ):
        return None
    if len(lessons) == 1:
        return lessons[0]
    if tag == "ser_estar" and re.search(
        r"\b(estoy|estás|está|estamos|están|estuve|estuviste|estuvo|estábamos|estaban)\b",
        correction_text,
        re.IGNORECASE,
    ):
        return next((lesson for lesson in lessons if lesson["id"] == "ser-estar-state-location"), lessons[0])
    return lessons[0]


def _public_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
    public = {
        key: lesson[key]
        for key in ("id", "tag", "title", "explanation", "examples", "trap_note")
    }
    public["level"] = lesson.get("level") or _LESSON_DATA["level"]
    return public


def _recent(value: Any, now: datetime, days: int) -> bool:
    at = _aware(value)
    return at is not None and at > now - timedelta(days=days)


def _offer_state(db: Any, user_id: str, l2: str, tags: set[str]) -> dict[str, dict[str, Any]]:
    if not tags:
        return {}
    response = (
        _table(db, LESSON_OFFERS_TABLE).select("*")
        .eq("user_id", user_id)
        .eq("l2", l2)
        .in_("tag", sorted(tags))
        .execute()
    )
    return {row.get("tag"): row for row in response.data or [] if row.get("tag")}


def offer_for_entry(
    db: Any,
    user_id: str,
    entry_id: str,
    now: Optional[datetime] = None,
) -> Optional[dict[str, Any]]:
    """Create at most one gentle offer when a supported tag recurs in recent entries."""
    moment = now or _now()
    current_response = (
        _table(db, "journal_entries").select("*")
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    current = (current_response.data or [None])[0]
    if not current or current.get("analysis_status") in {"mock", "failed"}:
        return None

    l2 = str(current.get("target_language") or "")
    if not SPANISH_CODE.fullmatch(l2):
        return None

    rows = _entry_rows(db, user_id, l2, RECENT_ENTRY_WINDOW)
    if not any(str(row.get("id")) == entry_id for row in rows):
        return None
    current_suggestions = [
        row for row in (current.get("grammar_suggestions") or []) if isinstance(row, dict)
    ]
    suggestions_by_tag = {
        tag: [row for row in current_suggestions if row.get("error_type") == tag]
        for tag in _tags_in_entry(current)
    }
    lesson_by_tag = {
        tag: lesson
        for tag, suggestions in suggestions_by_tag.items()
        if (lesson := _lesson_for(tag, suggestions)) is not None
    }
    current_tags = set(lesson_by_tag)
    if not current_tags:
        return None

    counts: dict[str, int] = {}
    for row in rows:
        for tag in _tags_in_entry(row):
            counts[tag] = counts.get(tag, 0) + 1

    repeated = {
        tag for tag in current_tags
        if counts.get(tag, 0) >= OFFER_THRESHOLD and tag in SUPPORTED_TAGS
    }
    if not repeated:
        return None

    existing = _offer_state(db, user_id, l2, repeated)
    eligible: list[tuple[int, str]] = []
    for tag in repeated:
        state = existing.get(tag) or {}
        snoozed_until = _aware(state.get("snoozed_until"))
        if snoozed_until and snoozed_until > moment:
            continue
        if _recent(state.get("seen_at"), moment, SEEN_COOLDOWN_DAYS):
            continue
        if _recent(state.get("offered_at"), moment, OFFER_COOLDOWN_DAYS):
            continue
        eligible.append((counts[tag], tag))
    if not eligible:
        return None

    count, tag = sorted(eligible, key=lambda item: (-item[0], item[1]))[0]
    offered_at = moment.isoformat()
    if tag in existing:
        _table(db, LESSON_OFFERS_TABLE).update({"offered_at": offered_at}).eq(
            "user_id", user_id
        ).eq("l2", l2).eq("tag", tag).execute()
    else:
        _table(db, LESSON_OFFERS_TABLE).insert({
            "user_id": user_id,
            "l2": l2,
            "tag": tag,
            "offered_at": offered_at,
        }).execute()

    lesson = lesson_by_tag[tag]
    return {"l2": l2, "tag": tag, "count": count, "lesson": _public_lesson(lesson)}


def mark_seen(
    db: Any, user_id: str, l2: str, tag: str, now: Optional[datetime] = None
) -> bool:
    if not SPANISH_CODE.fullmatch(l2) or tag not in SUPPORTED_TAGS:
        return False
    response = (
        _table(db, LESSON_OFFERS_TABLE).update({"seen_at": (now or _now()).isoformat()})
        .eq("user_id", user_id).eq("l2", l2).eq("tag", tag).execute()
    )
    return bool(response.data)


def snooze(
    db: Any, user_id: str, l2: str, tag: str, now: Optional[datetime] = None
) -> Optional[str]:
    if not SPANISH_CODE.fullmatch(l2) or tag not in SUPPORTED_TAGS:
        return None
    until = (now or _now()) + timedelta(days=SNOOZE_DAYS)
    response = (
        _table(db, LESSON_OFFERS_TABLE).update({"snoozed_until": until.isoformat()})
        .eq("user_id", user_id).eq("l2", l2).eq("tag", tag).execute()
    )
    return until.isoformat() if response.data else None


def _drill_items(rows: list[dict[str, Any]], tag: str, limit: int = 3) -> list[dict[str, str]]:
    """Build clozes from corrected learner sentences using the existing review-card helpers."""
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in rows:
        if entry.get("analysis_status") in {"mock", "failed"}:
            continue
        original_text = entry.get("original_text") or ""
        corrected_text = entry.get("corrected") or ""
        if not original_text or not corrected_text:
            continue
        for suggestion in entry.get("grammar_suggestions") or []:
            if not isinstance(suggestion, dict) or suggestion.get("error_type") != tag:
                continue
            original_phrase = str(suggestion.get("original") or "").strip()
            corrected_phrase = str(suggestion.get("corrected") or "").strip()
            if not original_phrase or not corrected_phrase or len(corrected_phrase) > 80:
                continue
            source = next(
                (sentence for sentence in split_sentences(original_text)
                 if find_form(sentence, (original_phrase,), "es")),
                None,
            )
            if not source:
                continue
            candidate = Candidate(
                sentence=source,
                surfaces=(corrected_phrase,),
                entry_id=str(entry.get("id") or "") or None,
                kind="entry_text",
            )
            corrected_sentence_text = corrected_sentence(
                candidate,
                (corrected_phrase,),
                "es",
                {
                    **entry,
                    "corrected": corrected_text,
                    "original_text": original_text,
                },
            )
            if not corrected_sentence_text:
                continue
            cloze = split_around(corrected_sentence_text, (corrected_phrase,), "es")
            if not cloze or not cloze.answer.strip():
                continue
            key = (corrected_sentence_text.casefold(), cloze.before, cloze.answer.casefold())
            if key in seen:
                continue
            seen.add(key)
            items.append({"before": cloze.before, "answer": cloze.answer, "after": cloze.after})
            if len(items) >= limit:
                return items
    return items


def drill_for_entry(
    db: Any,
    user_id: str,
    l2: str,
    tag: str,
    entry_id: str,
) -> list[dict[str, str]]:
    """Return up to three personal clozes only for a learner-owned offered lesson."""
    if not SPANISH_CODE.fullmatch(l2) or tag not in SUPPORTED_TAGS:
        return []
    offer = (
        _table(db, LESSON_OFFERS_TABLE).select("id,snoozed_until")
        .eq("user_id", user_id).eq("l2", l2).eq("tag", tag).limit(1).execute()
    ).data
    if not offer or not offer[0]:
        return []
    snoozed_until = _aware(offer[0].get("snoozed_until"))
    if snoozed_until and snoozed_until > _now():
        return []
    current = (
        _table(db, "journal_entries").select("id,grammar_suggestions")
        .eq("user_id", user_id).eq("id", entry_id).limit(1).execute()
    ).data
    if not current or tag not in _tags_in_entry(current[0]):
        return []
    rows = _entry_rows(db, user_id, l2, DRILL_ENTRY_WINDOW)
    return _drill_items(rows, tag)

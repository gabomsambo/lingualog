"""Suggested immersion changes. The level never moves unless the learner accepts.

Step down: at level L >= 1, meaning or rescue was used on at least
``STEP_DOWN_MIN_RATIO`` of the last ``STEP_DOWN_WINDOW`` entries in that language.

Step up: at level L <= 2, any support tap was used on at most
``STEP_UP_MAX_RATIO`` of the last ``STEP_UP_WINDOW`` entries, and the average
score is at least ``STEP_UP_MIN_SCORE``.

Dismiss hides the suggestion for ``SNOOZE_DAYS``. These names are the knobs to
tune later; nothing else should hard-code the numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

# Meaning or rescue: the learner opened a translation or asked for an L1 note.
STEP_DOWN_KINDS = frozenset({"reveal_meaning", "rescue_note"})
# Support: any recorded reveal or rescue.
SUPPORT_KINDS = frozenset(
    {"reveal_meaning", "rescue_note", "reveal_rewrite_gloss", "reveal_example"}
)

STEP_DOWN_MIN_LEVEL = 1
STEP_DOWN_WINDOW = 5
STEP_DOWN_MIN_RATIO = 0.60

STEP_UP_MAX_LEVEL = 2
STEP_UP_WINDOW = 8
STEP_UP_MAX_RATIO = 0.10
STEP_UP_MIN_SCORE = 75

SNOOZE_DAYS = 7


@dataclass(frozen=True)
class EntrySignal:
    entry_id: str
    user_id: str
    l2: str
    created_at: datetime
    score: Optional[float]


@dataclass(frozen=True)
class SupportTap:
    user_id: str
    entry_id: Optional[str]
    kind: str


@dataclass(frozen=True)
class Snooze:
    user_id: str
    l2: str
    snoozed_until: datetime


@dataclass(frozen=True)
class LanguageLevel:
    user_id: str
    l2: str
    level: int


@dataclass(frozen=True)
class LevelSuggestion:
    l2: str
    direction: str
    from_level: int
    to_level: int


def share_at_least(used: int, window: int, minimum: float) -> bool:
    """True when ``used / window`` reaches ``minimum``, including equality."""
    if window <= 0:
        return False
    return (used / window) >= minimum


def share_at_most(used: int, window: int, maximum: float) -> bool:
    """True when ``used / window`` is within ``maximum``, including equality."""
    if window <= 0:
        return False
    return (used / window) <= maximum


def snooze_deadline(now: datetime, days: int = SNOOZE_DAYS) -> datetime:
    return _aware(now) + timedelta(days=days)


def snooze_active(snoozed_until: Optional[datetime], now: datetime) -> bool:
    """A snooze hides the suggestion until its deadline. At that instant it expires."""
    if snoozed_until is None:
        return False
    return _aware(snoozed_until) > _aware(now)


def suggestions_for(
    user_id: str,
    levels: Sequence[LanguageLevel],
    entries: Sequence[EntrySignal],
    taps: Sequence[SupportTap],
    snoozes: Sequence[Snooze],
    now: datetime,
) -> list[LevelSuggestion]:
    """One suggestion per language for this learner. Other users' rows are ignored."""
    owned_levels = [row for row in levels if row.user_id == user_id]
    owned_entries = [row for row in entries if row.user_id == user_id]
    owned_taps = [
        row for row in taps if row.user_id == user_id and row.entry_id
    ]
    snooze_by_l2 = {
        row.l2: row.snoozed_until for row in snoozes if row.user_id == user_id
    }
    found: list[LevelSuggestion] = []
    for level in owned_levels:
        suggestion = suggest_for_language(
            l2=level.l2,
            level=level.level,
            entries=[row for row in owned_entries if row.l2 == level.l2],
            taps=owned_taps,
            snoozed_until=snooze_by_l2.get(level.l2),
            now=now,
        )
        if suggestion is not None:
            found.append(suggestion)
    found.sort(key=lambda row: row.l2)
    return found


def suggest_for_language(
    *,
    l2: str,
    level: int,
    entries: Sequence[EntrySignal],
    taps: Sequence[SupportTap],
    snoozed_until: Optional[datetime],
    now: datetime,
) -> Optional[LevelSuggestion]:
    if snooze_active(snoozed_until, now):
        return None
    # Read the windows here so tests can retune the named config.
    down_window = STEP_DOWN_WINDOW
    up_window = STEP_UP_WINDOW
    if level >= STEP_DOWN_MIN_LEVEL and len(entries) >= down_window:
        window = _newest(entries, down_window)
        used = _entries_with_kinds(window, taps, STEP_DOWN_KINDS)
        if share_at_least(used, down_window, STEP_DOWN_MIN_RATIO):
            return LevelSuggestion(l2, "down", level, level - 1)
    if level <= STEP_UP_MAX_LEVEL and len(entries) >= up_window:
        window = _newest(entries, up_window)
        used = _entries_with_kinds(window, taps, SUPPORT_KINDS)
        scores = [row.score for row in window if row.score is not None]
        if scores and share_at_most(used, up_window, STEP_UP_MAX_RATIO):
            average = sum(scores) / len(scores)
            if average >= STEP_UP_MIN_SCORE:
                return LevelSuggestion(l2, "up", level, level + 1)
    return None


def _newest(entries: Sequence[EntrySignal], window: int) -> list[EntrySignal]:
    ordered = sorted(entries, key=lambda row: (_aware(row.created_at), row.entry_id), reverse=True)
    return ordered[:window]


def _entries_with_kinds(
    window: Sequence[EntrySignal],
    taps: Sequence[SupportTap],
    kinds: frozenset[str],
) -> int:
    ids = {row.entry_id for row in window}
    hit = {
        tap.entry_id
        for tap in taps
        if tap.entry_id in ids and tap.kind in kinds
    }
    return len(hit)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

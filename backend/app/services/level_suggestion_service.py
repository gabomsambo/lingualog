"""Load a learner's history and turn it into a level suggestion.

Accept writes the new immersion through ``save_user_settings``, the same path
Settings uses. Dismiss stores a snooze. Neither path changes a level on its own
except accept, which the learner just confirmed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from database import create_supabase_client, fetch_language_profile, save_user_settings
from level_suggestion import (
    EVIDENCE_STATUS,
    STEP_DOWN_WINDOW,
    STEP_UP_WINDOW,
    EntrySignal,
    LanguageLevel,
    LevelSuggestion,
    Snooze,
    SupportTap,
    snooze_deadline,
    suggestions_for,
)

L2_PATTERN = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
SNOOZE_TABLE = "level_suggestion_snoozes"
ENTRY_LIMIT = max(STEP_DOWN_WINDOW, STEP_UP_WINDOW)


class NoLevelSuggestion(LookupError):
    """This learner has nothing to accept or dismiss for that language."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _score(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def _owned(rows: list[dict], user_id: str) -> list[dict]:
    return [row for row in rows if str(row.get("user_id")) == str(user_id)]


def _entry_l2(row: dict) -> str:
    return str(row.get("target_language") or "").strip()


def _entry_level(row: dict) -> Optional[int]:
    snapshot = row.get("policy_snapshot")
    if not isinstance(snapshot, dict):
        return None
    try:
        return int(snapshot.get("immersion_level"))
    except (TypeError, ValueError):
        return None


def current_suggestions(user_id: str, supabase: Any = None, now: Optional[datetime] = None) -> list[dict]:
    client = supabase or create_supabase_client()
    moment = now or _now()
    profiles = _owned(_table(client, "user_language_profiles", user_id), user_id)
    settings_rows = _owned(_table(client, "user_settings", user_id, columns="user_id,default_target_lang"), user_id)
    default_l2 = (settings_rows[0].get("default_target_lang") if settings_rows else None) or ""
    levels: list[LanguageLevel] = []
    entries: list[EntrySignal] = []
    for profile in profiles:
        l2 = str(profile.get("l2") or "")
        if not l2:
            continue
        try:
            level = int(profile.get("immersion_level", 1))
        except (TypeError, ValueError):
            continue
        since = _aware(profile["level_changed_at"]) if profile.get("level_changed_at") else None
        levels.append(LanguageLevel(user_id, l2, level, since))
        for row in _owned(_entries_for_language(client, user_id, l2, level, since), user_id):
            if not row.get("id") or not row.get("created_at"):
                continue
            if _entry_l2(row) != l2 or _entry_level(row) != level:
                continue
            entries.append(
                EntrySignal(
                    entry_id=str(row["id"]),
                    user_id=user_id,
                    l2=l2,
                    created_at=_aware(row["created_at"]),
                    score=_score(row.get("score")),
                    immersion_level=_entry_level(row),
                    analysis_status=row.get("analysis_status"),
                )
            )
    event_rows = _owned(_support_events(client, user_id, [row.entry_id for row in entries]), user_id)
    taps = [
        SupportTap(
            user_id,
            str(row["entry_id"]) if row.get("entry_id") else None,
            str(row.get("kind") or ""),
        )
        for row in event_rows
    ]
    snoozes = [
        Snooze(user_id, str(row["l2"]), _aware(row["snoozed_until"]))
        for row in _owned(_table(client, SNOOZE_TABLE, user_id), user_id)
        if row.get("l2") and row.get("snoozed_until")
    ]
    found = suggestions_for(user_id, levels, entries, taps, snoozes, moment)
    found.sort(key=lambda row: (row.l2 != default_l2, row.l2))
    return [_public(row) for row in found]


def accept_level_suggestion(user_id: str, l2: str, supabase: Any = None) -> dict:
    _require_l2(l2)
    client = supabase or create_supabase_client()
    match = _require_current(user_id, l2, client)
    profile = fetch_language_profile(user_id, l2) or {}
    if str(profile.get("user_id") or user_id) != str(user_id):
        raise NoLevelSuggestion(l2)
    proficiency = profile.get("proficiency") or "A2"
    settings_rows = _owned(_table(client, "user_settings", user_id, columns="user_id,default_target_lang"), user_id)
    default_l2 = settings_rows[0].get("default_target_lang") if settings_rows else None
    settings: dict[str, Any] = {}
    if default_l2 == l2:
        settings["immersion_level"] = match["to_level"]
    save_user_settings(
        user_id,
        settings,
        [{"l2": l2, "immersion_level": match["to_level"], "proficiency": proficiency}],
    )
    _delete_snooze(client, user_id, l2)
    return match


def dismiss_level_suggestion(user_id: str, l2: str, supabase: Any = None, now: Optional[datetime] = None) -> dict:
    _require_l2(l2)
    client = supabase or create_supabase_client()
    match = _require_current(user_id, l2, client)
    moment = now or _now()
    until = snooze_deadline(moment)
    client.table(SNOOZE_TABLE).upsert(
        {"user_id": user_id, "l2": l2, "snoozed_until": until.isoformat()},
        on_conflict="user_id,l2",
    ).execute()
    return {**match, "snoozed_until": until.isoformat()}


def _require_current(user_id: str, l2: str, client: Any) -> dict:
    match = next((row for row in current_suggestions(user_id, client) if row["l2"] == l2), None)
    if match is None:
        raise NoLevelSuggestion(l2)
    return match


def _require_l2(l2: str) -> None:
    if not L2_PATTERN.match(l2 or ""):
        raise ValueError("l2 must be a language code")


def _public(row: LevelSuggestion) -> dict:
    return {
        "l2": row.l2,
        "direction": row.direction,
        "from_level": row.from_level,
        "to_level": row.to_level,
    }


def _table(client: Any, name: str, user_id: str, columns: str = "*") -> list[dict]:
    response = client.table(name).select(columns).eq("user_id", user_id).execute()
    return list(response.data or [])


def _entries_for_language(
    client: Any, user_id: str, l2: str, level: int, since: Optional[datetime]
) -> list[dict]:
    query = (
        client.table("journal_entries")
        .select("id,user_id,target_language,score,created_at,analysis_status,policy_snapshot")
        .eq("user_id", user_id)
        .eq("target_language", l2)
        .eq("analysis_status", EVIDENCE_STATUS)
        .eq("policy_snapshot->>immersion_level", str(level))
        .not_.is_("score", "null")
    )
    if since is not None:
        query = query.gt("created_at", since.isoformat())
    response = query.order("created_at", desc=True).limit(ENTRY_LIMIT).execute()
    return list(response.data or [])


def _support_events(client: Any, user_id: str, entry_ids: list[str]) -> list[dict]:
    if not entry_ids:
        return []
    response = (
        client.table("support_events")
        .select("user_id,entry_id,kind")
        .eq("user_id", user_id)
        .in_("entry_id", entry_ids)
        .execute()
    )
    return list(response.data or [])


def _delete_snooze(client: Any, user_id: str, l2: str) -> None:
    client.table(SNOOZE_TABLE).delete().eq("user_id", user_id).eq("l2", l2).execute()

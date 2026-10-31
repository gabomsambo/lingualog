"""Vocabulary review: load a learner's cards, plan a session, apply a review.

Review makes no model calls. A studied word owns a recognition card; once that card has held
for about a week a production card joins it. Every review is applied by the
``apply_card_review`` function, which advances the card and appends its log row together.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from database import (
    USER_VOCABULARY_TABLE,
    create_supabase_client,
    fetch_language_profile,
    list_language_profiles,
    update_vocabulary_item,
)
from learning_policy import resolve_policy
from review_cards import build_review_card
from review_scheduler import (
    CATCHUP_DAILY_REVIEWS,
    DEFAULT_DAILY_NEW_WORDS,
    DEFAULT_RETENTION,
    FSRS_VERSION,
    PRODUCTION,
    PRODUCTION_FIRST_DUE,
    RECOGNITION,
    SESSION_SIZE,
    SessionPlan,
    aware,
    day_start,
    derived_status,
    is_at_risk,
    make_scheduler,
    plan_session,
    production_card_due,
    schedule_review,
)

L2_PATTERN = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
CARDS_TABLE = "vocab_cards"
LOGS_TABLE = "vocab_review_logs"
PARAMS_TABLE = "user_fsrs_params"
APPLY_REVIEW_RPC = "apply_card_review"
MODES = ("normal", "catchup")
WORD_ID_CHUNK = 100
# Statuses whose words are not being studied: their cards stay but are never offered.
_SUSPENDING_STATUSES = frozenset({"new", "known", "ignored"})


class ReviewNotFound(LookupError):
    """The card does not exist or belongs to someone else."""


class StaleReview(RuntimeError):
    """The card changed since it was served, so this review was not applied."""


class CardSuspended(RuntimeError):
    """The word is not being studied, so its card cannot be reviewed."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def validate_language(language: str) -> str:
    if not L2_PATTERN.match(language or ""):
        raise ValueError("language must be a code such as es or pt-BR")
    return language


# --- Loading -----------------------------------------------------------------


def load_review_settings(user_id: str, language: str) -> tuple[int, float]:
    """The language's daily new-word limit and desired retention."""
    profile = fetch_language_profile(user_id, language) or {}
    return (
        int(profile.get("daily_new_words") or DEFAULT_DAILY_NEW_WORDS),
        float(profile.get("desired_retention") or DEFAULT_RETENTION),
    )


def load_fsrs_parameters(user_id: str, language: str) -> Optional[list[float]]:
    response = (
        create_supabase_client().table(PARAMS_TABLE).select("parameters")
        .eq("user_id", user_id).eq("l2", language).limit(1).execute()
    )
    return (response.data[0].get("parameters") if response.data else None) or None


def scheduler_for(user_id: str, language: str, fuzz: bool = True):
    _, retention = load_review_settings(user_id, language)
    return make_scheduler(retention, load_fsrs_parameters(user_id, language), fuzz=fuzz)


def load_active_cards(user_id: str, language: Optional[str], now: datetime) -> list[dict]:
    """Cards that could be offered now: due, or never reviewed, with a usable word card.

    Cards due later are never needed to plan a session, so they stay in the database. That keeps
    the result well under the API's row limit however long the learner has been reviewing, and
    the most overdue come first if it is ever reached.
    """
    query = (
        create_supabase_client().table(CARDS_TABLE)
        .select(f"*, word:{USER_VOCABULARY_TABLE}!inner(card_status)")
        .eq("user_id", user_id)
        .eq("word.card_status", "ok")
        .is_("suspended_at", "null")
        .or_(f"reps.eq.0,due.lte.{now.isoformat()}")
        .order("due")
    )
    if language:
        query = query.eq("language", language)
    return [{k: v for k, v in row.items() if k != "word"} for row in query.execute().data or []]


def load_recognition_cards(user_id: str, word_ids: list[str]) -> list[dict]:
    """The unsuspended recognition cards of these words, a few at a time to keep the request short."""
    cards: list[dict] = []
    for start in range(0, len(word_ids), WORD_ID_CHUNK):
        response = (
            create_supabase_client().table(CARDS_TABLE).select("*")
            .eq("user_id", user_id).eq("card_type", RECOGNITION).is_("suspended_at", "null")
            .in_("word_id", word_ids[start:start + WORD_ID_CHUNK]).execute()
        )
        cards += response.data or []
    return cards


def load_card(user_id: str, card_id: str) -> Optional[dict]:
    response = (
        create_supabase_client().table(CARDS_TABLE).select("*")
        .eq("id", card_id).eq("user_id", user_id).limit(1).execute()
    )
    return response.data[0] if response.data else None


def load_recognition_card(user_id: str, word_id: str) -> Optional[dict]:
    response = (
        create_supabase_client().table(CARDS_TABLE).select("*")
        .eq("user_id", user_id).eq("word_id", word_id).eq("card_type", RECOGNITION)
        .limit(1).execute()
    )
    return response.data[0] if response.data else None


def load_words(user_id: str, word_ids: list[str]) -> dict[str, dict]:
    if not word_ids:
        return {}
    response = (
        create_supabase_client().table(USER_VOCABULARY_TABLE).select("*")
        .eq("user_id", user_id).in_("id", word_ids).execute()
    )
    return {row["id"]: row for row in response.data or []}


def load_encounters(user_id: str, word_ids: list[str]) -> list[dict]:
    if not word_ids:
        return []
    response = (
        create_supabase_client().table("word_encounters").select("*")
        .eq("user_id", user_id).in_("word_id", word_ids).execute()
    )
    return response.data or []


def load_entries(user_id: str, entry_ids: list[str]) -> dict[str, dict]:
    if not entry_ids:
        return {}
    response = (
        create_supabase_client().table("journal_entries")
        .select("id, original_text, corrected, sentence_mapping, sentence_mapping_status")
        .eq("user_id", user_id).in_("id", entry_ids).execute()
    )
    return {row["id"]: row for row in response.data or []}


def _rows_since(table: str, column: str, user_id: str, since: datetime, **equals: str) -> list[dict]:
    query = (
        create_supabase_client().table(table).select("language")
        .eq("user_id", user_id).gte(column, since.isoformat())
    )
    for name, value in equals.items():
        query = query.eq(name, value)
    return query.execute().data or []


def count_new_words_today(user_id: str, language: str, now: datetime) -> int:
    """Recognition cards first reviewed today: the new words already spent from the daily limit."""
    rows = _rows_since(
        CARDS_TABLE, "first_reviewed_at", user_id, day_start(now), card_type=RECOGNITION, language=language
    )
    return len(rows)


def count_reviews_today(user_id: str, language: str, now: datetime) -> int:
    return len(_rows_since(LOGS_TABLE, "reviewed_at", user_id, day_start(now), language=language, source="review"))


def load_learning_words(user_id: str, language: Optional[str] = None) -> list[dict]:
    query = (
        create_supabase_client().table(USER_VOCABULARY_TABLE).select("id, language")
        .eq("user_id", user_id).eq("status", "learning")
    )
    if language:
        query = query.eq("language", language)
    return query.execute().data or []


def load_card_word_ids(user_id: str, word_ids: list[str]) -> set[str]:
    if not word_ids:
        return set()
    response = (
        create_supabase_client().table(CARDS_TABLE).select("word_id")
        .eq("user_id", user_id).eq("card_type", RECOGNITION).in_("word_id", word_ids).execute()
    )
    return {row["word_id"] for row in response.data or []}


def insert_cards(rows: list[dict]) -> list[dict]:
    """Insert cards, leaving any that already exist. Returns only the rows that were new."""
    if not rows:
        return []
    response = (
        create_supabase_client().table(CARDS_TABLE)
        .upsert(rows, on_conflict="word_id,card_type", ignore_duplicates=True).execute()
    )
    return response.data or []


def set_cards_suspended(user_id: str, word_id: str, suspended: bool) -> None:
    table = create_supabase_client().table(CARDS_TABLE)
    if suspended:
        table.update({"suspended_at": _now().isoformat()}).eq("user_id", user_id) \
            .eq("word_id", word_id).is_("suspended_at", "null").execute()
    else:
        table.update({"suspended_at": None}).eq("user_id", user_id).eq("word_id", word_id).execute()


def suspend_inactive_cards(user_id: str, language: Optional[str] = None) -> None:
    """Suspend active cards of words that are new, known or ignored."""
    query = (
        create_supabase_client().table(CARDS_TABLE)
        .select(f"id, word:{USER_VOCABULARY_TABLE}!inner(status)")
        .eq("user_id", user_id).is_("suspended_at", "null")
        .in_("word.status", sorted(_SUSPENDING_STATUSES))
    )
    if language:
        query = query.eq("language", language)
    ids = [row["id"] for row in query.execute().data or []]
    for start in range(0, len(ids), WORD_ID_CHUNK):
        create_supabase_client().table(CARDS_TABLE).update({"suspended_at": _now().isoformat()}) \
            .eq("user_id", user_id).in_("id", ids[start:start + WORD_ID_CHUNK]).execute()


def apply_card_review(user_id: str, card_id: str, expected_reps: int, card: dict, log: dict) -> Optional[dict]:
    response = create_supabase_client().rpc(
        APPLY_REVIEW_RPC,
        {
            "p_user_id": user_id,
            "p_card_id": card_id,
            "p_expected_reps": expected_reps,
            "p_card": card,
            "p_log": log,
        },
    ).execute()
    return response.data or None


# --- Words and their cards -----------------------------------------------------


def sync_word_cards(user_id: str, word: dict[str, Any]) -> None:
    """Make a word's cards match its notebook state.

    A word in study owns an active recognition card. A word the learner marked known, ignored or
    returned to New keeps its history, but its cards are suspended. Mastered words are left alone.
    """
    status = word.get("status")
    if status == "learning":
        insert_cards([{
            "user_id": user_id, "word_id": word["id"], "language": word["language"],
            "card_type": RECOGNITION, "fsrs_version": FSRS_VERSION,
        }])
        set_cards_suspended(user_id, word["id"], False)
    elif status in _SUSPENDING_STATUSES:
        set_cards_suspended(user_id, word["id"], True)


def sync_learning_cards(user_id: str, language: Optional[str] = None) -> int:
    """Give every word in study a recognition card, and suspend cards of words no longer studied."""
    suspend_inactive_cards(user_id, language)
    words = load_learning_words(user_id, language)
    have = load_card_word_ids(user_id, [word["id"] for word in words])
    missing = [
        {"user_id": user_id, "word_id": w["id"], "language": w["language"],
         "card_type": RECOGNITION, "fsrs_version": FSRS_VERSION}
        for w in words if w["id"] not in have
    ]
    return len(insert_cards(missing))


# --- Sessions ------------------------------------------------------------------


def _plan(
    user_id: str, language: str, now: datetime, mode: str, limit: int
) -> tuple[SessionPlan, Any, tuple[int, float]]:
    settings = load_review_settings(user_id, language)
    scheduler = make_scheduler(settings[1], load_fsrs_parameters(user_id, language))
    plan = plan_session(
        load_active_cards(user_id, language, now),
        now,
        scheduler,
        daily_new_words=settings[0],
        reviewed_new_today=count_new_words_today(user_id, language, now),
        reviews_today=count_reviews_today(user_id, language, now),
        mode=mode,
        limit=limit,
    )
    return plan, scheduler, settings


def _counts(plan: SessionPlan) -> dict[str, Any]:
    return {
        "due": plan.due,
        "new_available": plan.new_available,
        "new_remaining": plan.new_remaining,
        "total": plan.total,
        "backlog": plan.backlog,
        "at_risk": plan.at_risk,
        "suggest_catchup": plan.suggest_catchup,
    }


def get_session(
    user_id: str,
    language: str,
    mode: str = "normal",
    limit: int = SESSION_SIZE,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """The next batch of cards for one language, built from the learner's own sentences."""
    validate_language(language)
    if mode not in MODES:
        raise ValueError("mode must be normal or catchup")
    now = now or _now()
    sync_learning_cards(user_id, language)
    plan, scheduler, (daily_new_words, retention) = _plan(user_id, language, now, mode, limit)

    word_ids = [card["word_id"] for card in plan.cards]
    words = load_words(user_id, word_ids)
    encounters = load_encounters(user_id, word_ids)
    entry_ids = sorted({
        str(entry_id)
        for entry_id in [w.get("entry_id") for w in words.values()]
        + [e.get("source_id") for e in encounters if e.get("source_type") == "entry"]
        if entry_id
    })
    entries = load_entries(user_id, entry_ids)
    quiz = resolve_policy(user_id, language).quiz

    cards = []
    for row in plan.cards:
        word = words.get(row["word_id"])
        if not word:
            continue
        cards.append(build_review_card(
            row,
            word,
            [e for e in encounters if e.get("word_id") == row["word_id"]],
            entries,
            quiz,
            word.get("status") or "learning",
            is_at_risk(row, now, scheduler),
        ))
    return {
        "language": language,
        "mode": mode,
        "cards": cards,
        "counts": _counts(plan),
        "settings": {
            "daily_new_words": daily_new_words,
            "desired_retention": retention,
            "catchup_daily_budget": CATCHUP_DAILY_REVIEWS,
        },
        "catchup": (
            {"daily_budget": plan.catchup_budget, "done_today": plan.catchup_done_today}
            if mode == "catchup" else None
        ),
    }


def get_summary(user_id: str, now: Optional[datetime] = None) -> dict[str, Any]:
    """What is waiting in each studied language, for the dashboard."""
    now = now or _now()
    sync_learning_cards(user_id)
    languages = [
        row["l2"] for row in list_language_profiles(user_id) or []
        if row.get("l2") and row.get("active") is not False
    ]
    rows = []
    for language in languages:
        plan, _, _ = _plan(user_id, language, now, "normal", SESSION_SIZE)
        rows.append({"language": language, **_counts(plan)})
    return {
        "languages": rows,
        "total": sum(row["total"] for row in rows),
        "at_risk": sum(row["at_risk"] for row in rows),
    }


def attach_review_state(user_id: str, items: list[dict], now: Optional[datetime] = None) -> list[dict]:
    """Add each word's review progress to the notebook list: due date, stability and the At-risk flag."""
    now = now or _now()
    recognition = {card["word_id"]: card for card in load_recognition_cards(user_id, [i["id"] for i in items])}
    schedulers: dict[str, Any] = {}
    enriched = []
    for item in items:
        card = recognition.get(item["id"])
        if not card:
            enriched.append({**item, "review": None})
            continue
        scheduler = schedulers.setdefault(item["language"], scheduler_for(user_id, item["language"]))
        enriched.append({
            **item,
            "review": {
                "due": aware(card["due"]).isoformat(),
                "stability": card.get("stability"),
                "reps": card.get("reps") or 0,
                "lapses": card.get("lapses") or 0,
                "at_risk": is_at_risk(card, now, scheduler),
            },
        })
    return enriched


# --- Reviews -------------------------------------------------------------------


def submit_review(
    user_id: str,
    card_id: str,
    rating: str,
    expected_reps: Optional[int] = None,
    duration_ms: Optional[int] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Apply one two-button review and keep the word's state in step with the scheduler."""
    now = now or _now()
    row = load_card(user_id, card_id)
    if not row:
        raise ReviewNotFound(card_id)
    if row.get("suspended_at"):
        raise CardSuspended(card_id)
    reps = int(row.get("reps") or 0)
    if expected_reps is not None and expected_reps != reps:
        raise StaleReview(card_id)

    scheduler = scheduler_for(user_id, row["language"])
    outcome = schedule_review(row, rating, now, scheduler, duration_ms)
    updated = apply_card_review(user_id, card_id, reps, outcome.card, outcome.log)
    if not updated:
        raise StaleReview(card_id)

    recognition = updated if updated["card_type"] == RECOGNITION else load_recognition_card(user_id, row["word_id"])
    word = load_words(user_id, [row["word_id"]]).get(row["word_id"]) or {}
    status = derived_status(word.get("status"), (recognition or {}).get("stability"))
    if word and status != word.get("status"):
        update_vocabulary_item(row["word_id"], user_id, {"status": status})

    production_added = False
    if recognition and updated["card_type"] == RECOGNITION and production_card_due(updated):
        production_added = bool(insert_cards([{
            "user_id": user_id, "word_id": row["word_id"], "language": row["language"],
            "card_type": PRODUCTION, "fsrs_version": FSRS_VERSION,
            "due": (now + PRODUCTION_FIRST_DUE).isoformat(),
        }]))

    return {
        "card_id": card_id,
        "rating": rating,
        "state": updated["state"],
        "due": aware(updated["due"]).isoformat(),
        "stability": updated.get("stability"),
        "reps": updated["reps"],
        "requeue": outcome.requeue,
        "status": status,
        "production_card_added": production_added,
    }

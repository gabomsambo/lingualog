"""FSRS scheduling for vocabulary review. Pure functions, no database and no model calls.

Two buttons map onto FSRS ratings: "again" is Again and "got_it" is Good. States are
derived from the scheduler: a word is Known once its recognition card is stable for
KNOWN_STABILITY_DAYS, and At risk when it is due and its retrievability has fallen below
AT_RISK_RETRIEVABILITY. Mastered is reserved for the writing-use evidence added later.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from fsrs import Card, Rating, Scheduler, State

logger = logging.getLogger(__name__)

FSRS_VERSION = "fsrs-6"

DEFAULT_RETENTION = 0.90
MIN_RETENTION = 0.80
MAX_RETENTION = 0.95
DEFAULT_DAILY_NEW_WORDS = 10

KNOWN_STABILITY_DAYS = 21.0
PRODUCTION_STABILITY_DAYS = 7.0
PRODUCTION_FIRST_DUE = timedelta(days=1)
AT_RISK_RETRIEVABILITY = 0.8
PARAMETER_COUNT = 21

SESSION_SIZE = 20
CATCHUP_BACKLOG = 40
CATCHUP_DAILY_REVIEWS = 30
REQUEUE_WITHIN = timedelta(minutes=20)

RATINGS = {"again": Rating.Again, "got_it": Rating.Good}

RECOGNITION = "recognition"
PRODUCTION = "production"

STATUS_LEARNING = "learning"
STATUS_KNOWN = "known"
# Statuses the scheduler never overwrites: the learner chose them, or writing evidence set them.
_LOCKED_STATUSES = frozenset({"mastered", "ignored"})


def aware(value: Any) -> Optional[datetime]:
    """Parse a stored timestamp into an aware UTC datetime."""
    if value is None or value == "":
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def clamp_retention(value: Any) -> float:
    """The learner's desired retention, held inside the range the settings allow."""
    try:
        retention = float(value)
    except (TypeError, ValueError):
        return DEFAULT_RETENTION
    return min(MAX_RETENTION, max(MIN_RETENTION, retention))


def make_scheduler(
    desired_retention: Any = DEFAULT_RETENTION,
    parameters: Optional[Sequence[float]] = None,
    fuzz: bool = True,
) -> Scheduler:
    """An FSRS-6 scheduler for one learner and language. Missing parameters mean the defaults."""
    options: dict[str, Any] = {
        "desired_retention": clamp_retention(desired_retention),
        "enable_fuzzing": fuzz,
    }
    if parameters and len(parameters) == PARAMETER_COUNT:
        try:
            return Scheduler(parameters=tuple(float(value) for value in parameters), **options)
        except ValueError:
            logger.warning("Ignoring stored FSRS parameters that are out of bounds")
    return Scheduler(**options)


def to_fsrs_card(row: Mapping[str, Any]) -> Card:
    """Rebuild the py-fsrs card from a vocab_cards row."""
    return Card(
        state=State(int(row.get("state") or State.Learning)),
        step=row.get("step"),
        stability=row.get("stability"),
        difficulty=row.get("difficulty"),
        due=aware(row.get("due")) or datetime.now(timezone.utc),
        last_review=aware(row.get("last_review")),
    )


@dataclass(frozen=True)
class ReviewOutcome:
    """The new scheduling state of a card and the log row for the review that produced it."""

    card: dict[str, Any]
    log: dict[str, Any]
    requeue: bool


def schedule_review(
    row: Mapping[str, Any],
    rating: str,
    now: datetime,
    scheduler: Scheduler,
    duration_ms: Optional[int] = None,
) -> ReviewOutcome:
    """Apply one review. ``rating`` is ``again`` or ``got_it``."""
    fsrs_rating = RATINGS[rating]
    before = to_fsrs_card(row)
    after, _ = scheduler.review_card(before, fsrs_rating, review_datetime=now)
    due = after.due
    card = {
        "state": int(after.state),
        "step": after.step,
        "stability": after.stability,
        "difficulty": after.difficulty,
        "due": due.isoformat(),
        "last_review": now.isoformat(),
        "lapsed": before.state == State.Review and fsrs_rating == Rating.Again,
    }
    log = {
        "rating": int(fsrs_rating),
        "reviewed_at": now.isoformat(),
        "duration_ms": duration_ms,
        "source": "review",
    }
    return ReviewOutcome(card=card, log=log, requeue=due - now <= REQUEUE_WITHIN)


def retrievability(row: Mapping[str, Any], now: datetime, scheduler: Scheduler) -> float:
    """Probability of recall right now. A card that was never reviewed has none yet (0.0)."""
    if not row.get("reps") or not row.get("last_review"):
        return 0.0
    return float(scheduler.get_card_retrievability(to_fsrs_card(row), now))


def is_due(row: Mapping[str, Any], now: datetime) -> bool:
    return aware(row.get("due")) is not None and aware(row["due"]) <= now


def is_at_risk(row: Mapping[str, Any], now: datetime, scheduler: Scheduler) -> bool:
    """Due and likely forgotten. A card never reviewed is new, not at risk."""
    return (
        bool(row.get("reps"))
        and row.get("suspended_at") is None
        and is_due(row, now)
        and retrievability(row, now, scheduler) < AT_RISK_RETRIEVABILITY
    )


def derived_status(current: Optional[str], recognition_stability: Optional[float]) -> str:
    """Notebook state after a review: Known once the recognition card is stable, else Learning."""
    if current in _LOCKED_STATUSES:
        return str(current)
    if recognition_stability is not None and recognition_stability >= KNOWN_STABILITY_DAYS:
        return STATUS_KNOWN
    return STATUS_LEARNING


def production_card_due(recognition: Mapping[str, Any]) -> bool:
    """A production card joins once the recognition card has held for about a week."""
    stability = recognition.get("stability")
    return (
        int(recognition.get("state") or 0) == int(State.Review)
        and stability is not None
        and stability >= PRODUCTION_STABILITY_DAYS
    )


def day_start(now: datetime) -> datetime:
    """Start of the learner's day. The daily new-word cap already counts UTC days."""
    utc = now.astimezone(timezone.utc)
    return utc.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass(frozen=True)
class SessionPlan:
    """Which cards a session offers and the counts the dashboard shows."""

    cards: list[dict[str, Any]]
    due: int
    new_available: int
    new_remaining: int
    backlog: int
    at_risk: int
    suggest_catchup: bool
    catchup_done_today: int = 0
    catchup_budget: int = 0

    @property
    def total(self) -> int:
        """What the dashboard calls "due": reviews waiting plus new words allowed today."""
        return self.due + min(self.new_available, self.new_remaining)


def plan_session(
    cards: Sequence[Mapping[str, Any]],
    now: datetime,
    scheduler: Scheduler,
    daily_new_words: int,
    reviewed_new_today: int,
    reviews_today: int,
    mode: str = "normal",
    limit: int = SESSION_SIZE,
) -> SessionPlan:
    """Choose the cards for one session from a language's active cards.

    Reviews come first, the most likely forgotten first. New words follow, but only as many
    as today's remaining allowance. Catch-up mode serves reviews only, a fixed number a day,
    so a backlog drains over several days instead of arriving at once.
    """
    active = [card for card in cards if card.get("suspended_at") is None]
    unseen = [card for card in active if not card.get("reps")]
    new_words = sorted(
        (card for card in unseen if card["card_type"] == RECOGNITION),
        key=lambda card: aware(card.get("created_at")) or now,
    )
    waiting = [card for card in active if card.get("reps") or card["card_type"] == PRODUCTION]
    reviews = [card for card in waiting if is_due(card, now)]
    reviews.sort(key=lambda card: (retrievability(card, now, scheduler), aware(card["due"])))

    new_remaining = max(0, daily_new_words - reviewed_new_today)
    backlog = len([card for card in reviews if card.get("reps")])
    at_risk = len([card for card in reviews if is_at_risk(card, now, scheduler)])
    suggest_catchup = backlog >= CATCHUP_BACKLOG

    if mode == "catchup":
        picked = reviews[: min(limit, max(0, CATCHUP_DAILY_REVIEWS - reviews_today))]
    else:
        picked = reviews[:limit]
        picked += new_words[: max(0, min(new_remaining, limit - len(picked)))]

    return SessionPlan(
        cards=picked,
        due=len(reviews),
        new_available=len(new_words),
        new_remaining=new_remaining,
        backlog=backlog,
        at_risk=at_risk,
        suggest_catchup=suggest_catchup,
        catchup_done_today=reviews_today if mode == "catchup" else 0,
        catchup_budget=CATCHUP_DAILY_REVIEWS if mode == "catchup" else 0,
    )

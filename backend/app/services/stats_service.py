"""Journal statistics and vocabulary/review progress.

The journal half groups writing stats. The vocabulary half builds the Progress page
(§4.9 of the vocabulary design) from plain rows: notebook counts, a 30-day trend,
active words, encounter counts, review health and the week's activity mix. Charts,
counts and trends are plain code and never call a model.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from supabase import Client as SupabaseClient

from app.schemas.stats_schemas import WordCountStat, LanguageStat, StreakData, UserStatsResponse
from app.services import vocab_service
from review_scheduler import aware, day_start, is_at_risk, make_scheduler

VOCAB_STATUSES = ("new", "learning", "known", "mastered", "ignored")
ENCOUNTER_KINDS = ("lookup", "read", "entry_text", "entry_fix", "entry_rewrite", "used_ok", "used_error")
# Research's rough guide to a word "becoming known"; shown as progress, never as a gate.
ENCOUNTER_GUIDE_MIN = 10
ENCOUNTER_GUIDE_MAX = 12
TREND_DAYS = 30
WEEK_DAYS = 7
TRUE_RETENTION_DAYS = 30
REVIEW_MINUTES_BUDGET = 20


async def get_daily_word_counts(db: SupabaseClient, user_id: str, days: int = 7) -> List[WordCountStat]:
    """Fetches total word counts for the last N days for a given user."""
    try:
        # Get entries from the last N days
        start_date = (date.today() - timedelta(days=days)).isoformat()

        response = db.table('journal_entries').select('original_text, created_at').eq('user_id', user_id).gte('created_at', start_date).execute()

        if not response.data:
            return []

        # Group by date and count words
        daily_counts = {}
        for entry in response.data:
            entry_date = entry['created_at'][:10]  # Extract date part
            word_count = len(entry['original_text'].split()) if entry['original_text'] else 0
            daily_counts[entry_date] = daily_counts.get(entry_date, 0) + word_count

        # Convert to WordCountStat objects
        return [WordCountStat(date=date_str, count=count) for date_str, count in daily_counts.items()]
    except Exception:
        return []


async def get_language_breakdown(db: SupabaseClient, user_id: str) -> Tuple[List[LanguageStat], int]:
    """Fetches language breakdown (counts and percentages) and total words for a user."""
    try:
        response = db.table('journal_entries').select('target_language, original_text').eq('user_id', user_id).execute()

        if not response.data:
            return [], 0

        # Group by the language the entry was written in and count words
        language_counts = {}
        total_words = 0

        for entry in response.data:
            language = entry.get('target_language') or 'Other'
            word_count = len(entry['original_text'].split()) if entry['original_text'] else 0
            language_counts[language] = language_counts.get(language, 0) + word_count
            total_words += word_count

        # Convert to LanguageStat objects with percentages
        language_stats = []
        for language, count in language_counts.items():
            percentage = (count / total_words * 100) if total_words > 0 else 0
            language_stats.append(LanguageStat(language=language, count=count, percentage=percentage))

        return language_stats, total_words
    except Exception:
        return [], 0


async def get_all_entry_dates(db: SupabaseClient, user_id: str) -> List[date]:
    """Fetches all unique dates on which the user made entries."""
    try:
        response = db.table('journal_entries').select('created_at').eq('user_id', user_id).execute()

        if not response.data:
            return []

        # Extract unique dates
        unique_dates = set()
        for entry in response.data:
            entry_date_str = entry['created_at'][:10]  # Extract date part
            try:
                entry_date = date.fromisoformat(entry_date_str)
                unique_dates.add(entry_date)
            except ValueError:
                continue

        return sorted(list(unique_dates))
    except Exception:
        return []


def calculate_streaks(entry_dates: List[date], today: date = date.today()) -> Tuple[int, int]:
    """Calculates current and longest writing streaks from a list of unique entry dates."""
    if not entry_dates:
        return 0, 0

    # Ensure dates are unique and sorted
    unique_dates = sorted(list(set(entry_dates)))

    current_streak = 0
    longest_streak = 0
    current_run = 0

    # Calculate longest streak
    if unique_dates:
        longest_streak = 1
        current_run = 1
        for i in range(1, len(unique_dates)):
            if (unique_dates[i] - unique_dates[i-1]).days == 1:
                current_run += 1
            else:
                longest_streak = max(longest_streak, current_run)
                current_run = 1
        longest_streak = max(longest_streak, current_run)

    # Calculate current streak
    # Check if today is an entry day, or yesterday if today has no entry yet
    current_streak_active_date = today
    if not unique_dates or unique_dates[-1] < today - timedelta(days=1):
         # No entries recently or last entry is older than yesterday
        current_streak = 0
    elif unique_dates[-1] == today:
        current_streak_active_date = today
    elif unique_dates[-1] == today - timedelta(days=1):
        current_streak_active_date = today - timedelta(days=1)
    else:
        current_streak = 0 # Gap before today/yesterday

    if current_streak != 0 or unique_dates[-1] >= today - timedelta(days=1): # check if streak could exist
        temp_current_streak = 0
        # Iterate backwards from the active date for current streak
        for d in reversed(unique_dates):
            if d == current_streak_active_date:
                temp_current_streak += 1
                current_streak_active_date -= timedelta(days=1)
            elif d < current_streak_active_date:
                 # Streak broken before reaching this date d
                break
        current_streak = temp_current_streak

        # If the most recent entry was not today, and it was yesterday, current streak is valid.
        # If most recent was today, it is valid.
        # If most recent was before yesterday, current streak is 0. This is handled by initial check.
        if unique_dates[-1] < today - timedelta(days=1):
            current_streak = 0

    return current_streak, longest_streak


async def get_user_stats_service(
    db: SupabaseClient,
    user_id: str
) -> UserStatsResponse:
    """Orchestrates fetching and calculating all user stats."""
    daily_word_counts = await get_daily_word_counts(db, user_id)
    language_stats, total_words = await get_language_breakdown(db, user_id)

    all_dates = await get_all_entry_dates(db, user_id)
    current_s, longest_s = calculate_streaks(all_dates)

    streak_data = StreakData(
        current=current_s,
        longest=longest_s,
        totalWords=total_words # This needs to be the grand total words from language_breakdown
    )

    return UserStatsResponse(
        wordCounts=daily_word_counts,
        languageBreakdown=language_stats,
        streak=streak_data
    )


# --- Vocabulary and review progress ------------------------------------------


def notebook_summary(words: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """Notebook counts by state. Ignored words are counted but kept out of the total."""
    counts = {status: 0 for status in VOCAB_STATUSES}
    for word in words:
        state = word.get("status") or "new"
        counts[state] = counts.get(state, 0) + 1
    counts["total"] = sum(counts[status] for status in VOCAB_STATUSES if status != "ignored")
    return counts


def notebook_trend(
    words: Sequence[Mapping[str, Any]], now: datetime, days: int = TREND_DAYS
) -> List[Dict[str, Any]]:
    """Notebook size at the end of each of the last ``days`` days, oldest first.

    The status a word had on a past day is not stored, so the trend counts the words
    that had been saved by then and are not ignored today.
    """
    active = [word for word in words if word.get("status") != "ignored"]
    trend = []
    for offset in range(days - 1, -1, -1):
        day = day_start(now) - timedelta(days=offset)
        end = day + timedelta(days=1)
        count = 0
        for word in active:
            created = aware(word.get("created_at"))
            if created is not None and created < end:
                count += 1
        trend.append({"date": day.date().isoformat(), "count": count})
    return trend


def encounter_summary(
    words: Sequence[Mapping[str, Any]],
    encounters: Sequence[Mapping[str, Any]],
    cards: Sequence[Mapping[str, Any]],
    logs: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """How the notebook's words were met: encounter kinds, reviews, and the mean per word."""
    word_ids = {word.get("id") for word in words if word.get("status") != "ignored"}
    card_words = {card.get("id"): card.get("word_id") for card in cards}
    per_word: Dict[Any, int] = {word_id: 0 for word_id in word_ids}
    by_kind = {kind: 0 for kind in ENCOUNTER_KINDS}
    used_ok: set = set()

    for encounter in encounters:
        word_id = encounter.get("word_id")
        if word_id not in word_ids:
            continue
        kind = encounter.get("kind")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        per_word[word_id] = per_word.get(word_id, 0) + 1
        if kind == "used_ok":
            used_ok.add(word_id)

    reviews = 0
    for log in logs:
        word_id = card_words.get(log.get("card_id"))
        if word_id in word_ids:
            reviews += 1
            per_word[word_id] = per_word.get(word_id, 0) + 1

    total = sum(per_word.values())
    return {
        "by_kind": by_kind,
        "reviews": reviews,
        "per_word": round(total / len(word_ids), 1) if word_ids else 0.0,
        "guide_min": ENCOUNTER_GUIDE_MIN,
        "guide_max": ENCOUNTER_GUIDE_MAX,
        "active_words": len(used_ok),
    }


def true_retention(logs: Sequence[Mapping[str, Any]], now: datetime) -> Optional[float]:
    """The share of reviews answered "got it", over the last month (all history when empty)."""
    window_start = day_start(now) - timedelta(days=TRUE_RETENTION_DAYS - 1)
    recent = [log for log in logs if (aware(log.get("reviewed_at")) or now) >= window_start]
    window = recent or list(logs)
    if not window:
        return None
    correct = len([log for log in window if int(log.get("rating") or 0) >= 3])
    return round(correct / len(window), 3)


def _is_waiting(card: Mapping[str, Any]) -> bool:
    """A card that enters the review queue: answered before, or a production card."""
    return bool(card.get("reps")) or card.get("card_type") == "production"


def review_summary(
    cards: Sequence[Mapping[str, Any]],
    logs: Sequence[Mapping[str, Any]],
    now: datetime,
    schedulers: Mapping[str, Any],
) -> Dict[str, Any]:
    """Review health: what is due today, the next seven days, and true retention."""
    active = [card for card in cards if not card.get("suspended_at") and _is_waiting(card)]
    due_today = len([card for card in active if (aware(card.get("due")) or now) <= now])

    forecast = []
    for offset in range(WEEK_DAYS):
        start = day_start(now) + timedelta(days=offset)
        end = start + timedelta(days=1)
        count = len([
            card for card in active
            if start <= (aware(card.get("due")) or now) < end
            or (offset == 0 and (aware(card.get("due")) or now) < start)
        ])
        forecast.append({"date": start.date().isoformat(), "count": count})

    at_risk = 0
    for card in active:
        scheduler = schedulers.get(card.get("language"))
        if scheduler is not None and is_at_risk(card, now, scheduler):
            at_risk += 1

    week_start = day_start(now) - timedelta(days=WEEK_DAYS - 1)
    week_logs = [log for log in logs if (aware(log.get("reviewed_at")) or now) >= week_start]
    minutes = sum(int(log.get("duration_ms") or 0) for log in week_logs) / 60000.0

    return {
        "due_today": due_today,
        "forecast": forecast,
        "at_risk": at_risk,
        "true_retention": true_retention(logs, now),
        "reviews_last_7_days": len(week_logs),
        "minutes_last_7_days": round(minutes, 1),
    }


def week_summary(
    entries_written: int,
    encounters: Sequence[Mapping[str, Any]],
    logs: Sequence[Mapping[str, Any]],
    now: datetime,
) -> Dict[str, Any]:
    """The week by Nation's strands: reading (input), journal (output), reviews (word study)."""
    week_start = day_start(now) - timedelta(days=WEEK_DAYS - 1)
    reading = len([
        encounter for encounter in encounters
        if encounter.get("kind") == "read" and (aware(encounter.get("created_at")) or now) >= week_start
    ])
    reviews = [log for log in logs if (aware(log.get("reviewed_at")) or now) >= week_start]
    minutes = sum(int(log.get("duration_ms") or 0) for log in reviews) / 60000.0
    total = reading + entries_written + len(reviews)
    share = round(len(reviews) / total, 3) if total else 0.0
    minutes_per_day = minutes / WEEK_DAYS
    return {
        "reading": reading,
        "journal": entries_written,
        "reviews": len(reviews),
        "review_minutes": round(minutes, 1),
        "review_share": share,
        # A gentle note when reviews start eating most of the learner's time.
        "over_budget": minutes_per_day > REVIEW_MINUTES_BUDGET
        or (share >= 0.7 and len(reviews) >= 20),
    }


def get_vocab_progress(
    user_id: str, language: Optional[str] = None, now: Optional[datetime] = None
) -> Dict[str, Any]:
    """Everything the Progress page shows for one language (or the whole notebook)."""
    now = now or datetime.now(timezone.utc)
    words = vocab_service.load_words(user_id, language)
    encounters = vocab_service.load_encounters(user_id, language)
    cards = vocab_service.load_cards(user_id, language)
    logs = vocab_service.load_review_logs(user_id, language)
    profiles = vocab_service.load_profiles(user_id)
    params = vocab_service.load_fsrs_parameters(user_id)

    desired = {
        row.get("l2"): row.get("desired_retention")
        for row in profiles if row.get("l2")
    }
    parameters = {row.get("l2"): row.get("parameters") for row in params if row.get("l2")}
    schedulers = {
        card_language: make_scheduler(desired.get(card_language), parameters.get(card_language), fuzz=False)
        for card_language in {card.get("language") for card in cards if card.get("language")}
    }

    since = day_start(now) - timedelta(days=WEEK_DAYS - 1)
    entries_written = vocab_service.count_entries_since(user_id, since)

    placement = None
    for row in profiles:
        if language and row.get("l2") == language:
            placement = row.get("placement")
            break

    encounters_block = encounter_summary(words, encounters, cards, logs)
    return {
        "language": language,
        "notebook": notebook_summary(words),
        "trend": notebook_trend(words, now),
        "active_words": encounters_block.pop("active_words"),
        "encounters": encounters_block,
        "review": review_summary(cards, logs, now, schedulers),
        "week": week_summary(entries_written, encounters, logs, now),
        "placement": placement,
        "placement_available": vocab_service.placement_available(language),
    }

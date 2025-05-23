from datetime import date, timedelta
from typing import List, Dict, Tuple, Set
from sqlalchemy.orm import Session # If using SQLAlchemy with Supabase client
from supabase_py_async import AsyncClient as SupabaseAsyncClient # Or sync client if you use that

from app.schemas.stats_schemas import WordCountStat, LanguageStat, StreakData, UserStatsResponse

async def get_daily_word_counts(db: SupabaseAsyncClient, user_id: str, days: int = 7) -> List[WordCountStat]:
    """Fetches total word counts for the last N days for a given user."""
    # TODO: Implement Supabase query
    # Example: SELECT DATE_TRUNC('day', created_at) as entry_date, SUM(word_count) as total_words
    # FROM journal_entries WHERE user_id = :user_id AND created_at >= :start_date
    # GROUP BY entry_date ORDER BY entry_date DESC LIMIT :days;
    pass

async def get_language_breakdown(db: SupabaseAsyncClient, user_id: str) -> Tuple[List[LanguageStat], int]:
    """Fetches language breakdown (counts and percentages) and total words for a user."""
    # TODO: Implement Supabase query for counts per language
    # Example: SELECT language, SUM(word_count) as total_words FROM journal_entries
    # WHERE user_id = :user_id GROUP BY language;
    # Calculate percentages and total words from the result.
    pass

async def get_all_entry_dates(db: SupabaseAsyncClient, user_id: str) -> List[date]:
    """Fetches all unique dates on which the user made entries."""
    # TODO: Implement Supabase query
    # Example: SELECT DISTINCT DATE_TRUNC('day', created_at) as entry_date FROM journal_entries
    # WHERE user_id = :user_id ORDER BY entry_date ASC;
    pass

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
    db: SupabaseAsyncClient, 
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
"""Book coverage: how many unknown words a page holds, as an estimate with soft bands.

The thresholds come from the research on comfortable reading (about 98% of running words
known is 5-6 unknown words on a paperback page; 95% is study reading at 12-15). The link
between coverage and understanding is gradual, so the bands are soft and the result is
always an estimate, never a percentage.
"""

from __future__ import annotations

from typing import Optional

COMFORTABLE_MAX = 6
STUDY_MAX = 15
HARD_MIN = 25
# How many finished sessions in a row must be hard before an easier book is suggested.
STAYS_HARD_SESSIONS = 3
# A marked word that comes back this many times is "recurring" at the end of a session.
RECURRING_MARKS = 2
# Statuses whose words the learner already has, so they do not count as unknown on a page.
HAVE_STATUSES = frozenset({"known", "mastered", "ignored"})

BANDS = ("comfortable", "study", "demanding", "hard")


def band_for(unknown_per_page: Optional[float]) -> Optional[str]:
    """The soft band for a number of unknown words per page; None when it is not known."""
    if unknown_per_page is None:
        return None
    if unknown_per_page <= COMFORTABLE_MAX:
        return "comfortable"
    if unknown_per_page <= STUDY_MAX:
        return "study"
    if unknown_per_page < HARD_MIN:
        return "demanding"
    return "hard"


def pages_read(page_from: Optional[int], page_to: Optional[int]) -> Optional[int]:
    """Pages covered by a session, or None when either end is unknown."""
    if not page_from or not page_to or page_to < page_from:
        return None
    return page_to - page_from + 1


def words_per_page(words_marked: int, pages: Optional[int]) -> Optional[float]:
    if not pages:
        return None
    return round(words_marked / pages, 1)


def stays_hard(session_rates: list[Optional[float]]) -> bool:
    """True when the latest sessions with a known rate were all in the hard band."""
    rates = [rate for rate in session_rates if rate is not None][-STAYS_HARD_SESSIONS:]
    return len(rates) == STAYS_HARD_SESSIONS and all(band_for(rate) == "hard" for rate in rates)


def page_estimate(candidate_statuses: list[Optional[str]], page_words: int) -> dict:
    """Estimate unknown words on one photographed page.

    ``candidate_statuses`` has one entry per pre-highlighted word: the learner's notebook
    state for it, or None when it is not in the notebook. Words the learner already has are
    not unknown.
    """
    unknown = sum(1 for status in candidate_statuses if status not in HAVE_STATUSES)
    return {"unknown_estimate": unknown, "page_words": page_words, "band": band_for(unknown)}

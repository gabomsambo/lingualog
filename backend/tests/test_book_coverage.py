"""Page coverage is an estimate with soft bands, never a percentage."""

import pytest

from book_coverage import band_for, page_estimate, pages_read, stays_hard, words_per_page


@pytest.mark.parametrize(
    ("unknown", "band"),
    [(0, "comfortable"), (6, "comfortable"), (6.5, "study"), (15, "study"), (16, "demanding"), (24.9, "demanding"),
     (25, "hard"), (80, "hard"), (None, None)],
)
def test_bands_follow_the_research_thresholds(unknown, band):
    assert band_for(unknown) == band


def test_pages_read_needs_both_ends_in_order():
    assert pages_read(37, 52) == 16
    assert pages_read(5, 5) == 1
    assert pages_read(None, 5) is None and pages_read(9, 3) is None


def test_words_per_page_rounds_and_needs_pages():
    assert words_per_page(14, 16) == 0.9
    assert words_per_page(14, None) is None


def test_a_book_stays_hard_only_after_three_hard_sessions_in_a_row():
    assert not stays_hard([30, 30])
    assert stays_hard([5, 30, 31, 40])
    assert not stays_hard([30, 30, 10])
    assert stays_hard([30, None, 30, 30])


def test_the_page_estimate_leaves_out_words_the_learner_already_has():
    estimate = page_estimate(["known", None, "new", "mastered", "learning", "ignored"], page_words=140)
    assert estimate == {"unknown_estimate": 3, "page_words": 140, "band": "comfortable"}

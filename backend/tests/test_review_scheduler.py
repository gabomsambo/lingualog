"""FSRS scheduling transitions, derived word states and session composition."""

from datetime import datetime, timedelta, timezone

import pytest

import review_scheduler as rs

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
SCHEDULER = rs.make_scheduler(0.90, fuzz=False)


def new_card(**changes):
    base = {
        "id": "card-1", "word_id": "word-1", "language": "es", "card_type": "recognition",
        "state": 1, "step": None, "stability": None, "difficulty": None, "stability_fast": None,
        "due": NOW.isoformat(), "last_review": None, "reps": 0, "lapses": 0, "suspended_at": None,
        "created_at": NOW.isoformat(),
    }
    return {**base, **changes}


def apply(row, rating, when):
    outcome = rs.schedule_review(row, rating, when, SCHEDULER)
    merged = {
        **row,
        **{key: value for key, value in outcome.card.items() if key != "lapsed"},
        "reps": row["reps"] + 1,
        "lapses": row["lapses"] + int(outcome.card["lapsed"]),
    }
    return merged, outcome


def test_new_card_passes_through_learning_steps_before_review():
    first, outcome = apply(new_card(), "got_it", NOW)
    assert first["state"] == 1 and first["step"] == 1
    assert rs.aware(first["due"]) - NOW == timedelta(minutes=10)
    assert outcome.requeue is True

    second, outcome = apply(first, "got_it", rs.aware(first["due"]))
    assert second["state"] == 2 and second["step"] is None
    assert second["stability"] > 0
    assert rs.aware(second["due"]) - rs.aware(first["due"]) >= timedelta(days=1)
    assert outcome.requeue is False


def test_again_on_a_new_card_restarts_the_first_step():
    card, outcome = apply(new_card(), "again", NOW)
    assert card["state"] == 1 and card["step"] == 0
    assert rs.aware(card["due"]) - NOW == timedelta(minutes=1)
    assert outcome.requeue is True


def test_again_on_a_review_card_is_a_lapse_into_relearning():
    reviewed = new_card(
        state=2, stability=12.0, difficulty=5.0, reps=4,
        last_review=(NOW - timedelta(days=12)).isoformat(), due=NOW.isoformat(),
    )
    lapsed, outcome = apply(reviewed, "again", NOW)
    assert lapsed["state"] == 3
    assert lapsed["lapses"] == 1
    assert lapsed["stability"] < reviewed["stability"]
    assert outcome.card["lapsed"] is True
    assert outcome.requeue is True


def test_got_it_on_a_review_card_is_not_a_lapse():
    reviewed = new_card(
        state=2, stability=12.0, difficulty=5.0, reps=4,
        last_review=(NOW - timedelta(days=12)).isoformat(), due=NOW.isoformat(),
    )
    grown, outcome = apply(reviewed, "got_it", NOW)
    assert grown["state"] == 2
    assert grown["stability"] > reviewed["stability"]
    assert outcome.card["lapsed"] is False


def test_log_row_records_the_two_button_rating():
    _, again = apply(new_card(), "again", NOW)
    _, got_it = apply(new_card(), "got_it", NOW)
    assert again.log["rating"] == 1
    assert got_it.log["rating"] == 3
    assert got_it.log["source"] == "review"


def test_one_correct_answer_never_makes_a_word_known():
    """Karpicke and Roediger: dropping a word after one recall keeps ~33% a week later."""
    card, _ = apply(new_card(), "got_it", NOW)
    assert rs.derived_status("learning", card["stability"]) == "learning"
    assert rs.aware(card["due"]) > NOW


def test_a_word_becomes_known_only_after_repeated_spaced_recall():
    row, when, reviews = new_card(), NOW, 0
    status = "learning"
    while status != "known":
        row, _ = apply(row, "got_it", when)
        when = rs.aware(row["due"])
        status = rs.derived_status(status, row["stability"])
        reviews += 1
        assert reviews < 20
    assert reviews >= 4
    assert row["stability"] >= rs.KNOWN_STABILITY_DAYS


@pytest.mark.parametrize("current", ["mastered", "ignored"])
def test_derived_status_never_overwrites_a_locked_state(current):
    assert rs.derived_status(current, 90.0) == current
    assert rs.derived_status(current, 1.0) == current


def test_a_lapse_can_move_a_known_word_back_to_learning():
    assert rs.derived_status("known", 25.0) == "known"
    assert rs.derived_status("known", 6.0) == "learning"


def test_higher_desired_retention_schedules_sooner():
    card = new_card(
        state=2, stability=20.0, difficulty=5.0, reps=5,
        last_review=(NOW - timedelta(days=20)).isoformat(),
    )
    relaxed = rs.schedule_review(card, "got_it", NOW, rs.make_scheduler(0.80, fuzz=False))
    strict = rs.schedule_review(card, "got_it", NOW, rs.make_scheduler(0.95, fuzz=False))
    assert rs.aware(strict.card["due"]) < rs.aware(relaxed.card["due"])


@pytest.mark.parametrize("value,expected", [(0.5, 0.80), (0.99, 0.95), (0.9, 0.9), ("x", 0.9), (None, 0.9)])
def test_desired_retention_is_clamped_to_the_allowed_range(value, expected):
    assert rs.clamp_retention(value) == expected


def test_custom_parameters_are_used_only_when_complete_and_in_bounds():
    defaults = rs.Scheduler().parameters
    custom = tuple(value * 1.05 for value in defaults)
    assert rs.make_scheduler(0.9, custom).parameters == custom
    assert rs.make_scheduler(0.9, [0.5, 0.5]).parameters == defaults
    assert rs.make_scheduler(0.9, [99.0] * rs.PARAMETER_COUNT).parameters == defaults


def reviewed(**changes):
    base = {
        "state": 2, "stability": 5.0, "difficulty": 5.0, "reps": 3,
        "last_review": (NOW - timedelta(days=30)).isoformat(),
        "due": (NOW - timedelta(days=25)).isoformat(),
    }
    return new_card(**{**base, **changes})


def test_at_risk_is_due_and_below_eighty_percent_retrievability():
    assert rs.is_at_risk(reviewed(), NOW, SCHEDULER) is True
    assert rs.retrievability(reviewed(), NOW, SCHEDULER) < rs.AT_RISK_RETRIEVABILITY


def test_not_due_or_never_reviewed_or_suspended_is_not_at_risk():
    not_due = reviewed(due=(NOW + timedelta(days=2)).isoformat())
    assert rs.is_at_risk(not_due, NOW, SCHEDULER) is False
    assert rs.is_at_risk(new_card(), NOW, SCHEDULER) is False
    assert rs.is_at_risk(reviewed(suspended_at=NOW.isoformat()), NOW, SCHEDULER) is False


def test_production_card_joins_once_recognition_has_held_a_week():
    assert rs.production_card_due({"state": 2, "stability": 7.0}) is True
    assert rs.production_card_due({"state": 2, "stability": 6.9}) is False
    assert rs.production_card_due({"state": 1, "stability": 30.0}) is False
    assert rs.production_card_due({"state": 2, "stability": None}) is False


# --- Session composition -------------------------------------------------------


def cards(reviews=0, new=0, overdue_days=3):
    rows = []
    for index in range(reviews):
        due = NOW - timedelta(days=overdue_days, hours=index)
        rows.append(reviewed(id=f"r{index}", word_id=f"rw{index}", due=due.isoformat(),
                             last_review=(due - timedelta(days=5)).isoformat()))
    for index in range(new):
        rows.append(new_card(id=f"n{index}", word_id=f"nw{index}",
                             created_at=(NOW - timedelta(hours=new - index)).isoformat()))
    return rows


def plan(rows, **overrides):
    options = {"daily_new_words": 10, "reviewed_new_today": 0, "reviews_today": 0}
    return rs.plan_session(rows, NOW, SCHEDULER, **{**options, **overrides})


def ids(session):
    return [card["id"] for card in session.cards]


def test_new_words_are_capped_by_the_daily_limit():
    session = plan(cards(new=15))
    assert len(session.cards) == 10
    assert session.new_available == 15
    assert session.new_remaining == 10


def test_new_words_already_started_today_use_up_the_limit():
    assert len(plan(cards(new=15), reviewed_new_today=4).cards) == 6
    assert plan(cards(new=15), reviewed_new_today=10).cards == []
    assert plan(cards(new=15), reviewed_new_today=25).new_remaining == 0


def test_the_limit_is_per_learner_setting():
    assert len(plan(cards(new=30), daily_new_words=3).cards) == 3


def test_new_words_come_oldest_first_and_after_reviews():
    session = plan(cards(reviews=3, new=3))
    assert ids(session)[:3] == ["r0", "r1", "r2"] or set(ids(session)[:3]) == {"r0", "r1", "r2"}
    assert ids(session)[3:] == ["n0", "n1", "n2"]


def test_a_session_is_twenty_cards_and_reviews_win_over_new_words():
    session = plan(cards(reviews=25, new=10))
    assert len(session.cards) == rs.SESSION_SIZE
    assert all(card["id"].startswith("r") for card in session.cards)
    assert session.due == 25


def test_new_words_fill_what_the_reviews_leave_of_the_session():
    session = plan(cards(reviews=15, new=10))
    assert len(session.cards) == 20
    assert [c["id"] for c in session.cards if c["id"].startswith("n")] == ["n0", "n1", "n2", "n3", "n4"]


def test_the_most_likely_forgotten_review_comes_first():
    stale = reviewed(id="stale", due=(NOW - timedelta(days=40)).isoformat(),
                     last_review=(NOW - timedelta(days=60)).isoformat())
    fresh = reviewed(id="fresh", due=(NOW - timedelta(hours=1)).isoformat(),
                     last_review=(NOW - timedelta(days=6)).isoformat())
    assert ids(plan([fresh, stale])) == ["stale", "fresh"]


def test_cards_not_yet_due_and_suspended_cards_are_left_out():
    later = reviewed(id="later", due=(NOW + timedelta(days=1)).isoformat())
    paused = reviewed(id="paused", suspended_at=NOW.isoformat())
    session = plan([later, paused, reviewed(id="due")])
    assert ids(session) == ["due"]
    assert session.due == 1


def test_a_production_card_is_a_review_not_a_new_word():
    production = new_card(id="p1", card_type="production", due=(NOW - timedelta(hours=1)).isoformat())
    session = plan([production] + cards(new=2), reviewed_new_today=10)
    assert ids(session) == ["p1"]
    assert session.new_remaining == 0


def test_a_production_card_not_yet_due_waits():
    production = new_card(id="p1", card_type="production", due=(NOW + timedelta(days=1)).isoformat())
    assert plan([production]).cards == []


def test_total_counts_reviews_plus_the_new_words_still_allowed_today():
    session = plan(cards(reviews=7, new=15), reviewed_new_today=6)
    assert session.total == 7 + 4


def test_a_large_backlog_suggests_catch_up_but_normal_mode_still_works():
    session = plan(cards(reviews=60))
    assert session.backlog == 60
    assert session.suggest_catchup is True
    assert len(session.cards) == rs.SESSION_SIZE
    assert plan(cards(reviews=39)).suggest_catchup is False


def test_catch_up_serves_only_reviews_and_no_new_words():
    session = plan(cards(reviews=100, new=10), mode="catchup")
    assert all(card["id"].startswith("r") for card in session.cards)
    assert session.catchup_budget == rs.CATCHUP_DAILY_REVIEWS


def test_catch_up_stops_at_the_daily_budget_so_a_backlog_drains_over_days():
    rows = cards(reviews=100)
    first = plan(rows, mode="catchup", limit=20)
    assert len(first.cards) == 20
    after_one_session = plan(rows, mode="catchup", limit=20, reviews_today=20)
    assert len(after_one_session.cards) == rs.CATCHUP_DAILY_REVIEWS - 20
    assert plan(rows, mode="catchup", limit=20, reviews_today=rs.CATCHUP_DAILY_REVIEWS).cards == []
    assert after_one_session.due == 100


def test_catch_up_rescues_the_most_forgotten_words_first():
    stale = reviewed(id="stale", due=(NOW - timedelta(days=80)).isoformat(),
                     last_review=(NOW - timedelta(days=100)).isoformat())
    session = plan(cards(reviews=50) + [stale], mode="catchup", limit=5)
    assert session.cards[0]["id"] == "stale"


def test_at_risk_count_only_includes_due_forgotten_cards():
    session = plan(cards(reviews=3, overdue_days=25))
    assert session.at_risk == 3
    assert plan(cards(reviews=3, overdue_days=0)).at_risk == 0

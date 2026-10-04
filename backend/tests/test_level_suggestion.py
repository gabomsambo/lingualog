"""Boundaries for suggested immersion changes, snooze expiry, and owner isolation."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from level_suggestion import (
    STEP_DOWN_MIN_RATIO,
    STEP_DOWN_WINDOW,
    STEP_UP_MAX_RATIO,
    STEP_UP_MIN_SCORE,
    STEP_UP_WINDOW,
    EntrySignal,
    LanguageLevel,
    Snooze,
    SupportTap,
    share_at_least,
    share_at_most,
    snooze_active,
    snooze_deadline,
    suggestions_for,
)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
USER = "user-a"
OTHER = "user-b"


def _entry(
    index: int,
    *,
    user: str = USER,
    l2: str = "es",
    score: float | None = 80,
    level: int = 2,
    status: str = "ok",
) -> EntrySignal:
    return EntrySignal(
        entry_id=f"e{index}",
        user_id=user,
        l2=l2,
        created_at=NOW - timedelta(minutes=index),
        score=score,
        immersion_level=level,
        analysis_status=status,
    )


def _level(level: int, *, user: str = USER, l2: str = "es") -> LanguageLevel:
    return LanguageLevel(user, l2, level)


def _tap(entry_id: str, kind: str = "reveal_meaning", *, user: str = USER) -> SupportTap:
    return SupportTap(user, entry_id, kind)


def _suggest(entries, taps, *, level: int = 2, l2: str = "es", snoozes=(), user: str = USER, levels=None):
    return suggestions_for(
        user,
        levels if levels is not None else [_level(level, user=user, l2=l2)],
        entries,
        taps,
        snoozes,
        NOW,
    )


def test_ratio_helpers_include_equality():
    assert STEP_DOWN_MIN_RATIO == 0.60
    assert STEP_UP_MAX_RATIO == 0.10
    assert STEP_UP_MIN_SCORE == 75
    assert share_at_least(3, 5, STEP_DOWN_MIN_RATIO)
    assert not share_at_least(2, 5, STEP_DOWN_MIN_RATIO)
    # Exactly 10% qualifies; just over does not. The live window of 8 cannot land on 10%.
    assert share_at_most(1, 10, STEP_UP_MAX_RATIO)
    assert not share_at_most(2, 10, STEP_UP_MAX_RATIO)
    assert share_at_most(0, STEP_UP_WINDOW, STEP_UP_MAX_RATIO)
    assert not share_at_most(1, STEP_UP_WINDOW, STEP_UP_MAX_RATIO)


def test_step_down_at_exact_sixty_percent():
    entries = [_entry(i) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(f"e{i}") for i in range(3)]
    found = _suggest(entries, taps, level=2)
    assert len(found) == 1
    assert found[0].direction == "down"
    assert found[0].from_level == 2
    assert found[0].to_level == 1


def test_step_down_below_sixty_percent_is_quiet():
    entries = [_entry(i, level=1) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(f"e{i}", "rescue_note") for i in range(2)]
    assert _suggest(entries, taps, level=1) == []


def test_step_down_ignores_support_that_is_not_meaning_or_rescue():
    entries = [_entry(i) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(f"e{i}", "reveal_example") for i in range(STEP_DOWN_WINDOW)]
    assert _suggest(entries, taps, level=2) == []


def test_step_down_needs_five_entries():
    entries = [_entry(i) for i in range(STEP_DOWN_WINDOW - 1)]
    taps = [_tap(row.entry_id) for row in entries]
    assert _suggest(entries, taps, level=2) == []


def test_step_down_does_not_apply_at_level_zero():
    entries = [_entry(i, level=0) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(row.entry_id) for row in entries]
    assert _suggest(entries, taps, level=0) == []


def test_step_up_at_exact_ten_percent(monkeypatch):
    monkeypatch.setattr("level_suggestion.STEP_UP_WINDOW", 10)
    entries = [_entry(i, level=1, score=STEP_UP_MIN_SCORE) for i in range(10)]
    taps = [_tap("e0", "reveal_rewrite_gloss")]
    found = _suggest(entries, taps, level=1)
    assert len(found) == 1
    assert found[0].direction == "up"
    assert found[0].to_level == 2


def test_step_up_just_over_ten_percent(monkeypatch):
    monkeypatch.setattr("level_suggestion.STEP_UP_WINDOW", 10)
    entries = [_entry(i, level=1, score=90) for i in range(10)]
    taps = [_tap("e0"), _tap("e1", "rescue_note")]
    assert _suggest(entries, taps, level=1) == []


def test_step_up_score_boundary_is_inclusive():
    entries = [_entry(i, score=STEP_UP_MIN_SCORE) for i in range(STEP_UP_WINDOW)]
    found = _suggest(entries, [], level=2)
    assert len(found) == 1
    assert found[0].direction == "up"
    assert found[0].to_level == 3


def test_step_up_score_just_below_threshold_is_quiet():
    entries = [_entry(i, score=STEP_UP_MIN_SCORE - 1) for i in range(STEP_UP_WINDOW)]
    assert _suggest(entries, [], level=2) == []


def test_step_up_one_of_eight_is_over_ten_percent():
    entries = [_entry(i, level=1, score=90) for i in range(STEP_UP_WINDOW)]
    assert _suggest(entries, [_tap("e0", "reveal_example")], level=1) == []


def test_step_up_needs_eight_entries():
    entries = [_entry(i, level=1, score=90) for i in range(STEP_UP_WINDOW - 1)]
    assert _suggest(entries, [], level=1) == []


def test_step_up_does_not_apply_at_level_three():
    entries = [_entry(i, level=3, score=90) for i in range(STEP_UP_WINDOW)]
    assert _suggest(entries, [], level=3) == []


def test_older_entries_outside_the_window_do_not_count():
    entries = [_entry(i) for i in range(STEP_DOWN_WINDOW + 3)]
    # The three newest entries (e0-e2) have no taps. Older ones do.
    taps = [_tap(f"e{i}") for i in range(3, STEP_DOWN_WINDOW + 3)]
    assert _suggest(entries, taps, level=2) == []


def test_snooze_hides_until_deadline_then_returns():
    entries = [_entry(i) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(f"e{i}") for i in range(3)]
    hidden = Snooze(USER, "es", NOW + timedelta(days=1))
    assert _suggest(entries, taps, snoozes=[hidden]) == []
    expired = Snooze(USER, "es", NOW)
    found = _suggest(entries, taps, snoozes=[expired])
    assert len(found) == 1
    assert not snooze_active(NOW, NOW)
    assert snooze_active(NOW + timedelta(seconds=1), NOW)
    assert snooze_deadline(NOW) - NOW == timedelta(days=7)


def test_owner_isolation_ignores_another_learners_history():
    entries = [_entry(i, user=OTHER) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(f"e{i}", user=OTHER) for i in range(STEP_DOWN_WINDOW)]
    levels = [_level(2, user=USER), _level(2, user=OTHER)]
    own = _suggest(entries, taps, user=USER, levels=levels)
    theirs = _suggest(entries, taps, user=OTHER, levels=levels)
    assert own == []
    assert len(theirs) == 1
    assert theirs[0].l2 == "es"


def test_accepting_does_not_cascade_on_history_from_the_old_level():
    entries = [_entry(i, level=2) for i in range(STEP_DOWN_WINDOW)]
    taps = [_tap(f"e{i}") for i in range(3)]
    assert _suggest(entries, taps, level=2)[0].to_level == 1
    assert _suggest(entries, taps, level=1) == []

    calm = [_entry(i, level=0, score=90) for i in range(STEP_UP_WINDOW)]
    assert _suggest(calm, [], level=0)[0].to_level == 1
    assert _suggest(calm, [], level=1) == []


def test_window_counts_only_entries_at_the_current_level():
    older = [_entry(i, level=1) for i in range(10, 10 + STEP_DOWN_WINDOW)]
    newer = [_entry(i, level=2) for i in range(STEP_DOWN_WINDOW - 1)]
    taps = [_tap(row.entry_id) for row in older + newer]
    assert _suggest(older + newer, taps, level=2) == []
    assert _suggest(older + newer + [_entry(5, level=2)], taps, level=2)[0].direction == "down"


@pytest.mark.parametrize("status", ["failed", "mock", "legacy"])
def test_entries_without_a_real_score_are_not_evidence(status):
    unscored = [_entry(i, level=1, score=None if status == "failed" else 90, status=status) for i in range(7)]
    scored = [_entry(10, level=1, score=90)]
    assert _suggest(unscored + scored, [], level=1) == []

    down = [_entry(i, status=status) for i in range(STEP_DOWN_WINDOW - 1)] + [_entry(9)]
    assert _suggest(down, [_tap(row.entry_id) for row in down], level=2) == []


def test_returning_to_a_level_ignores_history_from_before_the_last_change():
    old = [_entry(i, level=2) for i in range(100, 100 + STEP_DOWN_WINDOW)]
    taps = [_tap(row.entry_id) for row in old[:3]]
    assert _suggest(old, taps, level=2)[0].to_level == 1

    returned = [LanguageLevel(USER, "es", 2, since=NOW - timedelta(minutes=10))]
    assert _suggest(old, taps, levels=returned) == []

    fresh = [_entry(i, level=2) for i in range(STEP_DOWN_WINDOW)]
    fresh_taps = [_tap(row.entry_id) for row in fresh[:3]]
    assert _suggest(old + fresh, taps + fresh_taps, levels=returned)[0].to_level == 1


def test_entry_without_score_does_not_fill_a_window():
    entries = [_entry(i, level=1, score=90) for i in range(STEP_UP_WINDOW - 1)]
    entries.append(_entry(20, level=1, score=None))
    assert _suggest(entries, [], level=1) == []


class _Response:
    def __init__(self, data):
        self.data = data


class FakeSupabase:
    """Returns every stored row. Callers must filter by user_id themselves."""

    def __init__(self, tables):
        self.tables = tables
        self.calls = []
        self._name = ""
        self._filters = []

    def table(self, name):
        self._name = name
        self._filters = []
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    @property
    def not_(self):
        return self

    def is_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def gt(self, *_args, **_kwargs):
        return self

    def neq(self, *_args, **_kwargs):
        return self

    def in_(self, key, values):
        self._filters.append((key, tuple(values)))
        return self

    def execute(self):
        self.calls.append((self._name, tuple(self._filters)))
        return _Response(list(self.tables.get(self._name, [])))

    def upsert(self, row, on_conflict=None):
        self.calls.append(("upsert", self._name, row, on_conflict))
        return self

    def delete(self):
        self._filters = []
        self.calls.append(("delete", self._name))
        return self


def _history_tables():
    created = NOW.isoformat()
    entries = []
    events = []
    for index in range(5):
        entries.append(
            {
                "id": f"a{index}",
                "user_id": USER,
                "target_language": "es",
                "language": "es",
                "score": 40,
                "created_at": (NOW - timedelta(minutes=index)).isoformat(),
                "analysis_status": "ok",
                "policy_snapshot": {"v": 1, "immersion_level": 2},
            }
        )
    for index in range(3):
        events.append({"user_id": USER, "entry_id": f"a{index}", "kind": "reveal_meaning"})
    # Another learner's perfect step-down must not leak.
    for index in range(5):
        entries.append(
            {
                "id": f"b{index}",
                "user_id": OTHER,
                "target_language": "es",
                "language": "es",
                "score": 40,
                "created_at": created,
                "analysis_status": "ok",
                "policy_snapshot": {"v": 1, "immersion_level": 2},
            }
        )
        events.append({"user_id": OTHER, "entry_id": f"b{index}", "kind": "rescue_note"})
    return {
        "user_language_profiles": [
            {"user_id": USER, "l2": "es", "immersion_level": 2, "proficiency": "B1"},
            {"user_id": OTHER, "l2": "es", "immersion_level": 2, "proficiency": "C2"},
        ],
        "user_settings": [
            {"user_id": USER, "default_target_lang": "es"},
            {"user_id": OTHER, "default_target_lang": "es"},
        ],
        "journal_entries": entries,
        "support_events": events,
        "level_suggestion_snoozes": [],
    }


def test_service_scopes_queries_and_results_to_the_caller():
    from app.services.level_suggestion_service import current_suggestions

    fake = FakeSupabase(_history_tables())
    found = current_suggestions(USER, supabase=fake)
    assert found == [{"l2": "es", "direction": "down", "from_level": 2, "to_level": 1}]
    assert current_suggestions(OTHER, supabase=fake)[0]["from_level"] == 2
    for name, filters in fake.calls:
        if name in {"upsert", "delete"}:
            continue
        assert ("user_id", USER) in filters or ("user_id", OTHER) in filters


def test_service_reads_taps_only_for_the_window_entries():
    from app.services.level_suggestion_service import current_suggestions

    tables = _history_tables()
    for row in tables["journal_entries"]:
        if row["user_id"] == USER and row["id"] in {"a3", "a4"}:
            row["policy_snapshot"] = {"v": 1, "immersion_level": 1}
    fake = FakeSupabase(tables)
    assert current_suggestions(USER, supabase=fake) == []
    tap_filters = [dict(filters) for name, filters in fake.calls if name == "support_events"]
    assert tap_filters == [{"user_id": USER, "entry_id": ("a0", "a1", "a2")}]


def test_accept_updates_only_the_callers_profile(monkeypatch):
    from app.services import level_suggestion_service as service

    saved = []
    fake = FakeSupabase(_history_tables())
    monkeypatch.setattr(
        service,
        "fetch_language_profile",
        lambda user_id, l2: {
            "user_id": user_id,
            "l2": l2,
            "immersion_level": 2,
            "proficiency": "B1" if user_id == USER else "C2",
        },
    )
    monkeypatch.setattr(
        service,
        "save_user_settings",
        lambda user_id, settings, profiles: saved.append((user_id, settings, profiles)),
    )

    result = service.accept_level_suggestion(USER, "es", supabase=fake)
    assert result["to_level"] == 1
    assert saved == [
        (
            USER,
            {"immersion_level": 1},
            [{"l2": "es", "immersion_level": 1, "proficiency": "B1"}],
        )
    ]
    assert ("delete", "level_suggestion_snoozes") in [(call[0], call[1]) for call in fake.calls if call[0] == "delete"]


def test_accept_leaves_legacy_immersion_when_language_is_not_the_default(monkeypatch):
    from app.services import level_suggestion_service as service

    tables = _history_tables()
    tables["user_settings"] = [{"user_id": USER, "default_target_lang": "ja"}]
    saved = []
    monkeypatch.setattr(
        service,
        "fetch_language_profile",
        lambda user_id, l2: {"user_id": user_id, "l2": l2, "immersion_level": 2, "proficiency": "B1"},
    )
    monkeypatch.setattr(
        service,
        "save_user_settings",
        lambda user_id, settings, profiles: saved.append((user_id, settings, profiles)),
    )
    service.accept_level_suggestion(USER, "es", supabase=FakeSupabase(tables))
    assert saved[0][1] == {}
    assert saved[0][2][0]["immersion_level"] == 1


def test_studied_language_without_a_profile_row_gets_a_suggestion(monkeypatch):
    from app.services import level_suggestion_service as service

    tables = _history_tables()
    tables["user_settings"] = [
        {
            "user_id": USER,
            "default_target_lang": "es",
            "target_languages": ["es", "fr"],
            "native_lang": "en",
            "immersion_level": 2,
        }
    ]
    for index in range(STEP_DOWN_WINDOW):
        tables["journal_entries"].append(
            {
                "id": f"f{index}",
                "user_id": USER,
                "target_language": "fr",
                "language": "fr",
                "score": 50,
                "created_at": (NOW - timedelta(hours=1, minutes=index)).isoformat(),
                "analysis_status": "ok",
                "policy_snapshot": {"v": 1, "immersion_level": 2},
            }
        )
    tables["support_events"] += [
        {"user_id": USER, "entry_id": f"f{index}", "kind": "rescue_note"} for index in range(3)
    ]
    found = service.current_suggestions(USER, supabase=FakeSupabase(tables), now=NOW)
    assert {"l2": "fr", "direction": "down", "from_level": 2, "to_level": 1} in found
    assert [row["l2"] for row in found] == ["es", "fr"]

    saved = []
    monkeypatch.setattr(service, "fetch_language_profile", lambda user_id, l2: None)
    monkeypatch.setattr(
        service,
        "save_user_settings",
        lambda user_id, settings, profiles: saved.append((user_id, settings, profiles)),
    )
    service.accept_level_suggestion(USER, "fr", supabase=FakeSupabase(tables))
    assert saved == [(USER, {}, [{"l2": "fr", "immersion_level": 1, "proficiency": "A2"}])]


def _french_entry(key: str, minutes_ago: int, level: int, score: float) -> dict:
    return {
        "id": key,
        "user_id": USER,
        "target_language": "fr",
        "language": "fr",
        "score": score,
        "created_at": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
        "analysis_status": "ok",
        "policy_snapshot": {"v": 1, "immersion_level": level},
    }


def test_studied_language_without_a_profile_row_ignores_history_from_before_its_level_changed():
    from app.services.level_suggestion_service import current_suggestions

    tables = _history_tables()
    tables["user_settings"] = [
        {"user_id": USER, "default_target_lang": "es", "target_languages": ["es", "fr"], "immersion_level": 2}
    ]
    old = [_french_entry(f"old{i}", 300 + i, 2, 50) for i in range(STEP_DOWN_WINDOW)]
    calm = [_french_entry(f"calm{i}", 200 + i, 1, 90) for i in range(STEP_UP_WINDOW)]
    tables["journal_entries"] += old + calm
    tables["support_events"] += [
        {"user_id": USER, "entry_id": row["id"], "kind": "reveal_meaning"} for row in old[:3]
    ]
    found = current_suggestions(USER, supabase=FakeSupabase(tables), now=NOW)
    assert [row["l2"] for row in found] == ["es"]

    fresh = [_french_entry(f"new{i}", 100 + i, 2, 50) for i in range(STEP_DOWN_WINDOW)]
    tables["journal_entries"] += fresh
    tables["support_events"] += [
        {"user_id": USER, "entry_id": row["id"], "kind": "reveal_meaning"} for row in fresh[:3]
    ]
    found = current_suggestions(USER, supabase=FakeSupabase(tables), now=NOW)
    assert {"l2": "fr", "direction": "down", "from_level": 2, "to_level": 1} in found


def test_entry_only_and_native_languages_get_no_suggestion():
    from app.services.level_suggestion_service import current_suggestions

    tables = _history_tables()
    tables["user_settings"] = [
        {
            "user_id": USER,
            "default_target_lang": "es",
            "target_languages": ["es", "en"],
            "native_lang": "en",
            "immersion_level": 2,
        }
    ]
    # A former default that still has a profile row stays studied.
    tables["user_language_profiles"].append(
        {"user_id": USER, "l2": "ja", "immersion_level": 2, "proficiency": "B1"}
    )
    tables["journal_entries"] += [_french_entry(f"ja{i}", 40 + i, 2, 40) for i in range(STEP_DOWN_WINDOW)]
    for row in tables["journal_entries"]:
        if str(row["id"]).startswith("ja"):
            row["target_language"] = "ja"
            row["language"] = "ja"
    tables["support_events"] += [
        {"user_id": USER, "entry_id": f"ja{index}", "kind": "reveal_meaning"} for index in range(3)
    ]
    # French exists only on entries. English is the native language, even though it is listed.
    tables["journal_entries"] += [_french_entry(f"fr{i}", 20 + i, 2, 40) for i in range(STEP_DOWN_WINDOW)]
    tables["journal_entries"] += [_french_entry(f"en{i}", 10 + i, 2, 40) for i in range(STEP_DOWN_WINDOW)]
    for row in tables["journal_entries"]:
        if str(row["id"]).startswith("en"):
            row["target_language"] = "en"
            row["language"] = "en"
    tables["support_events"] += [
        {"user_id": USER, "entry_id": f"fr{index}", "kind": "reveal_meaning"} for index in range(3)
    ]
    tables["support_events"] += [
        {"user_id": USER, "entry_id": f"en{index}", "kind": "reveal_meaning"} for index in range(3)
    ]
    found = current_suggestions(USER, supabase=FakeSupabase(tables), now=NOW)
    assert [row["l2"] for row in found] == ["es", "ja"]


def test_dismiss_snoozes_for_seven_days_and_then_expires(monkeypatch):
    from app.services import level_suggestion_service as service

    fake = FakeSupabase(_history_tables())
    dismissed = service.dismiss_level_suggestion(USER, "es", supabase=fake, now=NOW)
    until = datetime.fromisoformat(dismissed["snoozed_until"])
    assert until - NOW == timedelta(days=7)
    upserts = [call for call in fake.calls if call[0] == "upsert"]
    assert upserts[0][2]["user_id"] == USER
    assert upserts[0][2]["l2"] == "es"

    tables = _history_tables()
    tables["level_suggestion_snoozes"] = [
        {"user_id": USER, "l2": "es", "snoozed_until": (NOW + timedelta(days=7)).isoformat()}
    ]
    assert service.current_suggestions(USER, supabase=FakeSupabase(tables), now=NOW) == []
    later = NOW + timedelta(days=7)
    assert service.current_suggestions(USER, supabase=FakeSupabase(tables), now=later)[0]["direction"] == "down"


def test_accept_unknown_suggestion_raises():
    from app.services.level_suggestion_service import NoLevelSuggestion, accept_level_suggestion

    with pytest.raises(NoLevelSuggestion):
        accept_level_suggestion(USER, "fr", supabase=FakeSupabase(_history_tables()))


@pytest.fixture
def client():
    from server import app

    return TestClient(app)


def test_endpoints_require_the_owner_header(client, monkeypatch):
    from app.routers import level_suggestions as routes

    seen = {}

    def accept(user_id, l2):
        seen["accept"] = user_id
        return {"l2": l2, "direction": "down", "from_level": 2, "to_level": 1}

    def dismiss(user_id, l2):
        seen["dismiss"] = user_id
        return {"l2": l2, "snoozed_until": NOW.isoformat()}

    monkeypatch.setattr(routes, "current_suggestions", lambda user_id: seen.setdefault("list", user_id) and [])
    monkeypatch.setattr(routes, "accept_level_suggestion", accept)
    monkeypatch.setattr(routes, "dismiss_level_suggestion", dismiss)

    assert client.get("/user/level-suggestions").status_code == 401
    assert client.post("/user/level-suggestions/es/accept").status_code == 401
    assert client.post("/user/level-suggestions/es/dismiss").status_code == 401

    listed = client.get("/user/level-suggestions", headers={"X-User-ID": USER})
    accepted = client.post("/user/level-suggestions/es/accept", headers={"X-User-ID": USER})
    dismissed = client.post("/user/level-suggestions/es/dismiss", headers={"X-User-ID": OTHER})
    assert listed.status_code == 200
    assert accepted.status_code == 200
    assert dismissed.status_code == 200
    assert seen["list"] == USER
    assert seen["accept"] == USER
    assert seen["dismiss"] == OTHER


def test_endpoint_missing_suggestion_is_404(client, monkeypatch):
    from app.routers import level_suggestions as routes
    from app.services.level_suggestion_service import NoLevelSuggestion

    def missing(user_id, l2):
        raise NoLevelSuggestion(l2)

    monkeypatch.setattr(routes, "accept_level_suggestion", missing)
    response = client.post("/user/level-suggestions/es/accept", headers={"X-User-ID": USER})
    assert response.status_code == 404

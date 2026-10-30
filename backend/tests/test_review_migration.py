"""Review migration behavior against local Supabase, rolled back after each test."""

import json
import os
import re
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

MIGRATION = (
    Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20261006000000_review_fsrs.sql"
)
DATABASE_URL = os.getenv(
    "MIGRATION_TEST_DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
)


@pytest.fixture
def cursor():
    try:
        connection = psycopg2.connect(DATABASE_URL, connect_timeout=3)
    except psycopg2.OperationalError:
        pytest.skip("local Supabase Postgres is not running")
    try:
        cursor = connection.cursor()
        # Idempotent, and rolled back with the test, so a database that has not been migrated yet works too.
        _migrate(cursor)
        yield cursor
    finally:
        connection.rollback()
        connection.close()


def _migrate(cursor):
    sql = re.sub(r"^\s*(BEGIN|COMMIT);\s*$", "", MIGRATION.read_text(), flags=re.MULTILINE)
    cursor.execute(sql)


def _user(cursor):
    user_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO auth.users (id, email) VALUES (%s, %s)", (user_id, f"{user_id}@test.invalid"))
    return user_id


def _word(cursor, user_id, status="learning", lemma="banco", language="es"):
    word_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO public.user_vocabulary (id, user_id, term, lemma, language, status) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (word_id, user_id, lemma, lemma, language, status),
    )
    return word_id


def _card(cursor, user_id, word_id, card_type="recognition", **columns):
    card_id = str(uuid.uuid4())
    values = {"id": card_id, "user_id": user_id, "word_id": word_id, "language": "es",
              "card_type": card_type, **columns}
    cursor.execute(
        f"INSERT INTO public.vocab_cards ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
        list(values.values()),
    )
    return card_id


REVIEWED = {
    "state": 2, "step": None, "stability": 12.5, "difficulty": 5.1,
    "due": "2026-11-12T10:00:00+00:00", "last_review": "2026-10-31T10:00:00+00:00", "lapsed": False,
}
LOG = {"rating": 3, "reviewed_at": "2026-10-31T10:00:00+00:00", "duration_ms": 3100, "source": "review"}


def _apply(cursor, user_id, card_id, expected_reps=0, card=REVIEWED, log=LOG):
    cursor.execute(
        "SELECT public.apply_card_review(%s, %s, %s, %s::jsonb, %s::jsonb)",
        (user_id, card_id, expected_reps, json.dumps(card), json.dumps(log)),
    )
    return cursor.fetchone()[0]


def test_words_already_in_study_get_one_recognition_card_even_when_rerun(cursor):
    user_id = _user(cursor)
    studying = _word(cursor, user_id, "learning", "banco")
    _word(cursor, user_id, "new", "mesa")
    _word(cursor, user_id, "known", "silla")

    _migrate(cursor)
    _migrate(cursor)

    cursor.execute("SELECT word_id, card_type, state, reps FROM public.vocab_cards WHERE user_id = %s", (user_id,))
    assert cursor.fetchall() == [(studying, "recognition", 1, 0)]


def test_a_word_has_at_most_one_card_of_each_type(cursor):
    user_id = _user(cursor)
    word_id = _word(cursor, user_id)
    _card(cursor, user_id, word_id)
    _card(cursor, user_id, word_id, "production")
    cursor.execute("SAVEPOINT duplicate")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _card(cursor, user_id, word_id)
    cursor.execute("ROLLBACK TO SAVEPOINT duplicate")


@pytest.mark.parametrize("columns", [{"card_type": "listening"}, {"state": 0}, {"state": 4}])
def test_cards_reject_unknown_types_and_states(cursor, columns):
    user_id = _user(cursor)
    word_id = _word(cursor, user_id)
    cursor.execute("SAVEPOINT bad")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _card(cursor, user_id, word_id, **{"card_type": "recognition", **columns})
    cursor.execute("ROLLBACK TO SAVEPOINT bad")


def test_apply_card_review_advances_the_card_and_appends_the_log(cursor):
    user_id = _user(cursor)
    card_id = _card(cursor, user_id, _word(cursor, user_id))

    updated = _apply(cursor, user_id, card_id)

    assert updated["reps"] == 1 and updated["lapses"] == 0
    assert updated["state"] == 2 and updated["stability"] == 12.5
    assert updated["first_reviewed_at"] == updated["last_review"]
    cursor.execute(
        "SELECT rating, duration_ms, source, language FROM public.vocab_review_logs WHERE card_id = %s", (card_id,)
    )
    assert cursor.fetchall() == [(3, 3100, "review", "es")]


def test_apply_card_review_counts_a_lapse_and_keeps_the_first_review_date(cursor):
    user_id = _user(cursor)
    card_id = _card(cursor, user_id, _word(cursor, user_id))
    first = _apply(cursor, user_id, card_id)
    lapsed = _apply(cursor, user_id, card_id, 1, {**REVIEWED, "state": 3, "step": 0, "lapsed": True},
                    {**LOG, "rating": 1, "reviewed_at": "2026-11-12T10:00:00+00:00"})
    assert lapsed["lapses"] == 1 and lapsed["reps"] == 2
    assert lapsed["first_reviewed_at"] == first["first_reviewed_at"]


def test_apply_card_review_refuses_a_stale_a_foreign_or_a_suspended_card(cursor):
    owner, other = _user(cursor), _user(cursor)
    card_id = _card(cursor, owner, _word(cursor, owner))
    suspended = _card(cursor, owner, _word(cursor, owner, lemma="mesa"), suspended_at="2026-10-30T00:00:00+00:00")

    assert _apply(cursor, other, card_id) is None
    assert _apply(cursor, owner, card_id, expected_reps=3) is None
    assert _apply(cursor, owner, suspended) is None
    assert _apply(cursor, owner, str(uuid.uuid4())) is None
    cursor.execute("SELECT count(*) FROM public.vocab_review_logs WHERE user_id IN (%s, %s)", (owner, other))
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT reps FROM public.vocab_cards WHERE id = %s", (card_id,))
    assert cursor.fetchone()[0] == 0

    assert _apply(cursor, owner, card_id)["reps"] == 1
    assert _apply(cursor, owner, card_id) is None


def test_review_logs_only_accept_ratings_one_to_four_and_known_sources(cursor):
    user_id = _user(cursor)
    card_id = _card(cursor, user_id, _word(cursor, user_id))
    for column, value in (("rating", 0), ("rating", 5), ("source", "guess")):
        cursor.execute("SAVEPOINT bad")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "INSERT INTO public.vocab_review_logs (user_id, card_id, language, rating, source) "
                "VALUES (%s, %s, 'es', %s, %s)",
                (user_id, card_id, value if column == "rating" else 3, value if column == "source" else "review"),
            )
        cursor.execute("ROLLBACK TO SAVEPOINT bad")


def test_deleting_a_word_removes_its_cards_and_review_history(cursor):
    user_id = _user(cursor)
    word_id = _word(cursor, user_id)
    card_id = _card(cursor, user_id, word_id)
    _apply(cursor, user_id, card_id)
    cursor.execute("DELETE FROM public.user_vocabulary WHERE id = %s", (word_id,))
    cursor.execute("SELECT count(*) FROM public.vocab_cards WHERE id = %s", (card_id,))
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT count(*) FROM public.vocab_review_logs WHERE card_id = %s", (card_id,))
    assert cursor.fetchone()[0] == 0


def test_the_review_tables_are_owner_only(cursor):
    cursor.execute(
        "SELECT tablename, count(*) FROM pg_policies WHERE schemaname = 'public' "
        "AND tablename IN ('vocab_cards', 'vocab_review_logs', 'user_fsrs_params') GROUP BY tablename"
    )
    assert dict(cursor.fetchall()) == {"vocab_cards": 4, "vocab_review_logs": 4, "user_fsrs_params": 4}
    cursor.execute(
        "SELECT relname FROM pg_class WHERE relrowsecurity AND relname IN "
        "('vocab_cards', 'vocab_review_logs', 'user_fsrs_params')"
    )
    assert len(cursor.fetchall()) == 3


def _profile(**columns):
    return json.dumps([{"l2": "es", "immersion_level": 2, "proficiency": "B1", **columns}])


def _save_profiles(cursor, user_id, profiles):
    cursor.execute("SELECT public.save_user_settings(%s, '{}'::jsonb, %s::jsonb)", (user_id, profiles))
    cursor.execute(
        "SELECT daily_new_words, desired_retention, immersion_level FROM public.user_language_profiles "
        "WHERE user_id = %s AND l2 = 'es'",
        (user_id,),
    )
    return cursor.fetchone()


def test_saving_settings_stores_review_settings_only_when_sent(cursor):
    user_id = _user(cursor)
    assert _save_profiles(cursor, user_id, _profile()) == (10, 0.9, 2)
    assert _save_profiles(cursor, user_id, _profile(daily_new_words=15, desired_retention=0.85)) == (15, 0.85, 2)
    assert _save_profiles(cursor, user_id, _profile(immersion_level=3)) == (15, 0.85, 3)
    assert _save_profiles(cursor, user_id, _profile(desired_retention=0.93)) == (15, 0.93, 2)


def test_desired_retention_cannot_leave_its_range(cursor):
    user_id = _user(cursor)
    _save_profiles(cursor, user_id, _profile())
    for value in (0.79, 0.96, 0.99):
        cursor.execute("SAVEPOINT bad")
        with pytest.raises(psycopg2.errors.CheckViolation):
            _save_profiles(cursor, user_id, _profile(desired_retention=value))
        cursor.execute("ROLLBACK TO SAVEPOINT bad")

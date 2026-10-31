"""Word bank migration behavior against local Supabase, rolled back after each test."""

import json
import os
import re
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

MIGRATION = (
    Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20261007000000_word_bank.sql"
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


def _word(cursor, user_id):
    word_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO public.user_vocabulary (id, user_id, term, lemma, language, status) "
        "VALUES (%s, %s, 'madrugar', 'madrugar', 'es', 'learning')",
        (word_id, user_id),
    )
    return word_id


def _encounter(cursor, user_id, word_id, entry_id, kind):
    cursor.execute(
        "INSERT INTO public.word_encounters (user_id, word_id, language, lemma, surface, sentence, kind, "
        "source_type, source_id) VALUES (%s, %s, 'es', 'madrugar', 'madrugué', 'Ayer madrugué.', %s, 'entry', %s)",
        (user_id, word_id, kind, entry_id),
    )


def test_entries_keep_the_chosen_words_and_their_checked_uses_and_rerunning_is_harmless(cursor):
    user_id = _user(cursor)
    _migrate(cursor)
    targets = [{"word_id": str(uuid.uuid4()), "lemma": "madrugar", "term": "madrugar", "challenge": True}]
    uses = [{"word_id": targets[0]["word_id"], "status": "used_correctly", "became_mastered": False}]
    cursor.execute(
        "INSERT INTO public.journal_entries (user_id, original_text, analysis_status, target_words, target_word_uses) "
        "VALUES (%s, 'Ayer madrugué.', 'ok', %s::jsonb, %s::jsonb) RETURNING target_words, target_word_uses",
        (user_id, json.dumps(targets), json.dumps(uses)),
    )
    assert cursor.fetchone() == (targets, uses)


def test_entries_without_the_word_bank_have_no_target_columns_filled(cursor):
    user_id = _user(cursor)
    cursor.execute(
        "INSERT INTO public.journal_entries (user_id, original_text, analysis_status) VALUES (%s, 'Hola', 'ok') "
        "RETURNING target_words, target_word_uses",
        (user_id,),
    )
    assert cursor.fetchone() == (None, None)


@pytest.mark.parametrize("kind", ["used_ok", "used_error"])
def test_uses_in_the_learners_own_entries_are_encounters(cursor, kind):
    user_id = _user(cursor)
    word_id = _word(cursor, user_id)
    _encounter(cursor, user_id, word_id, str(uuid.uuid4()), kind)
    cursor.execute("SELECT kind, source_type FROM public.word_encounters WHERE word_id = %s", (word_id,))
    assert cursor.fetchall() == [(kind, "entry")]


def test_a_word_used_outside_the_known_kinds_is_still_rejected(cursor):
    user_id = _user(cursor)
    word_id = _word(cursor, user_id)
    cursor.execute("SAVEPOINT bad")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _encounter(cursor, user_id, word_id, str(uuid.uuid4()), "used_perfectly")
    cursor.execute("ROLLBACK TO SAVEPOINT bad")


def test_a_challenge_use_can_be_logged_as_a_review(cursor):
    user_id = _user(cursor)
    word_id = _word(cursor, user_id)
    card_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO public.vocab_cards (id, user_id, word_id, language, card_type) "
        "VALUES (%s, %s, %s, 'es', 'production')",
        (card_id, user_id, word_id),
    )
    cursor.execute(
        "INSERT INTO public.vocab_review_logs (user_id, card_id, language, rating, source) "
        "VALUES (%s, %s, 'es', 3, 'challenge_use') RETURNING source",
        (user_id, card_id),
    )
    assert cursor.fetchone() == ("challenge_use",)


def test_the_lookup_indexes_exist(cursor):
    cursor.execute(
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'word_encounters' "
        "AND indexname IN ('idx_word_encounters_entry_uses', 'idx_word_encounters_correct_uses') ORDER BY 1"
    )
    assert [row[0] for row in cursor.fetchall()] == [
        "idx_word_encounters_correct_uses", "idx_word_encounters_entry_uses",
    ]

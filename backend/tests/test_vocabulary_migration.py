"""Vocabulary migration behavior against local Supabase, rolled back after each test."""

import os
import re
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20261004080000_vocabulary_cards.sql"
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
        yield connection.cursor()
    finally:
        connection.rollback()
        connection.close()


def _migrate(cursor):
    sql = re.sub(r"^\s*(BEGIN|COMMIT);\s*$", "", MIGRATION.read_text(), flags=re.MULTILINE)
    cursor.execute(sql)


def test_backfills_card_maps_saved_and_clears_provider_errors(cursor):
    user_id = str(uuid.uuid4())
    word_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO auth.users (id, email) VALUES (%s, %s)", (user_id, f"{user_id}@test.invalid"))
    cursor.execute("ALTER TABLE public.user_vocabulary DROP CONSTRAINT user_vocabulary_status_check")
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'user_vocabulary' AND column_name = 'lemma')"
    )
    if cursor.fetchone()[0]:
        cursor.execute(
            """
            INSERT INTO public.user_vocabulary (
              id, user_id, term, lemma, language, definition, status,
              ai_example_sentences, ai_cultural_note, mnemonic
            ) VALUES (%s, %s, 'banco', 'banco', 'es', 'park bench', 'saved',
              '["Me senté en un banco."]'::jsonb,
              'Error generating AI details: OpenAI 429 no credits',
              'Picture a bench')
            """,
            (word_id, user_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO public.user_vocabulary (
              id, user_id, term, language, definition, status,
              ai_example_sentences, ai_cultural_note, mnemonic
            ) VALUES (%s, %s, 'banco', 'es', 'park bench', 'saved',
              '["Me senté en un banco."]'::jsonb,
              'Error generating AI details: OpenAI 429 no credits',
              'Picture a bench')
            """,
            (word_id, user_id),
        )

    _migrate(cursor)

    cursor.execute(
        "SELECT status, sense, card, card_status, ai_cultural_note FROM public.user_vocabulary WHERE id = %s",
        (word_id,),
    )
    status, sense, card, card_status, cultural_note = cursor.fetchone()
    assert status == "new"
    assert sense == "park bench"
    assert card["lemma"] == "banco"
    assert card["sense_in_context"] == "park bench"
    assert card["examples"] == ["Me senté en un banco."]
    assert card_status == "ok"
    assert cultural_note is None
    cursor.execute("SELECT to_regclass('public.word_ai_cache')")
    assert cursor.fetchone()[0] is None

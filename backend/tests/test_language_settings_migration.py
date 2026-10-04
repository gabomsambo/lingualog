"""The language-settings backfill, run against a local Supabase Postgres inside a rolled-back transaction."""

import os
import re
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

MIGRATION = (
    Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20261004070000_language_settings.sql"
)
DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


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


def _user(cursor, native, default, legacy, profiles=()):
    user_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO auth.users (id, email) VALUES (%s, %s)", (user_id, f"{user_id}@example.test"))
    cursor.execute("DELETE FROM public.user_language_profiles WHERE user_id = %s", (user_id,))
    cursor.execute(
        "UPDATE public.user_settings SET native_lang = %s, default_target_lang = %s, target_languages = %s"
        " WHERE user_id = %s",
        (native, default, list(legacy), user_id),
    )
    for l2 in profiles:
        cursor.execute(
            "INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency)"
            " VALUES (%s, %s, 2, 'B1')",
            (user_id, l2),
        )
    return user_id


def _migrate(cursor):
    sql = re.sub(r"^\s*(BEGIN|COMMIT);\s*$", "", MIGRATION.read_text(), flags=re.MULTILINE)
    cursor.execute(sql)


def _studied(cursor, user_id):
    cursor.execute(
        "SELECT l2, active FROM public.user_language_profiles WHERE user_id = %s ORDER BY l2", (user_id,)
    )
    return cursor.fetchall()


def test_untouched_default_does_not_make_a_spanish_speaker_study_spanish(cursor):
    user_id = _user(cursor, native="es", default="en", legacy=["es"])
    _migrate(cursor)
    assert _studied(cursor, user_id) == [("en", True)]


def test_native_language_already_studied_is_kept(cursor):
    user_id = _user(cursor, native="es", default="en", legacy=["es"], profiles=["es"])
    _migrate(cursor)
    assert _studied(cursor, user_id) == [("en", True), ("es", True)]


def test_native_language_chosen_as_default_is_studied(cursor):
    user_id = _user(cursor, native="es", default="es", legacy=["es"])
    _migrate(cursor)
    assert _studied(cursor, user_id) == [("es", True)]


def test_other_legacy_languages_stay_studied(cursor):
    user_id = _user(cursor, native="en", default="es", legacy=["es", "fr"])
    _migrate(cursor)
    assert _studied(cursor, user_id) == [("es", True), ("fr", True)]

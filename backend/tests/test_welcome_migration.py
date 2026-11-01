"""First-run profile migration and save path against local Supabase Postgres."""

import json
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
    / "20261104000000_first_run_welcome.sql"
)
DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


@pytest.fixture
def cursor():
    try:
        connection = psycopg2.connect(DATABASE_URL, connect_timeout=3)
    except psycopg2.OperationalError:
        pytest.skip("local Supabase Postgres is not running")
    try:
        cursor = connection.cursor()
        yield cursor
    finally:
        connection.rollback()
        connection.close()


def _migrate(cursor):
    sql = re.sub(r"^\s*(BEGIN|COMMIT);\s*$", "", MIGRATION.read_text(), flags=re.MULTILINE)
    cursor.execute(sql)


def _user(cursor):
    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO auth.users (id, email) VALUES (%s, %s)",
        (user_id, f"{user_id}@example.test"),
    )
    return user_id


def test_backfills_existing_profiles_and_leaves_new_profiles_unonboarded(cursor):
    existing_user = _user(cursor)
    cursor.execute(
        "INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency) "
        "VALUES (%s, 'es', 1, 'A2') ON CONFLICT (user_id, l2) DO NOTHING",
        (existing_user,),
    )

    _migrate(cursor)
    cursor.execute(
        "SELECT onboarded_at FROM public.user_language_profiles WHERE user_id = %s AND l2 = 'es'",
        (existing_user,),
    )
    assert cursor.fetchone()[0] is not None

    new_user = _user(cursor)
    cursor.execute(
        "SELECT immersion_level, proficiency, onboarded_at FROM public.user_language_profiles "
        "WHERE user_id = %s AND l2 = 'es'",
        (new_user,),
    )
    assert cursor.fetchone() == (0, "A1", None)


def test_settings_save_persists_goal_without_resetting_onboarding(cursor):
    _migrate(cursor)
    user_id = _user(cursor)
    cursor.execute(
        "SELECT public.save_user_settings(%s, '{}'::jsonb, %s::jsonb)",
        (
            user_id,
            json.dumps([{"l2": "es", "immersion_level": 0, "proficiency": "A1", "goal": "class"}]),
        ),
    )
    cursor.execute(
        "SELECT goal, onboarded_at FROM public.user_language_profiles WHERE user_id = %s AND l2 = 'es'",
        (user_id,),
    )
    assert cursor.fetchone() == ("class", None)

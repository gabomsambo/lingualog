"""Book mode migration behavior against local Supabase, rolled back after each test."""

import os
import re
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20261008000000_book_mode.sql"
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


def _book(cursor, user_id, title="La sombra del viento", **columns):
    book_id = str(uuid.uuid4())
    values = {"id": book_id, "user_id": user_id, "title": title, "language": "es", **columns}
    cursor.execute(
        f"INSERT INTO public.books ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
        list(values.values()),
    )
    return book_id


def _session(cursor, user_id, book_id, **columns):
    session_id = str(uuid.uuid4())
    values = {"id": session_id, "user_id": user_id, "book_id": book_id, **columns}
    cursor.execute(
        f"INSERT INTO public.reading_sessions ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
        list(values.values()),
    )
    return session_id


def _mark(cursor, user_id, book_id, session_id, **columns):
    mark_id = str(uuid.uuid4())
    values = {
        "id": mark_id, "user_id": user_id, "language": "es", "lemma": "atar", "surface": "atadas",
        "kind": "read", "source_type": "book_session", "source_id": session_id, "book_id": book_id,
        "card_status": "pending", **columns,
    }
    cursor.execute(
        f"INSERT INTO public.word_encounters ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
        list(values.values()),
    )
    return mark_id


def _rejected(cursor, error, statement, *args):
    cursor.execute("SAVEPOINT rejected")
    with pytest.raises(error):
        cursor.execute(statement, args)
    cursor.execute("ROLLBACK TO SAVEPOINT rejected")


def test_the_migration_can_run_twice(cursor):
    _migrate(cursor)
    _book(cursor, _user(cursor))


def test_a_book_needs_a_title_and_a_known_status(cursor):
    user_id = _user(cursor)
    for columns in ({"title": "   "}, {"status": "abandoned"}):
        cursor.execute("SAVEPOINT bad")
        with pytest.raises(psycopg2.errors.CheckViolation):
            _book(cursor, user_id, **columns)
        cursor.execute("ROLLBACK TO SAVEPOINT bad")


def test_a_book_has_at_most_one_open_session(cursor):
    user_id = _user(cursor)
    book_id = _book(cursor, user_id)
    _session(cursor, user_id, book_id)
    _session(cursor, user_id, book_id, ended_at="2026-10-31T10:00:00+00:00", page_from=1, page_to=5)
    cursor.execute("SAVEPOINT second")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _session(cursor, user_id, book_id)
    cursor.execute("ROLLBACK TO SAVEPOINT second")


def test_a_session_cannot_end_before_it_starts(cursor):
    user_id = _user(cursor)
    cursor.execute("SAVEPOINT bad")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _session(cursor, user_id, _book(cursor, user_id), page_from=9, page_to=3)
    cursor.execute("ROLLBACK TO SAVEPOINT bad")


def test_marks_may_be_pending_and_may_be_skipped_but_nothing_else(cursor):
    user_id = _user(cursor)
    book_id = _book(cursor, user_id)
    session_id = _session(cursor, user_id, book_id)
    mark_id = _mark(cursor, user_id, book_id, session_id)
    cursor.execute("UPDATE public.word_encounters SET resolution = 'skipped' WHERE id = %s", (mark_id,))
    for column, value in (("resolution", "later"), ("card_status", "maybe")):
        cursor.execute("SAVEPOINT bad")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(f"UPDATE public.word_encounters SET {column} = %s WHERE id = %s", (value, mark_id))
        cursor.execute("ROLLBACK TO SAVEPOINT bad")


def test_existing_encounters_are_untouched(cursor):
    user_id = _user(cursor)
    cursor.execute(
        "INSERT INTO public.word_encounters (user_id, language, lemma, surface, kind, source_type) "
        "VALUES (%s, 'es', 'banco', 'banco', 'lookup', 'manual') RETURNING card_status, book_id, resolution",
        (user_id,),
    )
    assert cursor.fetchone() == ("ok", None, None)


def test_deleting_a_book_removes_sessions_and_unlinks_marks(cursor):
    user_id = _user(cursor)
    book_id = _book(cursor, user_id)
    session_id = _session(cursor, user_id, book_id)
    mark_id = _mark(cursor, user_id, book_id, session_id)
    cursor.execute("INSERT INTO public.page_photo_events (user_id, book_id) VALUES (%s, %s)", (user_id, book_id))

    cursor.execute("DELETE FROM public.books WHERE id = %s", (book_id,))

    cursor.execute("SELECT count(*) FROM public.reading_sessions WHERE id = %s", (session_id,))
    assert cursor.fetchone() == (0,)
    cursor.execute("SELECT book_id FROM public.word_encounters WHERE id = %s", (mark_id,))
    assert cursor.fetchone() == (None,)
    cursor.execute("SELECT count(*), count(book_id) FROM public.page_photo_events WHERE user_id = %s", (user_id,))
    assert cursor.fetchone() == (1, 0)


def test_every_new_table_has_row_level_security_for_its_owner(cursor):
    cursor.execute(
        "SELECT c.relname, c.relrowsecurity, "
        "array_agg(p.polname ORDER BY p.polname) FROM pg_class c "
        "JOIN pg_policy p ON p.polrelid = c.oid "
        "WHERE c.relname IN ('books', 'reading_sessions', 'page_photo_events') GROUP BY c.relname, c.relrowsecurity"
    )
    rows = {name: (enabled, policies) for name, enabled, policies in cursor.fetchall()}
    assert set(rows) == {"books", "reading_sessions", "page_photo_events"}
    for name, (enabled, policies) in rows.items():
        assert enabled
        assert policies == [f"{name}_{action}_own" for action in ("delete", "insert", "select", "update")]

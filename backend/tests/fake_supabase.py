"""A small in-memory stand-in for the Supabase client, enough for the query shapes the services use."""

import copy
import itertools
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

DEFAULTS = {
    "books": {"status": "reading", "author": None},
    "reading_sessions": {"ended_at": None, "page_from": None, "page_to": None, "words_marked": 0, "pages_read": None},
    "word_encounters": {
        "word_id": None, "sense": None, "sentence": None, "page": None, "card": None,
        "card_policy": None, "card_status": "ok", "source_id": None, "book_id": None, "resolution": None,
    },
}
_clock = itertools.count()


def _now() -> str:
    """Strictly increasing timestamps, so insertion order is also creation order."""
    return (datetime.now(timezone.utc) + timedelta(microseconds=next(_clock))).isoformat()


class Query:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self.rows = store.tables.setdefault(name, [])
        self.filters, self.action, self.payload = [], "select", None
        self.count_mode = False
        self._order, self._limit, self._single = None, None, False

    def select(self, *_columns, count=None):
        self.count_mode = bool(count)
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.action, self.payload = "update", payload
        return self

    def upsert(self, payload, **_options):
        return self.insert(payload)

    def delete(self):
        self.action = "delete"
        return self

    def eq(self, column, value):
        self.filters.append(lambda row: _get(row, column) == value)
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in set(values))
        return self

    def is_(self, column, value):
        wanted = None if value == "null" else value
        self.filters.append(lambda row: row.get(column) == wanted)
        return self

    def gte(self, column, value):
        self.filters.append(lambda row: (row.get(column) or "") >= value)
        return self

    def order(self, column, desc=False):
        self._order = (column, desc)
        return self

    def limit(self, count):
        self._limit = count
        return self

    def maybe_single(self):
        self._single = True
        return self

    def execute(self):
        matching = [row for row in self.rows if all(check(row) for check in self.filters)]
        if self.action == "insert":
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            created = []
            for item in rows:
                row = {"id": str(uuid.uuid4()), "created_at": _now(), "updated_at": _now(), "started_at": _now()}
                row.update(copy.deepcopy(DEFAULTS.get(self.name, {})))
                row.update(copy.deepcopy(item))
                self.rows.append(row)
                created.append(copy.deepcopy(row))
            return SimpleNamespace(data=created, count=len(created))
        if self.action == "update":
            for row in matching:
                row.update(copy.deepcopy(self.payload))
            return SimpleNamespace(data=copy.deepcopy(matching), count=len(matching))
        if self.action == "delete":
            for row in matching:
                self.rows.remove(row)
            return SimpleNamespace(data=copy.deepcopy(matching), count=len(matching))
        if self._order:
            column, desc = self._order
            matching.sort(key=lambda row: str(row.get(column) or ""), reverse=desc)
        if self._limit:
            matching = matching[: self._limit]
        data = copy.deepcopy(matching)
        if self._single:
            return SimpleNamespace(data=data[0] if data else None, count=len(data))
        return SimpleNamespace(data=data, count=len(data) if self.count_mode else None)


def _get(row, column):
    if "->>" in column:
        head, key = column.split("->>")
        return (row.get(head) or {}).get(key)
    return row.get(column)


class FakeSupabase:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return Query(self, name)

    def rows(self, name):
        return self.tables.get(name, [])

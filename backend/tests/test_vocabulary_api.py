"""Vocabulary API persistence and ownership behavior."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import server
from ai.gemini import GeminiError

USER_ID = "00000000-0000-0000-0000-000000000001"
NOW = datetime.now(timezone.utc).isoformat()


@pytest.fixture
def client():
    return TestClient(server.app)


def row(**changes):
    base = {
        "id": "word-1",
        "user_id": USER_ID,
        "term": "banco",
        "lemma": "banco",
        "language": "es",
        "status": "new",
        "card_status": "failed",
        "card": None,
        "card_policy": None,
        "tags": [],
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **changes}


def test_card_failure_persists_status_but_no_error_or_card(monkeypatch, client):
    saved = MagicMock(side_effect=lambda item_data, user_id: row(**item_data))
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_term", lambda *_: None)
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(
        server,
        "generate_word_card",
        MagicMock(side_effect=GeminiError("ai_unavailable", "provider failed")),
    )
    monkeypatch.setattr(server, "save_vocabulary_item", saved)

    response = client.post(
        "/vocabulary",
        headers={"X-User-ID": USER_ID},
        json={"term": "banco", "language": "es", "example_sentence": "Me senté en un banco."},
    )

    assert response.status_code == 201
    persisted = saved.call_args.kwargs["item_data"]
    assert persisted["card_status"] == "failed"
    assert "card" not in persisted
    assert "card_policy" not in persisted
    assert "provider failed" not in str(persisted)


def test_retry_failure_only_marks_status(monkeypatch, client):
    update = MagicMock(return_value=row())
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_id_and_user", lambda *_: row())
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(
        server,
        "generate_word_card",
        MagicMock(side_effect=GeminiError("ai_quota_exhausted", "no quota")),
    )
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.post("/vocabulary/word-1/card", headers={"X-User-ID": USER_ID})

    assert response.status_code == 503
    update.assert_called_once_with("word-1", USER_ID, {"card_status": "failed"})


def test_patch_filters_by_owner_and_normalizes_tags(monkeypatch, client):
    update = MagicMock(return_value=row(note="mine", tags=["travel", "class"]))
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.patch(
        "/vocabulary/word-1",
        headers={"X-User-ID": USER_ID},
        json={"note": "mine", "tags": [" travel ", "class", "travel"]},
    )

    assert response.status_code == 200
    update.assert_called_once_with(
        "word-1",
        USER_ID,
        {"note": "mine", "tags": ["travel", "class"]},
    )


def test_patch_returns_not_found_when_owner_filter_matches_nothing(monkeypatch, client):
    update = MagicMock(return_value=None)
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.patch(
        "/vocabulary/word-1",
        headers={"X-User-ID": "00000000-0000-0000-0000-000000000099"},
        json={"status": "known"},
    )

    assert response.status_code == 404
    update.assert_called_once_with(
        "word-1",
        "00000000-0000-0000-0000-000000000099",
        {"status": "known"},
    )

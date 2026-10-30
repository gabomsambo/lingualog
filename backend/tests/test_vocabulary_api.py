"""Vocabulary API persistence and ownership behavior."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

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


def test_inflected_save_does_not_overwrite_existing_lemma_row(monkeypatch, client):
    good = row(id="lemma-1", term="correr", lemma="correr", card_status="ok",
               card={"lemma": "correr"}, status="known")
    lookups = {"corriendo": None, "correr": good}
    save, update = MagicMock(), MagicMock()
    card = MagicMock(lemma="correr", sense_in_context="to run", part_of_speech="verb")
    card.model_dump.return_value = {"lemma": "correr"}
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_term", lambda _u, t, _l: lookups[t])
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(server, "card_policy_snapshot", lambda _p: {"v": 1})
    monkeypatch.setattr(server, "generate_word_card", AsyncMock(return_value=card))
    monkeypatch.setattr(server, "save_vocabulary_item", save)
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.post(
        "/vocabulary",
        headers={"X-User-ID": USER_ID},
        json={"term": "corriendo", "language": "es", "example_sentence": "Estoy corriendo."},
    )

    assert response.status_code == 201
    assert response.json()["id"] == "lemma-1"
    assert response.json()["status"] == "known"
    save.assert_not_called()
    update.assert_not_called()


def test_resave_of_failed_row_keeps_notebook_state(monkeypatch, client):
    failed = row(id="w9", status="learning", example_sentence="old", entry_id="e1")
    update = MagicMock(return_value=failed)
    card = MagicMock(lemma="banco", sense_in_context="bench", part_of_speech="noun")
    card.model_dump.return_value = {"lemma": "banco"}
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_term", lambda *_: failed)
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(server, "card_policy_snapshot", lambda _p: {"v": 1})
    monkeypatch.setattr(server, "generate_word_card", AsyncMock(return_value=card))
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.post(
        "/vocabulary",
        headers={"X-User-ID": USER_ID},
        json={"term": "banco", "language": "es", "example_sentence": "new", "entry_id": "e2"},
    )

    assert response.status_code == 201
    changes = update.call_args.args[2]
    assert "status" not in changes
    assert "example_sentence" not in changes
    assert "entry_id" not in changes
    assert changes["card_status"] == "ok"


@pytest.mark.parametrize("body", [{"tags": None}, {"status": None}])
def test_patch_rejects_explicit_null(monkeypatch, client, body):
    update = MagicMock()
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.patch("/vocabulary/word-1", headers={"X-User-ID": USER_ID}, json=body)

    assert response.status_code == 422
    update.assert_not_called()


def test_lookup_records_encounter(monkeypatch, client):
    card = MagicMock(lemma="banco", sense_in_context="bench")
    card.model_dump.return_value = {"lemma": "banco", "sense_in_context": "bench"}
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(server, "card_policy_snapshot", lambda _p: {"v": 1})
    monkeypatch.setattr(server, "fetch_lookup_cache", lambda *_: None)
    monkeypatch.setattr(server, "generate_word_card", AsyncMock(return_value=card))
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_term", lambda *_: None)
    save = MagicMock(return_value={"id": "enc-1"})
    monkeypatch.setattr(server, "save_word_encounter", save)
    monkeypatch.setattr(server, "count_word_encounters", lambda *_: 1)

    response = client.post(
        "/lookup", headers={"X-User-ID": USER_ID},
        json={"text": "banco", "sentence": "Me senté en un banco.", "language": "es", "source": "manual"},
    )

    assert response.status_code == 200
    assert response.json()["encounter_id"] == "enc-1"
    assert save.call_args.args[0]["sentence"] == "Me senté en un banco."


def test_lookup_cache_hit_avoids_model_call(monkeypatch, client):
    provider = AsyncMock()
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(server, "card_policy_snapshot", lambda _p: {"v": 1})
    monkeypatch.setattr(server, "fetch_lookup_cache", lambda *_: {
        "lemma": "banco", "sense": "bench", "card": {"lemma": "banco"}, "card_status": "ok",
    })
    monkeypatch.setattr(server, "generate_word_card", provider)
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_term", lambda *_: None)
    monkeypatch.setattr(server, "save_word_encounter", lambda *_: {"id": "enc-2"})
    monkeypatch.setattr(server, "count_word_encounters", lambda *_: 3)

    response = client.post(
        "/lookup", headers={"X-User-ID": USER_ID},
        json={"text": "banco", "language": "es", "source": "manual"},
    )

    assert response.status_code == 200
    assert response.json()["seen_count"] == 3
    provider.assert_not_awaited()


def test_study_triage_enforces_daily_cap(monkeypatch, client):
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_id_and_user", lambda *_: row())
    monkeypatch.setattr(server, "get_daily_new_word_usage", lambda *_: (10, 10))
    update = MagicMock()
    monkeypatch.setattr(server, "update_vocabulary_item", update)

    response = client.patch(
        "/vocabulary/word-1", headers={"X-User-ID": USER_ID}, json={"status": "learning"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "daily_new_words_cap"
    update.assert_not_called()


def test_cached_save_rejects_another_users_encounter(monkeypatch, client):
    monkeypatch.setattr(server, "fetch_vocabulary_item_by_term", lambda *_: None)
    monkeypatch.setattr(server, "resolve_policy", lambda *_: object())
    monkeypatch.setattr(server, "fetch_word_encounter", lambda *_: None)

    response = client.post(
        "/vocabulary", headers={"X-User-ID": USER_ID},
        json={"term": "banco", "language": "es", "encounter_id": "someone-elses"},
    )

    assert response.status_code == 404

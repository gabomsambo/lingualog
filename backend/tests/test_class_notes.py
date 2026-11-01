"""Class-note API, quota, ownership, and cached vocabulary hand-off."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from ai.schemas import FocusUse, JournalFeedback, TargetWordUse
import database
import server
from app.services import class_note_service
from learning_policy import resolve_policy
from tests.fake_supabase import FakeSupabase

USER = "00000000-0000-0000-0000-000000000011"
OTHER = "00000000-0000-0000-0000-000000000012"
HEADERS = {"X-User-ID": USER}


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(database, "create_supabase_client", lambda: fake)
    monkeypatch.setattr(class_note_service, "create_supabase_client", lambda: fake)
    policy = resolve_policy(
        None,
        "es",
        {"immersion_level": 1},
        settings={"native_lang": "en"},
        language_profile={"immersion_level": 1, "proficiency": "A1"},
    )
    monkeypatch.setattr(class_note_service, "resolve_policy", lambda *_: policy)
    monkeypatch.setattr(server, "resolve_policy", lambda *_: policy)
    return fake


@pytest.fixture
def client(db):
    return TestClient(server.app, raise_server_exceptions=False)


def extraction(count=20):
    return {
        "words": [
            {
                "term": f"palabra{index}",
                "lemma": f"palabra{index}",
                "gloss": f"word {index}",
                "part_of_speech": "noun",
                "example": f"La palabra{index} aparece en clase.",
                "reading": "",
            }
            for index in range(count)
        ],
        "grammar_focus": "estar + gerundio",
        "phrases": ["Estoy estudiando"],
        "tasks": [
            {"title": f"Task {index + 1}", "prompt": f"Write task {index + 1}",
             "length_hint": "25–50 words", "grammar_scope": "present tense"}
            for index in range(3)
        ],
        "level": "A1",
        "length_hint": "25–50 words",
        "grammar_scope": "present tense",
    }


def test_paste_creates_one_private_note_and_confirms_twenty_words(client, db, monkeypatch):
    provider = AsyncMock(return_value=extraction())
    monkeypatch.setattr(class_note_service, "extract_class_note", provider)
    raw_text = "palabra0 palabra1 palabra2 palabra3"

    created = client.post("/class-notes", headers=HEADERS, json={"text": raw_text, "language": "es"})

    assert created.status_code == 201
    note = created.json()
    assert note["raw_text"] == raw_text and note["source"] == "paste"
    assert len(note["extracted"]["words"]) == 20
    assert len(note["extracted"]["tasks"]) == 3
    provider.assert_awaited_once_with(raw_text, "es", "A1")

    confirmed = client.post(
        f"/class-notes/{note['id']}/confirm",
        headers=HEADERS,
        json=note["extracted"],
    )

    assert confirmed.status_code == 200
    assert len(confirmed.json()["extracted"]["words"]) == 20
    encounters = db.rows("word_encounters")
    assert len(encounters) == 20
    assert {row["source_type"] for row in encounters} == {"class_note"}
    assert {row["source_id"] for row in encounters} == {note["id"]}


def test_waiting_class_note_disappears_after_entry_is_linked(client, db, monkeypatch):
    monkeypatch.setattr(class_note_service, "extract_class_note", AsyncMock(return_value=extraction(1)))
    note = client.post("/class-notes", headers=HEADERS, json={"text": "casa", "language": "es"}).json()

    waiting = client.get("/class-notes/waiting?language=es", headers=HEADERS)
    assert waiting.status_code == 200 and waiting.json()["id"] == note["id"]

    db.table("journal_entries").insert({"user_id": USER, "class_note_id": note["id"]}).execute()
    waiting = client.get("/class-notes/waiting?language=es", headers=HEADERS)
    assert waiting.status_code == 200 and waiting.json() is None


def test_class_notes_are_owner_scoped(client, monkeypatch):
    monkeypatch.setattr(class_note_service, "extract_class_note", AsyncMock(return_value=extraction(1)))
    note = client.post("/class-notes", headers=HEADERS, json={"text": "casa", "language": "es"}).json()

    response = client.get(f"/class-notes/{note['id']}", headers={"X-User-ID": OTHER})

    assert response.status_code == 404


def test_class_note_quota_hook_refuses_before_model_call(client, monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr(class_note_service, "extract_class_note", provider)
    monkeypatch.setattr(class_note_service, "class_note_quota_allows", lambda _user_id: False)

    response = client.post("/class-notes", headers=HEADERS, json={"text": "casa", "language": "es"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "class_note_quota_reached"
    provider.assert_not_awaited()


def test_vocabulary_path_reuses_the_class_note_card_without_another_model_call(client, db, monkeypatch):
    monkeypatch.setattr(class_note_service, "extract_class_note", AsyncMock(return_value=extraction(1)))
    note = client.post("/class-notes", headers=HEADERS, json={"text": "palabra0", "language": "es"}).json()
    confirmed = client.post(
        f"/class-notes/{note['id']}/confirm",
        headers=HEADERS,
        json=note["extracted"],
    ).json()
    word = confirmed["extracted"]["words"][0]
    provider = AsyncMock()
    monkeypatch.setattr(server, "generate_word_card", provider)

    saved = client.post(
        "/vocabulary",
        headers=HEADERS,
        json={
            "term": word["lemma"],
            "language": "es",
            "part_of_speech": word["part_of_speech"],
            "definition": word["gloss"],
            "example_sentence": word["example"],
            "encounter_id": word["encounter_id"],
        },
    )

    assert saved.status_code == 201
    assert saved.json()["status"] == "new"
    assert saved.json()["card_status"] == "ok"
    provider.assert_not_awaited()
    assert db.rows("word_encounters")[0]["word_id"] == saved.json()["id"]


def test_twenty_confirmed_words_and_focus_are_checked_in_one_feedback_call(client, db, monkeypatch):
    monkeypatch.setattr(class_note_service, "extract_class_note", AsyncMock(return_value=extraction(20)))
    note = client.post("/class-notes", headers=HEADERS, json={"text": "class list", "language": "es"}).json()
    confirmed = client.post(
        f"/class-notes/{note['id']}/confirm",
        headers=HEADERS,
        json=note["extracted"],
    ).json()

    saved_ids = []
    for word in confirmed["extracted"]["words"]:
        response = client.post(
            "/vocabulary",
            headers=HEADERS,
            json={
                "term": word["lemma"],
                "language": "es",
                "part_of_speech": word["part_of_speech"],
                "definition": word["gloss"],
                "example_sentence": word["example"],
                "encounter_id": word["encounter_id"],
            },
        )
        assert response.status_code == 201
        saved_ids.append(response.json()["id"])

    focus = note["extracted"]["grammar_focus"]
    terms = [word["lemma"] for word in confirmed["extracted"]["words"]]
    entry_text = " ".join(terms)
    feedback = JournalFeedback(
        corrected=entry_text,
        rewrite=entry_text,
        score=80,
        tone="Neutral",
        explanation="Good practice.",
        rubric={"grammar": 80, "vocabulary": 80, "complexity": 80},
        grammar_suggestions=[],
        new_words=[],
        sentence_mapping=[{"source_sentence": 0, "corrected_sentences": [0]}],
        sentence_actions=[],
        detected_language="es",
        target_word_uses=[
            TargetWordUse(term=term, status="used_correctly", form_in_text=term)
            for term in terms
        ],
        focus_uses=[FocusUse(focus=focus, status="used_correctly", evidence="Estoy estudiando.")],
    )
    feedback_call = AsyncMock(return_value=feedback)
    monkeypatch.setattr(server, "_analyze_with_provider", feedback_call)
    monkeypatch.setattr(
        server,
        "_policy_for_request",
        lambda *_args, **_kwargs: class_note_service.resolve_policy(USER, "es"),
    )
    monkeypatch.setattr(
        server,
        "_target_words_for_request",
        lambda _user_id, _language, _word_ids: [
            {"word_id": word_id, "lemma": term, "term": term, "forms": [term]}
            for word_id, term in zip(saved_ids, terms)
        ],
    )
    monkeypatch.setattr(server, "fetch_user_profile_settings", AsyncMock(return_value=None))
    monkeypatch.setattr(server, "mark_language_profile_onboarded", lambda *_: None)
    monkeypatch.setattr(server, "_record_target_word_uses", lambda *_args, **_kwargs: None)

    response = client.post(
        "/log-entry",
        headers=HEADERS,
        json={
            "text": entry_text,
            "language": "es",
            "target_language": "es",
            "class_note_id": note["id"],
            "target_word_ids": saved_ids,
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert len(payload["target_word_uses"]) == 20
    assert {use["status"] for use in payload["target_word_uses"]} == {"used_correctly"}
    assert payload["focus_uses"] == [{
        "focus": focus,
        "status": "used_correctly",
        "evidence": "Estoy estudiando.",
        "fix": "",
        "note": "",
    }]
    feedback_call.assert_awaited_once()
    assert feedback_call.await_args.kwargs["grammar_focus"] == focus
    saved_entry = db.rows("journal_entries")[-1]
    assert saved_entry["class_note_id"] == note["id"]
    assert len(saved_entry["target_word_uses"]) == 20

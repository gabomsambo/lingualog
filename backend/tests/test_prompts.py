"""The static Spanish prompt pack is filtered and glossed by the learner's policy."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.routers.prompts as prompt_router
import server

USER = "00000000-0000-0000-0000-00000000000a"
HEADERS = {"X-User-ID": USER}


def policy(_user_id, l2):
    return SimpleNamespace(l2=l2 or "es", proficiency="A1", meaning="open", l1="en")


def test_prompts_filter_by_level_topic_and_excluded_ids(monkeypatch):
    monkeypatch.setattr(prompt_router, "resolve_policy", policy)
    client = TestClient(server.app)

    response = client.get(
        "/prompts?l2=es&level=A1&topic=alimentacion&exclude=es-a1-04",
        headers=HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] == "A1"
    assert payload["prompts"]
    assert all(prompt["level"] == "A1" for prompt in payload["prompts"])
    assert all("alimentacion" in prompt["topics"] for prompt in payload["prompts"])
    assert "es-a1-04" not in {prompt["id"] for prompt in payload["prompts"]}


def test_prompt_gloss_is_returned_only_when_meaning_policy_allows_it(monkeypatch):
    monkeypatch.setattr(prompt_router, "resolve_policy", policy)
    client = TestClient(server.app)

    open_result = client.get("/prompts?l2=es&level=A1", headers=HEADERS).json()
    assert open_result["gloss_available"] is True
    assert open_result["prompts"][0]["gloss"]["sentence_frame"]

    monkeypatch.setattr(
        prompt_router,
        "resolve_policy",
        lambda _user_id, l2: SimpleNamespace(l2=l2 or "es", proficiency="A1", meaning="rescue_only", l1="en"),
    )
    hidden_result = client.get("/prompts?l2=es&level=A1", headers=HEADERS).json()
    assert hidden_result["gloss_available"] is False
    assert all(prompt["gloss"] is None for prompt in hidden_result["prompts"])


def test_prompts_require_a_signed_in_user():
    response = TestClient(server.app).get("/prompts?l2=es&level=A1")

    assert response.status_code == 401


def test_prompt_selection_is_logged_with_the_prompt_id(monkeypatch):
    from app.routers import support_events
    from tests.fake_supabase import FakeSupabase

    store = FakeSupabase()
    monkeypatch.setattr(support_events, "create_supabase_client", lambda: store)

    response = TestClient(server.app).post(
        "/events",
        headers=HEADERS,
        json={"kind": "prompt_selected", "l2": "es", "prompt_id": "es-a1-01"},
    )

    assert response.status_code == 201
    assert store.rows("support_events")[0]["prompt_id"] == "es-a1-01"


def test_prompt_usage_event_rejects_unknown_prompt_id():
    response = TestClient(server.app).post(
        "/events",
        headers=HEADERS,
        json={"kind": "prompt_selected", "l2": "es", "prompt_id": "not-a-prompt"},
    )

    assert response.status_code == 400

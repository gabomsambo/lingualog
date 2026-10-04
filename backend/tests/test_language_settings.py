"""Studied languages, full immersion, the did-you-mean check and the settings it relies on."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import server
from ai.schemas import JournalFeedback
from app.models import UserSettings
from learning_policy import LEVELS, feedback_prompt_rules, resolve_policy


def _policy(native, l2, immersion=1, overrides=None, explanation_mode=None):
    settings = {"native_lang": native, "default_target_lang": l2, "immersion_level": immersion}
    if explanation_mode:
        settings.update(explanation_mode=explanation_mode, explanation_mode_explicit=True)
    return resolve_policy(
        "user-1",
        l2,
        overrides,
        settings=settings,
        language_profile={"l2": l2, "immersion_level": immersion, "proficiency": "B2"},
    )


def _feedback(detected=""):
    return JournalFeedback(
        corrected="Corrected",
        rewrite="Rewrite",
        score=80,
        tone="Neutral",
        explanation="Explanation.",
        rubric={"grammar": 80, "vocabulary": 80, "complexity": 80},
        detected_language=detected,
    )


@pytest.fixture
def client():
    return TestClient(server.app, raise_server_exceptions=False)


class TestFullImmersion:
    @pytest.mark.parametrize("native,l2", [("en", "en"), ("es", "es"), ("pt", "pt-BR")])
    def test_studying_your_own_language_is_level_three_at_every_level(self, native, l2):
        for level in range(4):
            policy = _policy(native, l2, immersion=level, explanation_mode="native_only")
            assert policy.immersion_level == 3
            assert policy.immersion_source == "same_language"
            assert policy.explanation_source == "same_language"
            assert policy.explanation == LEVELS[3]["explanation"]
            assert policy.meaning == "rescue_only"
            assert policy.translation_policy == "omit"

    def test_same_language_beats_a_per_entry_slider(self):
        policy = _policy("es", "es", overrides={"immersion_level": 0, "explanation_mode": "bilingual"})
        assert policy.immersion_level == 3
        assert policy.explanation == "l2"

    def test_full_immersion_prompt_never_forbids_the_only_language(self):
        rules = feedback_prompt_rules(_policy("en", "en"))
        assert "Full immersion" in rules
        assert "Never use English" not in rules
        assert "Leave `note_l1` empty" in rules

    def test_english_is_an_ordinary_target_for_a_spanish_speaker(self):
        policy = _policy("es", "en", immersion=0)
        assert policy.l2 == "en"
        assert policy.immersion_level == 0
        assert policy.explanation == "l1"
        assert "in Spanish only" in feedback_prompt_rules(policy)

    def test_english_at_level_three_explains_in_english(self):
        policy = _policy("es", "en", immersion=3)
        assert "Write everything in English only" in feedback_prompt_rules(policy)


class TestDetectedLanguage:
    def test_prompt_asks_for_the_written_language_without_assuming_the_target(self):
        rules = feedback_prompt_rules(_policy("en", "es"))
        assert "`detected_language`" in rules
        assert "Do not assume Spanish" in rules

    @pytest.mark.parametrize(
        "reported,stored",
        [("fr", "fr"), ("FR", "fr"), ("pt-BR", "pt"), ("und", None), ("", None), ("French", None)],
    )
    def test_log_entry_stores_the_normalised_report(self, client, reported, stored):
        with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value=None)), patch(
            "server.fetch_language_profile", return_value=None
        ), patch("server.save_entry", return_value={"id": "entry-1"}) as save, patch(
            "server.generate_structured", new=AsyncMock(return_value=_feedback(reported))
        ):
            response = client.post(
                "/log-entry",
                json={"text": "Samedi je suis allé au marché.", "target_language": "es"},
                headers={"X-User-ID": "user-1"},
            )
        assert response.status_code == 201
        assert response.json()["detected_language"] == stored
        saved = save.call_args[0][0]
        assert saved["detected_language"] == stored
        assert saved["language"] == "es"

    def test_mock_provider_reports_no_language(self, client):
        with patch.object(server, "AI_PROVIDER", "mock"), patch(
            "server.fetch_user_profile_settings", new=AsyncMock(return_value=None)
        ), patch("server.fetch_language_profile", return_value=None), patch(
            "server.save_entry", return_value={"id": "entry-1"}
        ):
            response = client.post("/log-entry", json={"text": "Hola amigos"}, headers={"X-User-ID": "user-1"})
        assert response.status_code == 201
        assert response.json()["detected_language"] is None


ENTRY = {
    "id": "entry-1",
    "content": "Samedi je suis allé au marché.",
    "language": "es",
    "target_language": "es",
    "policy_snapshot": _policy("en", "es", immersion=2).to_dict(),
}


class TestSwitchLanguage:
    def _analyze(self, client, body, profiles):
        with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value={"native_lang": "en"})), patch(
            "server.fetch_single_entry", return_value=dict(ENTRY)
        ), patch("server.list_language_profiles", return_value=profiles), patch(
            "server.fetch_language_profile",
            side_effect=lambda user_id, l2: next((p for p in profiles if p["l2"] == l2), None),
        ), patch("server.update_entry_analysis", return_value={"id": "entry-1"}) as update, patch(
            "server.generate_structured", new=AsyncMock(return_value=_feedback("fr"))
        ) as generate:
            response = client.post("/entries/entry-1/analyze", json=body, headers={"X-User-ID": "user-1"})
        return response, update, generate

    def test_switch_to_a_studied_language_reanalyses_as_that_language(self, client):
        profiles = [
            {"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True},
            {"l2": "fr", "immersion_level": 0, "proficiency": "A1", "active": True},
        ]
        response, update, generate = self._analyze(client, {"target_language": "fr"}, profiles)
        assert response.status_code == 200
        assert "French" in generate.call_args[0][0]
        columns = update.call_args[0][2]
        assert columns["language"] == "fr"
        assert columns["target_language"] == "fr"
        assert columns["policy_snapshot"]["l2"] == "fr"
        assert columns["policy_snapshot"]["immersion_level"] == 0
        assert columns["meaning_translations_cache"] == {}
        assert columns["detected_language"] == "fr"
        assert columns["detected_language_kept"] is False

    @pytest.mark.parametrize(
        "profiles",
        [
            [{"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True}],
            [
                {"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True},
                {"l2": "fr", "immersion_level": 0, "proficiency": "A1", "active": False},
            ],
        ],
    )
    def test_switch_to_a_language_not_studied_changes_nothing(self, client, profiles):
        response, update, generate = self._analyze(client, {"target_language": "fr"}, profiles)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "language_not_studied"
        update.assert_not_called()
        generate.assert_not_called()

    def test_switch_when_profiles_cannot_be_read_is_unavailable(self, client):
        with patch("server.fetch_user_profile_settings", new=AsyncMock(return_value={"native_lang": "en"})), patch(
            "server.fetch_single_entry", return_value=dict(ENTRY)
        ), patch("server.list_language_profiles", side_effect=RuntimeError("db down")), patch(
            "server.update_entry_analysis"
        ) as update, patch("server.generate_structured", new=AsyncMock()) as generate:
            response = client.post(
                "/entries/entry-1/analyze", json={"target_language": "fr"}, headers={"X-User-ID": "user-1"}
            )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "profiles_unavailable"
        update.assert_not_called()
        generate.assert_not_called()

    def test_plain_retry_keeps_the_language_and_snapshot(self, client):
        response, update, _ = self._analyze(client, None, [])
        assert response.status_code == 200
        columns = update.call_args[0][2]
        assert "language" not in columns
        assert columns["policy_snapshot"]["l2"] == "es"

    def test_keep_records_the_choice(self, client):
        with patch("server.fetch_single_entry", return_value=dict(ENTRY)), patch(
            "server.update_entry_analysis", return_value={"id": "entry-1"}
        ) as update:
            response = client.post("/entries/entry-1/keep-language", headers={"X-User-ID": "user-1"})
        assert response.status_code == 204
        update.assert_called_once_with("entry-1", "user-1", {"detected_language_kept": True})

    def test_keep_on_someone_elses_entry_is_not_found(self, client):
        with patch("server.fetch_single_entry", return_value=None), patch("server.update_entry_analysis") as update:
            response = client.post("/entries/entry-1/keep-language", headers={"X-User-ID": "user-2"})
        assert response.status_code == 404
        update.assert_not_called()


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return type("Response", (), {"data": self.rows})()


class _Supabase:
    def table(self, _name):
        return _Query([{"default_target_lang": "es", "immersion_level": 2}])


class TestStudiedLanguagesSave:
    SAVED = [
        {"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True},
        {"l2": "fr", "immersion_level": 1, "proficiency": "A2", "active": True},
    ]

    def _put(self, monkeypatch, body):
        saves = []
        monkeypatch.setattr("database.create_supabase_client", lambda: _Supabase())
        monkeypatch.setattr(server, "list_language_profiles", lambda user_id: [dict(row) for row in self.SAVED])
        monkeypatch.setattr(server, "save_user_settings", lambda user_id, s, p: saves.append((s, p)))

        async def fake_get_user_settings(request):
            now = datetime.now(timezone.utc)
            return UserSettings(id=uuid.uuid4(), user_id=uuid.uuid4(), created_at=now, updated_at=now)

        monkeypatch.setattr(server, "get_user_settings", fake_get_user_settings)
        response = TestClient(server.app).put("/user/settings", json=body, headers={"X-User-ID": "user-1"})
        return response, saves

    def test_removing_a_language_keeps_its_profile_inactive(self, monkeypatch):
        response, saves = self._put(
            monkeypatch,
            {"language_profiles": [{"l2": "fr", "immersion_level": 1, "proficiency": "A2", "active": False}]},
        )
        assert response.status_code == 200
        assert saves[0][1] == [{"l2": "fr", "immersion_level": 1, "proficiency": "A2", "active": False}]

    def test_the_default_language_cannot_be_removed(self, monkeypatch):
        response, saves = self._put(
            monkeypatch,
            {"language_profiles": [{"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": False}]},
        )
        assert response.status_code == 400
        assert saves == []

    def test_a_removed_language_cannot_become_the_default(self, monkeypatch):
        response, saves = self._put(
            monkeypatch,
            {
                "default_target_lang": "fr",
                "language_profiles": [{"l2": "fr", "immersion_level": 1, "proficiency": "A2", "active": False}],
            },
        )
        assert response.status_code == 400
        assert saves == []

    def test_a_failed_profile_read_saves_nothing(self, monkeypatch):
        saves = []
        monkeypatch.setattr("database.create_supabase_client", lambda: _Supabase())

        def failing_list(user_id):
            raise RuntimeError("db down")

        monkeypatch.setattr(server, "list_language_profiles", failing_list)
        monkeypatch.setattr(server, "save_user_settings", lambda user_id, s, p: saves.append((s, p)))
        response = TestClient(server.app).put(
            "/user/settings", json={"default_target_lang": "es"}, headers={"X-User-ID": "user-1"}
        )
        assert response.status_code == 500
        assert saves == []

    def test_a_failed_profile_read_does_not_reset_proficiency(self, monkeypatch):
        saves = []
        monkeypatch.setattr("database.create_supabase_client", lambda: _Supabase())

        def failing_fetch(user_id, l2):
            raise RuntimeError("db down")

        monkeypatch.setattr(server, "fetch_language_profile", failing_fetch)
        monkeypatch.setattr(server, "save_user_settings", lambda user_id, s, p: saves.append((s, p)))
        response = TestClient(server.app).put(
            "/user/settings", json={"immersion_level": 3}, headers={"X-User-ID": "user-1"}
        )
        assert response.status_code == 500
        assert saves == []

    def test_a_new_default_is_added_to_the_studied_list(self, monkeypatch):
        response, saves = self._put(monkeypatch, {"default_target_lang": "en"})
        assert response.status_code == 200
        settings, profiles = saves[0]
        assert settings["default_target_lang"] == "en"
        assert profiles == [{"l2": "en", "immersion_level": 2, "proficiency": "A2", "active": True}]

    def test_native_language_can_be_studied_and_default(self, monkeypatch):
        response, saves = self._put(
            monkeypatch,
            {
                "native_lang": "es",
                "default_target_lang": "es",
                "language_profiles": [{"l2": "es", "immersion_level": 2, "proficiency": "C1", "active": True}],
            },
        )
        assert response.status_code == 200
        assert saves[0][0]["native_lang"] == "es"


def test_settings_report_which_languages_are_studied(monkeypatch):
    monkeypatch.setattr(
        server,
        "list_language_profiles",
        lambda user_id: [
            {"l2": "es", "immersion_level": 2, "proficiency": "B1", "active": True},
            {"l2": "fr", "immersion_level": 1, "proficiency": "A2", "active": False},
            {"l2": "ja", "immersion_level": 0, "proficiency": "A1"},
        ],
    )
    profiles = server._language_profiles_for_user("user-1")
    assert [(p.l2, p.active) for p in profiles] == [("es", True), ("fr", False), ("ja", True)]


def test_settings_fail_to_load_when_profiles_cannot_be_read(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "native_language": "en",
        "target_languages": ["es"], "email_notifications": True, "push_notifications": True,
        "daily_reminders": True, "weekly_progress": True, "reminder_time": "09:00", "theme": "system",
        "app_language": "en", "sound_effects": True, "animations": True, "difficulty_level": "intermediate",
        "daily_goal": 100, "weekly_goal": 700, "auto_save": True, "show_hints": True, "public_profile": False,
        "share_progress": False, "analytics_opt_in": True, "created_at": now, "updated_at": now,
    }

    class _SettingsSupabase:
        def table(self, _name):
            return _Query([row])

    def failing_list(user_id):
        raise RuntimeError("db down")

    monkeypatch.setattr("database.create_supabase_client", lambda: _SettingsSupabase())
    monkeypatch.setattr(server, "list_language_profiles", failing_list)
    response = TestClient(server.app).get("/user/settings", headers={"X-User-ID": "user-1"})
    assert response.status_code == 500

    monkeypatch.setattr(server, "list_language_profiles", lambda user_id: [])
    response = TestClient(server.app).get("/user/settings", headers={"X-User-ID": "user-1"})
    assert response.status_code == 200
    assert response.json()["language_profiles"] == []


@pytest.mark.asyncio
async def test_meaning_translation_refuses_the_entrys_own_language():
    from app.services import entry_translation_service as svc

    with patch.object(svc, "fetch_single_entry", return_value={"id": "e1", "language": "es", "content": "Hola."}):
        with pytest.raises(ValueError):
            await svc.translate_entry_part("e1", "u1", "original", "es")

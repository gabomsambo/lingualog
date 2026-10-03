"""Shared pytest configuration for the backend test suite."""
import pytest


@pytest.fixture(autouse=True)
def stub_gemini_key(monkeypatch):
    """Provide a dummy Gemini API key so adapter tests never need a real one."""
    import ai.gemini
    monkeypatch.setattr(ai.gemini, "GEMINI_API_KEY", "dummy-key-for-tests")


@pytest.fixture(autouse=True)
def stub_language_profile_lookup(monkeypatch):
    """Unit tests resolve policy from the settings dict, not a live database."""
    import server
    monkeypatch.setattr(server, "fetch_language_profile", lambda user_id, l2: None)

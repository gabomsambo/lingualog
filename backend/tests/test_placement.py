"""The optional vocabulary-size placement check: an estimate, never a score."""

import pytest
from fastapi.testclient import TestClient

import placement
import server
from app.services import vocab_service

USER = "00000000-0000-0000-0000-00000000000a"
HEADERS = {"X-User-ID": USER}


def test_samples_are_fixed_per_band_and_language():
    bands = placement.band_samples("es")
    assert len(bands) == len(placement.BANDS) == 5
    assert all(len(band) == placement.WORDS_PER_BAND for band in bands)
    assert placement.has_samples("es-ES") is True
    assert placement.has_samples("ja") is False
    assert len(placement.sample_words("pt-BR")) == 40


def test_estimate_scales_each_bands_share():
    words = placement.sample_words("es")
    assert placement.estimate_size("es", words) == 32000
    assert placement.estimate_size("es", []) == 0
    # Band 1 is 2000 ranks wide: knowing all eight of its words adds 2000.
    assert placement.estimate_size("es", words[:8]) == 2000
    # Bands 1 and 2: 2000 + 2000.
    assert placement.estimate_size("es", words[:16]) == 4000
    assert placement.estimate_size("es", ["not-in-the-sample"]) == 0
    assert placement.estimate_size("ja", words) is None


def test_matching_words_only_keeps_the_sample():
    words = placement.sample_words("de")
    matched = placement.matching_words("DE", [words[0].upper(), "xyz", words[-1]])
    assert matched == [words[0], words[-1]]


def test_placement_result_counts_only_tapped_sample_words():
    words = placement.sample_words("fr")
    result = vocab_service.placement_result("fr", [words[0], "invented"])
    assert result["v"] == 1
    assert result["sample_size"] == 40
    assert result["known"] == [words[0]]
    # One of band 1's eight words: 1/8 of its 2000 ranks.
    assert result["estimate"] == 250
    assert result["checked_at"]


def test_get_placement_returns_the_sample_and_stored_result(monkeypatch):
    monkeypatch.setattr(
        vocab_service, "load_profiles",
        lambda user_id: [{"l2": "es", "placement": {"v": 1, "estimate": 2200}}],
    )
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.get("/placement/es").status_code == 401

    response = client.get("/placement/es", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "es"
    assert len(body["words"]) == 40
    assert len(body["bands"]) == 5
    assert body["result"] == {"v": 1, "estimate": 2200}


def test_get_placement_is_not_offered_for_unsampled_languages():
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.get("/placement/ja", headers=HEADERS).status_code == 404


def test_post_placement_stores_the_estimate(monkeypatch):
    stored = {}
    monkeypatch.setattr(vocab_service, "save_placement", lambda user_id, l2, result: stored.update(result) or True)
    words = placement.sample_words("es")
    client = TestClient(server.app, raise_server_exceptions=False)

    response = client.post(
        "/placement/es", headers=HEADERS, json={"known": [words[0], words[1], "hacker"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["known"] == [words[0], words[1]]
    assert body["estimate"] == 500
    assert stored["estimate"] == 500


def test_post_placement_is_not_offered_for_unsampled_languages():
    client = TestClient(server.app, raise_server_exceptions=False)
    assert client.post("/placement/ja", headers=HEADERS, json={"known": []}).status_code == 404

"""
Tests for the FastAPI server application.

This module contains tests to verify the API endpoints and middleware
functionality of the LinguaLog backend.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.server import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_app_exists():
    """Verify that the FastAPI app is instantiated."""
    assert app is not None
    assert app.title == "LinguaLog API"


def test_not_found_route(client):
    """Test that requesting a non-existent route returns 404."""
    response = client.get("/non-existent-route")
    assert response.status_code == 404
    
    
@patch("backend.server.analyze_entry")
@patch("backend.server.save_entry")
def test_post_log_entry(mock_save_entry, mock_analyze_entry, client):
    """Test the POST /log-entry endpoint creates and saves an entry."""
    # Mock analyze_entry to return predefined analysis
    mock_analysis = {
        "corrected": "Hola, me llamo Juan.",
        "rewrite": "Hola, me llamo Juan. (more natural)",
        "fluency_score": 85,
        "tone": "Neutral",
        "translation": "Hello, my name is Juan."
    }
    mock_analyze_entry.return_value = mock_analysis
    
    # Mock save_entry to return a fake saved entry
    mock_saved_entry = {
        "id": "test-id",
        "created_at": "2023-05-05T12:00:00Z"
    }
    mock_save_entry.return_value = mock_saved_entry
    
    # Send request to endpoint
    response = client.post(
        "/log-entry",
        json={"text": "Hola me llamo Juan"}
    )
    
    # Verify the response
    assert response.status_code == 201
    assert "corrected" in response.json()
    assert "rewritten" in response.json()
    assert "score" in response.json()
    assert "tone" in response.json()
    assert "translation" in response.json()
    
    # Verify analyze_entry was called with the correct text
    mock_analyze_entry.assert_called_once_with("Hola me llamo Juan")
    
    # Verify save_entry was called with entry data containing analysis results
    mock_save_entry.assert_called_once()
    call_args = mock_save_entry.call_args[0][0]
    assert call_args["original_text"] == "Hola me llamo Juan"
    assert call_args["corrected"] == mock_analysis["corrected"]
    assert call_args["rewrite"] == mock_analysis["rewrite"]
    assert call_args["score"] == mock_analysis["fluency_score"]
    assert call_args["tone"] == mock_analysis["tone"]
    assert call_args["translation"] == mock_analysis["translation"]


@patch("backend.server.fetch_entries")
def test_get_entries(mock_fetch_entries, client):
    """Test the GET /entries endpoint returns entries from the database."""
    # Mock fetch_entries to return predefined entries
    mock_entries = [
        {
            "id": "1",
            "user_id": None,
            "original_text": "Entry 1",
            "corrected": "Entry 1",
            "rewrite": "Entry 1 (better)",
            "score": 85,
            "tone": "Neutral",
            "translation": "Translation 1",
            "created_at": "2023-05-05T12:00:00Z"
        },
        {
            "id": "2",
            "user_id": None,
            "original_text": "Entry 2",
            "corrected": "Entry 2",
            "rewrite": "Entry 2 (better)",
            "score": 90,
            "tone": "Confident",
            "translation": "Translation 2",
            "created_at": "2023-05-04T12:00:00Z"
        }
    ]
    mock_fetch_entries.return_value = mock_entries
    
    # Send request to endpoint
    response = client.get("/entries")
    
    # Verify the response
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json() == mock_entries
    
    # Verify fetch_entries was called
    mock_fetch_entries.assert_called_once() 
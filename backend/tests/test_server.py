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


@patch("backend.server.delete_entry")
def test_delete_entry_success(mock_delete_entry, client):
    """Test the DELETE /entries/{entry_id} endpoint successfully deletes an entry."""
    mock_delete_entry.return_value = True
    user_id = "test-user-id"
    entry_id_to_delete = "entry-to-delete-id"

    response = client.delete(
        f"/entries/{entry_id_to_delete}",
        headers={"X-User-ID": user_id}
    )

    assert response.status_code == 204
    mock_delete_entry.assert_called_once_with(entry_id=entry_id_to_delete, user_id=user_id)


@patch("backend.server.delete_entry")
def test_delete_entry_not_found(mock_delete_entry, client):
    """Test DELETE /entries/{entry_id} when entry is not found or not owned by user."""
    mock_delete_entry.return_value = False
    user_id = "test-user-id"
    entry_id_to_delete = "non-existent-entry-id"

    response = client.delete(
        f"/entries/{entry_id_to_delete}",
        headers={"X-User-ID": user_id}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Entry with id {entry_id_to_delete} not found or already deleted."
    mock_delete_entry.assert_called_once_with(entry_id=entry_id_to_delete, user_id=user_id)


@patch("backend.server.delete_entry")
def test_delete_entry_no_user_id(mock_delete_entry, client):
    """Test DELETE /entries/{entry_id} without X-User-ID header."""
    entry_id_to_delete = "entry-id"

    response = client.delete(f"/entries/{entry_id_to_delete}")

    assert response.status_code == 401
    assert response.json()["detail"] == "User ID not provided"
    mock_delete_entry.assert_not_called()


@patch("backend.server.delete_entry")
def test_delete_entry_exception(mock_delete_entry, client):
    """Test DELETE /entries/{entry_id} when an unexpected exception occurs."""
    mock_delete_entry.side_effect = Exception("Database connection error")
    user_id = "test-user-id"
    entry_id_to_delete = "entry-id"

    response = client.delete(
        f"/entries/{entry_id_to_delete}",
        headers={"X-User-ID": user_id}
    )

    assert response.status_code == 500
    assert response.json()["detail"] == f"Error deleting entry: Database connection error"
    mock_delete_entry.assert_called_once_with(entry_id=entry_id_to_delete, user_id=user_id)


# Additional test cases might include testing with invalid entry_id format if applicable. 


# --- Vocabulary Endpoint Tests ---

@patch("backend.server.save_vocabulary_item")
def test_add_vocabulary_item_success(mock_save_vocab, client):
    user_id = "test-user-id"
    item_data = {
        "term": "Konnichiwa",
        "language": "Japanese",
        "definition": "Hello",
        "part_of_speech": "interjection",
        "reading": "こんにちは",
        "example_sentence": "Konnichiwa, sensei!",
        "status": "saved",
        "entry_id": "some-entry-id"
    }
    saved_item_response = {
        **item_data, 
        "id": "vocab-item-id-123", 
        "user_id": user_id,
        "created_at": "2023-10-27T10:00:00Z", 
        "updated_at": "2023-10-27T10:00:00Z"
    }
    mock_save_vocab.return_value = saved_item_response

    response = client.post("/vocabulary", json=item_data, headers={"X-User-ID": user_id})

    assert response.status_code == 201
    assert response.json()["id"] == "vocab-item-id-123"
    assert response.json()["term"] == "Konnichiwa"
    mock_save_vocab.assert_called_once_with(item_data=item_data, user_id=user_id)

@patch("backend.server.save_vocabulary_item")
def test_add_vocabulary_item_conflict(mock_save_vocab, client):
    user_id = "test-user-id"
    item_data = {"term": "Hola", "language": "Spanish", "definition": "Hello"}
    mock_save_vocab.side_effect = Exception("unique constraint blah blah unique_user_term_language") # Simulate DB conflict

    response = client.post("/vocabulary", json=item_data, headers={"X-User-ID": user_id})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

@patch("backend.server.save_vocabulary_item")
def test_add_vocabulary_item_no_user_id(mock_save_vocab, client):
    item_data = {"term": "Bonjour", "language": "French"}
    response = client.post("/vocabulary", json=item_data)
    assert response.status_code == 401
    mock_save_vocab.assert_not_called()

@patch("backend.server.fetch_user_vocabulary")
def test_get_user_vocabulary_success(mock_fetch_vocab, client):
    user_id = "test-user-id"
    mock_vocab_list = [
        {"id": "id1", "user_id": user_id, "term": "Arigato", "language": "Japanese", "created_at": "2023-10-27T10:00:00Z", "updated_at": "2023-10-27T10:00:00Z"},
        {"id": "id2", "user_id": user_id, "term": "Sayonara", "language": "Japanese", "created_at": "2023-10-26T10:00:00Z", "updated_at": "2023-10-26T10:00:00Z"}
    ]
    mock_fetch_vocab.return_value = mock_vocab_list

    response = client.get("/vocabulary", headers={"X-User-ID": user_id})
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["term"] == "Arigato"
    mock_fetch_vocab.assert_called_once_with(user_id=user_id, language=None)

@patch("backend.server.fetch_user_vocabulary")
def test_get_user_vocabulary_by_language(mock_fetch_vocab, client):
    user_id = "test-user-id"
    mock_fetch_vocab.return_value = [] # Exact data doesn't matter, just the call
    client.get("/vocabulary?language=Japanese", headers={"X-User-ID": user_id})
    mock_fetch_vocab.assert_called_once_with(user_id=user_id, language="Japanese")

@patch("backend.server.fetch_user_vocabulary")
def test_get_user_vocabulary_no_user_id(mock_fetch_vocab, client):
    response = client.get("/vocabulary")
    assert response.status_code == 401
    mock_fetch_vocab.assert_not_called()

@patch("backend.server.delete_vocabulary_item")
def test_delete_vocabulary_item_success(mock_delete_vocab, client):
    user_id = "test-user-id"
    item_id_to_delete = "vocab-id-to-delete"
    mock_delete_vocab.return_value = True

    response = client.delete(f"/vocabulary/{item_id_to_delete}", headers={"X-User-ID": user_id})
    assert response.status_code == 204
    mock_delete_vocab.assert_called_once_with(item_id=item_id_to_delete, user_id=user_id)

@patch("backend.server.delete_vocabulary_item")
def test_delete_vocabulary_item_not_found(mock_delete_vocab, client):
    user_id = "test-user-id"
    item_id_to_delete = "non-existent-vocab-id"
    mock_delete_vocab.return_value = False

    response = client.delete(f"/vocabulary/{item_id_to_delete}", headers={"X-User-ID": user_id})
    assert response.status_code == 404
    assert response.json()["detail"] == f"Vocabulary item with id {item_id_to_delete} not found or not owned by user."

@patch("backend.server.delete_vocabulary_item")
def test_delete_vocabulary_item_no_user_id(mock_delete_vocab, client):
    item_id_to_delete = "some-vocab-id"
    response = client.delete(f"/vocabulary/{item_id_to_delete}")
    assert response.status_code == 401
    mock_delete_vocab.assert_not_called() 
"""
Tests for the Supabase integration.

This module verifies that the Supabase client functions work as expected,
with mocked responses to avoid hitting the actual database during tests.
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.supabase import create_supabase_client, save_entry, fetch_entries


@patch("backend.supabase.create_client")
def test_create_supabase_client(mock_create_client):
    """Test that the Supabase client is created with the correct parameters."""
    # Setup mock
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Call function under test (with patched environment variables)
    with patch("backend.supabase.SUPABASE_URL", "https://test-url.supabase.co"):
        with patch("backend.supabase.SUPABASE_SERVICE_KEY", "test-key"):
            client = create_supabase_client()
    
    # Assertions
    assert client == mock_client
    mock_create_client.assert_called_once_with("https://test-url.supabase.co", "test-key")


@patch("backend.supabase.create_supabase_client")
def test_save_entry(mock_create_client):
    """Test that save_entry correctly calls Supabase insert with the entry data."""
    # Setup mock client and response
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()
    
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock(data=[{"id": "test-id", "created_at": "2023-05-05T12:00:00Z"}])
    
    mock_create_client.return_value = mock_client
    
    # Test data
    entry_data = {
        "user_id": None,
        "original_text": "Test entry",
        "corrected": "Test entry",
        "rewrite": "Test entry (more natural)",
        "score": 85,
        "tone": "Neutral",
        "translation": "Translated version of: Test entry"
    }
    
    # Call function under test
    result = save_entry(entry_data)
    
    # Assertions
    mock_client.table.assert_called_once_with("journal_entries")
    mock_table.insert.assert_called_once_with(entry_data)
    mock_insert.execute.assert_called_once()
    
    assert result == {"id": "test-id", "created_at": "2023-05-05T12:00:00Z"}


@patch("backend.supabase.create_supabase_client")
def test_fetch_entries_no_user_id(mock_create_client):
    """Test that fetch_entries correctly retrieves all entries when no user_id is provided."""
    # Setup mock client and response
    mock_table = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()
    
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit
    
    # Mock data to be returned
    mock_entries = [
        {"id": "1", "user_id": None, "original_text": "Entry 1", "created_at": "2023-05-05T12:00:00Z"},
        {"id": "2", "user_id": None, "original_text": "Entry 2", "created_at": "2023-05-04T12:00:00Z"}
    ]
    mock_limit.execute.return_value = MagicMock(data=mock_entries)
    
    mock_create_client.return_value = mock_client
    
    # Call function under test
    result = fetch_entries()
    
    # Assertions
    mock_client.table.assert_called_once_with("journal_entries")
    mock_table.order.assert_called_once_with("created_at", desc=True)
    mock_order.limit.assert_called_once_with(20)  # Default limit
    mock_limit.execute.assert_called_once()
    
    assert result == mock_entries


@patch("backend.supabase.create_supabase_client")
def test_fetch_entries_with_user_id(mock_create_client):
    """Test that fetch_entries correctly filters by user_id when provided."""
    # Setup mock client and response
    mock_table = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_eq = MagicMock()
    mock_execute = MagicMock()
    
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit
    mock_limit.eq.return_value = mock_eq
    
    # Mock data to be returned
    mock_entries = [
        {"id": "1", "user_id": "user123", "original_text": "Entry 1", "created_at": "2023-05-05T12:00:00Z"},
        {"id": "2", "user_id": "user123", "original_text": "Entry 2", "created_at": "2023-05-04T12:00:00Z"}
    ]
    mock_eq.execute.return_value = MagicMock(data=mock_entries)
    
    mock_create_client.return_value = mock_client
    
    # Call function under test
    result = fetch_entries(user_id="user123", limit=5)
    
    # Assertions
    mock_client.table.assert_called_once_with("journal_entries")
    mock_table.order.assert_called_once_with("created_at", desc=True)
    mock_order.limit.assert_called_once_with(5)
    mock_limit.eq.assert_called_once_with("user_id", "user123")
    mock_eq.execute.assert_called_once()
    
    assert result == mock_entries


@patch("backend.supabase.create_supabase_client")
def test_fetch_entries_empty_result(mock_create_client):
    """Test that fetch_entries handles empty results correctly."""
    # Setup mock client and response
    mock_table = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit
    
    # Mock empty data response
    mock_limit.execute.return_value = MagicMock(data=[])
    
    mock_create_client.return_value = mock_client
    
    # Call function under test
    result = fetch_entries()
    
    # Assertions
    assert result == [] 
"""
Tests for the Mistral-7B-Instruct-v0.3 integration.

This module contains tests for the mistral_engine.py functionality:
- Successful case: Basic text generation works
- Failure case: Invalid model path handling
- Edge case: Empty input handling
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
import mistral_engine


class TestMistralEngine:
    """Test suite for the Mistral engine integration."""
    
    @pytest.fixture
    def mock_model_and_tokenizer(self):
        """Fixture to provide mocked model and tokenizer."""
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        
        # Configure mock tokenizer to return a properly structured input for the model
        mock_tokenizer.apply_chat_template.return_value = MagicMock(to=lambda x: x)
        
        # Configure mock model to generate a sequence when called
        mock_model.generate.return_value = [1, 2, 3]  # Mock token IDs
        
        # Configure mock tokenizer to decode the output
        mock_tokenizer.decode.return_value = "This is a mock response from the model."
        
        return mock_model, mock_tokenizer
    
    @pytest.mark.skip(reason="Requires actual model download, use only for manual testing")
    def test_download_model_real(self):
        """Test actual model download (skipped by default)."""
        # This test will actually download the model, so we mark it as skipped by default
        model_path = mistral_engine.download_model()
        assert model_path.exists()
        assert (model_path / "tokenizer.model.v3").exists()
    
    def test_download_model_mock(self):
        """Test model download with mocked snapshot_download."""
        # Mock the snapshot_download
        with patch('mistral_engine.snapshot_download') as mock_download:
            # Set a test path
            test_path = Path('/tmp/test_mistral_model')
            
            # Make sure path exists for the checks
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = False
                with patch('pathlib.Path.mkdir') as mock_mkdir:
                    # Call the function
                    path = mistral_engine.download_model(str(test_path))
                    
                    # Verify correct path is returned
                    assert path == test_path
                    
                    # Verify download was called
                    mock_download.assert_called_once()
    
    def test_generate_text_success(self, mock_model_and_tokenizer):
        """
        SUCCESSFUL CASE:
        Test that text generation works with model and tokenizer.
        """
        mock_model, mock_tokenizer = mock_model_and_tokenizer
        
        # Test with a simple prompt
        prompt = "Hello, Mistral!"
        result = mistral_engine.generate_text(prompt, mock_model, mock_tokenizer)
        
        # Verify the expected interactions and result
        assert result == "This is a mock response from the model."
        mock_tokenizer.apply_chat_template.assert_called_once()
        mock_model.generate.assert_called_once()
        mock_tokenizer.decode.assert_called_once()
    
    def test_generate_text_failure(self):
        """
        FAILURE CASE:
        Test that appropriate error is raised when model fails.
        """
        # Use a clearly invalid model path
        with patch('mistral_engine.load_model') as mock_load:
            mock_load.side_effect = Exception("Model loading failed")
            
            # Test with a simple prompt, expecting an exception
            with pytest.raises(Exception) as exc_info:
                mistral_engine.generate_text("Test prompt")
            
            # Verify the error message is propagated
            assert "Model loading failed" in str(exc_info.value)
    
    def test_generate_text_empty_input(self, mock_model_and_tokenizer):
        """
        EDGE CASE:
        Test handling of empty input text.
        """
        mock_model, mock_tokenizer = mock_model_and_tokenizer
        
        # Test with empty prompt
        prompt = ""
        result = mistral_engine.generate_text(prompt, mock_model, mock_tokenizer)
        
        # Empty input should still work and return the mocked response
        assert result == "This is a mock response from the model."
        mock_tokenizer.apply_chat_template.assert_called_once()
    
    def test_analyze_entry_json_parsing(self, mock_model_and_tokenizer):
        """Test parsing of JSON responses in analyze_entry."""
        mock_model, mock_tokenizer = mock_model_and_tokenizer
        
        # Create a mock JSON response
        mock_json = {
            "corrected": "Corrected text",
            "rewrite": "Rewritten text",
            "fluency_score": 85,
            "tone": "Confident",
            "translation": "Translated text",
            "explanation": "Explanation text"
        }
        
        # Mock generate_text to return a JSON string
        with patch('mistral_engine.generate_text') as mock_generate:
            mock_generate.return_value = json.dumps(mock_json)
            
            # Call analyze_entry
            result = mistral_engine.analyze_entry("Test text")
            
            # Verify the parsed response matches our mock JSON
            assert result["corrected"] == "Corrected text"
            assert result["rewrite"] == "Rewritten text"
            assert result["fluency_score"] == 85
            assert result["tone"] == "Confident"
            assert result["translation"] == "Translated text"
            assert result["explanation"] == "Explanation text"
    
    def test_analyze_entry_missing_fields(self, mock_model_and_tokenizer):
        """Test handling of missing fields in JSON response."""
        mock_model, mock_tokenizer = mock_model_and_tokenizer
        
        # Create a mock JSON response with missing fields
        mock_json = {
            "corrected": "Corrected text",
            # missing "rewrite"
            "fluency_score": 85,
            # missing "tone"
            # missing "translation"
            "explanation": "Explanation text"
        }
        
        # Mock generate_text to return a JSON string
        with patch('mistral_engine.generate_text') as mock_generate:
            mock_generate.return_value = json.dumps(mock_json)
            
            # Call analyze_entry
            result = mistral_engine.analyze_entry("Test text")
            
            # Verify the missing fields are filled with defaults
            assert result["corrected"] == "Corrected text"
            assert result["rewrite"] == "Test text"  # Default is original text
            assert result["fluency_score"] == 85
            assert result["tone"] == "Neutral"  # Default tone
            assert result["translation"] == "Test text"  # Default is original text
            assert result["explanation"] == "Explanation text" 
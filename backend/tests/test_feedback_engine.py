"""
Tests for the AI feedback engine.

This module verifies that the feedback generation functions produce 
the expected output structure and data types.
"""
import pytest
from typing import Dict, Any

from backend.feedback_engine import generate_feedback, analyze_entry


def test_feedback_structure():
    """Test that generate_feedback returns a dictionary with the expected keys."""
    sample_text = "This is a test journal entry."
    result = generate_feedback(sample_text)
    
    # Verify the structure of the feedback dictionary
    assert isinstance(result, dict)
    assert "corrected" in result
    assert "rewritten" in result
    assert "score" in result
    assert "tone" in result
    assert "translation" in result
    assert "explanation" in result


def test_feedback_types():
    """Test that the feedback values have the expected data types."""
    sample_text = "This is a test journal entry."
    result = generate_feedback(sample_text)
    
    # Verify the data types
    assert isinstance(result["corrected"], str)
    assert isinstance(result["rewritten"], str)
    assert isinstance(result["score"], int)
    assert isinstance(result["tone"], str)
    assert isinstance(result["translation"], str)
    assert isinstance(result["explanation"], str) or result["explanation"] is None
    
    # Verify score range
    assert 0 <= result["score"] <= 100


def test_empty_input():
    """Test that the feedback engine handles empty input correctly."""
    result = generate_feedback("")
    
    # Even with empty input, should return the expected structure
    assert isinstance(result, dict)
    assert all(key in result for key in ["corrected", "rewritten", "score", "tone", "translation", "explanation"])


def test_analyze_entry_normal_input():
    """Test analyze_entry with normal Spanish text input."""
    input_text = "Hoy fui al mercado y compré frutas frescas."
    result = analyze_entry(input_text)
    
    # Verify result is a dictionary with expected keys
    assert isinstance(result, dict)
    expected_keys = {"corrected", "rewrite", "fluency_score", "tone", "translation"}
    assert set(result.keys()) == expected_keys
    
    # Verify fluency_score is in valid range
    assert isinstance(result["fluency_score"], int)
    assert 70 <= result["fluency_score"] <= 100
    
    # Verify tone is one of the expected values
    assert result["tone"] in ["Reflective", "Confident", "Neutral"]
    
    # Verify other fields
    assert result["corrected"] == input_text
    assert isinstance(result["rewrite"], str)
    assert isinstance(result["translation"], str)


def test_analyze_entry_empty_input():
    """Test analyze_entry with empty string input."""
    input_text = ""
    result = analyze_entry(input_text)
    
    # Verify result is a dictionary with expected keys
    assert isinstance(result, dict)
    expected_keys = {"corrected", "rewrite", "fluency_score", "tone", "translation"}
    assert set(result.keys()) == expected_keys
    
    # Verify fluency_score is in valid range
    assert isinstance(result["fluency_score"], int)
    assert 70 <= result["fluency_score"] <= 100
    
    # Verify tone is one of the expected values
    assert result["tone"] in ["Reflective", "Confident", "Neutral"]
    
    # Verify empty input is handled appropriately
    assert result["corrected"] == ""
    assert result["rewrite"] == " (more natural)"
    assert result["translation"] == "Translated version of: "


def test_analyze_entry_long_input():
    """Test analyze_entry with a simulated long text input (300 words)."""
    # Generate a long text by repeating a sentence multiple times
    base_sentence = "Este es un párrafo largo para probar el análisis de texto. "
    # A sentence with roughly 10 words, repeated 30 times should give ~300 words
    input_text = base_sentence * 30
    
    result = analyze_entry(input_text)
    
    # Verify result is a dictionary with expected keys
    assert isinstance(result, dict)
    expected_keys = {"corrected", "rewrite", "fluency_score", "tone", "translation"}
    assert set(result.keys()) == expected_keys
    
    # Verify fluency_score is in valid range
    assert isinstance(result["fluency_score"], int)
    assert 70 <= result["fluency_score"] <= 100
    
    # Verify tone is one of the expected values
    assert result["tone"] in ["Reflective", "Confident", "Neutral"]
    
    # Verify the long input is handled correctly
    assert result["corrected"] == input_text
    assert isinstance(result["rewrite"], str)
    assert isinstance(result["translation"], str)
    assert len(result["translation"]) > len(input_text) / 2  # Simple check that translation exists

# TODO: Add more comprehensive tests once actual AI feedback implementation is complete 
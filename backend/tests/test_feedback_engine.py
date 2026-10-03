"""
Tests for the AI feedback engine.

This module verifies that the feedback generation functions produce 
the expected output structure and data types.
"""
import pytest
from typing import Dict, Any

from backend.feedback_engine import generate_feedback, analyze_entry


@pytest.mark.asyncio
async def test_feedback_structure():
    """Test that generate_feedback returns a dictionary with the expected keys."""
    sample_text = "This is a test journal entry."
    language = "English"
    result = await generate_feedback(sample_text, language)
    
    # Verify the structure of the feedback dictionary
    assert isinstance(result, dict)
    assert "corrected" in result
    assert "rewritten" in result
    assert "score" in result
    assert "tone" in result
    assert "translation" in result
    assert "explanation" in result


@pytest.mark.asyncio
async def test_feedback_types():
    """Test that the feedback values have the expected data types."""
    sample_text = "This is a test journal entry."
    language = "English"
    result = await generate_feedback(sample_text, language)
    
    # Verify the data types
    assert isinstance(result["corrected"], str)
    assert isinstance(result["rewritten"], str)
    assert isinstance(result["score"], int)
    assert isinstance(result["tone"], str)
    assert isinstance(result["translation"], str)
    assert isinstance(result["explanation"], str) or result["explanation"] is None
    
    # Verify score range
    assert 0 <= result["score"] <= 100


@pytest.mark.asyncio
async def test_empty_input():
    """Test that the feedback engine handles empty input correctly."""
    language = "English"
    result = await generate_feedback("", language)
    
    # Even with empty input, should return the expected structure
    assert isinstance(result, dict)
    assert all(key in result for key in ["corrected", "rewritten", "score", "tone", "translation", "explanation"])


EXPECTED_ANALYSIS_KEYS = {"corrected", "rewrite", "score", "tone", "translation", "explanation"}
EXPECTED_TONES = {"Reflective", "Confident", "Neutral", "Inquisitive"}


def assert_analysis_shape(result: Dict[str, Any]) -> None:
    assert isinstance(result, dict)
    assert EXPECTED_ANALYSIS_KEYS <= set(result.keys())
    assert isinstance(result["score"], int)
    assert 70 <= result["score"] <= 100
    assert result["tone"] in EXPECTED_TONES
    assert isinstance(result["rewrite"], str)
    assert isinstance(result["translation"], str)


@pytest.mark.asyncio
async def test_analyze_entry_normal_input():
    """Test analyze_entry with normal Spanish text input."""
    input_text = "Hoy fui al mercado y compré frutas frescas."
    result = await analyze_entry(input_text, "Spanish")

    assert_analysis_shape(result)
    assert input_text in result["corrected"]
    assert input_text in result["rewrite"]


@pytest.mark.asyncio
async def test_analyze_entry_empty_input():
    """Test analyze_entry with empty string input."""
    result = await analyze_entry("", "English")

    assert_analysis_shape(result)
    assert result["grammar_suggestions"] == []
    assert result["new_words"] == []


@pytest.mark.asyncio
async def test_analyze_entry_long_input():
    """Test analyze_entry with a simulated long text input (300 words)."""
    input_text = "Este es un párrafo largo para probar el análisis de texto. " * 30
    result = await analyze_entry(input_text, "Spanish")

    assert_analysis_shape(result)
    assert input_text in result["corrected"]
    assert input_text in result["translation"]

"""Behavioral tests for Gemini's authoritative sentence mapping."""
import logging

import pytest
from pydantic import ValidationError

from ai.schemas import GeminiJournalFeedback, JournalFeedback, SentenceMapping
from server import _build_feedback_response


def feedback(corrected: str, mapping: list[dict]) -> JournalFeedback:
    return JournalFeedback(
        corrected=corrected,
        rewrite=corrected,
        score=80,
        tone="Neutral",
        explanation="",
        rubric={"grammar": 80, "vocabulary": 80, "complexity": 80},
        sentence_mapping=mapping,
    )


def test_gemini_schema_requires_mapping_and_index_list_shape():
    assert "sentence_mapping" in GeminiJournalFeedback.model_json_schema()["required"]
    with pytest.raises(ValidationError):
        SentenceMapping(source_sentence=0)
    with pytest.raises(ValidationError):
        SentenceMapping(source_sentence=0, corrected_sentences="not-a-list")


@pytest.mark.parametrize(
    ("original", "corrected", "mapping"),
    [
        (
            "Fui al cine. Comimos palomitas.",
            "Fui al cine y comimos palomitas.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": [0]},
            ],
        ),
        (
            "El día es largo. Que es así.",
            "El día es largo.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": []},
            ],
        ),
        (
            "Fui al cine y comimos palomitas.",
            "Fui al cine. Comimos palomitas.",
            [{"source_sentence": 0, "corrected_sentences": [0, 1]}],
        ),
        (
            "Hola. Adiós.",
            "Hola. Adiós.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": [1]},
            ],
        ),
    ],
)
def test_mapping_accepts_merged_removed_split_and_unchanged(original, corrected, mapping):
    response = _build_feedback_response(feedback(corrected, mapping), original)
    assert response.sentence_mapping_status == "valid"
    assert response.sentence_mapping == mapping


def test_inconsistent_mapping_is_rejected_and_logged(caplog):
    result = feedback(
        "Primera. Segunda.",
        [{"source_sentence": 0, "corrected_sentences": [0]}],
    )
    with caplog.at_level(logging.WARNING):
        response = _build_feedback_response(result, "Primera. Segunda.")
    assert response.sentence_mapping is None
    assert response.sentence_mapping_status == "invalid"
    assert "using legacy heuristic" in caplog.text


@pytest.mark.parametrize("bad_index", [-1, 2])
def test_bad_corrected_indexes_fall_back_instead_of_failing_feedback(bad_index, caplog):
    result = feedback(
        "Primera.",
        [{"source_sentence": 0, "corrected_sentences": [bad_index]}],
    )
    with caplog.at_level(logging.WARNING):
        response = _build_feedback_response(result, "Primera.")
    assert response.sentence_mapping is None
    assert response.sentence_mapping_status == "invalid"
    assert "using legacy heuristic" in caplog.text

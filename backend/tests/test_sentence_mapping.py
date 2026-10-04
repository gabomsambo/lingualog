"""Behavioral tests for Gemini's authoritative sentence mapping."""
import logging

import pytest
from pydantic import ValidationError

from ai.schemas import GeminiJournalFeedback, JournalFeedback, SentenceAction, SentenceMapping
from server import _build_feedback_response


def feedback(
    corrected: str,
    mapping: list[dict],
    actions: list[dict] | None = None,
) -> JournalFeedback:
    return JournalFeedback(
        corrected=corrected,
        rewrite=corrected,
        score=80,
        tone="Neutral",
        explanation="",
        rubric={"grammar": 80, "vocabulary": 80, "complexity": 80},
        sentence_mapping=mapping,
        sentence_actions=actions or [],
    )


def test_gemini_schema_requires_mapping_actions_and_index_list_shape():
    required = GeminiJournalFeedback.model_json_schema()["required"]
    assert "sentence_mapping" in required
    assert "sentence_actions" in required
    with pytest.raises(ValidationError):
        SentenceMapping(source_sentence=0)
    with pytest.raises(ValidationError):
        SentenceMapping(source_sentence=0, corrected_sentences="not-a-list")
    # `source_sentence` and `action` are required; `reason` defaults to "".
    with pytest.raises(ValidationError):
        SentenceAction(action="removed", reason="ok")
    with pytest.raises(ValidationError):
        SentenceAction(source_sentence=0, reason="ok")


def test_schema_only_accepts_removed_or_merged_actions():
    with pytest.raises(ValidationError):
        SentenceAction(source_sentence=0, action="kept", reason="ok")


@pytest.mark.parametrize(
    ("original", "corrected", "mapping", "actions"),
    [
        (
            "Fui al cine. Comimos palomitas.",
            "Fui al cine y comimos palomitas.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": [0]},
            ],
            [
                {
                    "source_sentence": 1,
                    "action": "merged",
                    "reason": "Two source sentences glued into one corrected sentence.",
                    "reason_l1": "Two source sentences glued into one corrected sentence.",
                    "reason_l2": "",
                }
            ],
        ),
        (
            "El día es largo. Que es así.",
            "El día es largo.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": []},
            ],
            [
                {
                    "source_sentence": 1,
                    "action": "removed",
                    "reason": "La segunda frase es un fragmento sin verbo que solo repite la primera.",
                    "reason_l1": "The second sentence is a fragment with no verb that just echoes the first.",
                    "reason_l2": "",
                }
            ],
        ),
        (
            "Fui al cine y comimos palomitas.",
            "Fui al cine. Comimos palomitas.",
            [{"source_sentence": 0, "corrected_sentences": [0, 1]}],
            [],
        ),
        (
            "Hola. Adiós.",
            "Hola. Adiós.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": [1]},
            ],
            [],
        ),
    ],
)
def test_mapping_accepts_merged_removed_split_and_unchanged(original, corrected, mapping, actions):
    response = _build_feedback_response(feedback(corrected, mapping, actions), original)
    assert response.sentence_mapping_status == "valid"
    assert response.sentence_mapping == mapping
    # An action is required only when at least one source was removed or merged
    # (owns no corrected sentence of its own). A pure split keeps every row
    # populated, so actions should be empty.
    owner: dict[int, int] = {}
    for item in mapping:
        for target_index in item["corrected_sentences"]:
            owner.setdefault(target_index, item["source_sentence"])
    any_action_needed = any(
        not item["corrected_sentences"]
        or all(owner[idx] != item["source_sentence"] for idx in item["corrected_sentences"])
        for item in mapping
    )
    if any_action_needed:
        assert response.sentence_actions == actions
    else:
        assert response.sentence_actions is None


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


def test_odd_sentence_corrected_in_place_is_accepted():
    """An odd learner sentence ("Que es así.") is corrected in place, not dropped."""
    response = _build_feedback_response(
        feedback(
            "Es así.",
            [{"source_sentence": 0, "corrected_sentences": [0]}],
            [],
        ),
        "Que es así.",
    )
    assert response.sentence_mapping_status == "valid"
    assert response.sentence_actions is None


def test_removal_with_explanation_is_accepted():
    response = _build_feedback_response(
        feedback(
            "Hola. ¿Cómo estás?",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": []},
                {"source_sentence": 2, "corrected_sentences": [1]},
            ],
            [
                {
                    "source_sentence": 1,
                    "action": "removed",
                    "reason": "Exact duplicate of the previous sentence.",
                    "reason_l1": "Exact duplicate of the previous sentence.",
                    "reason_l2": "",
                }
            ],
        ),
        "Hola. Hola. ¿Cómo estás?",
    )
    assert response.sentence_mapping_status == "valid"
    assert response.sentence_actions[0]["action"] == "removed"


@pytest.mark.parametrize("missing_actions", [None, [], [
    {"source_sentence": 0, "action": "removed", "reason": "", "reason_l1": "", "reason_l2": ""}
]])
def test_removal_without_explanation_is_a_contract_violation(caplog, missing_actions):
    """A mapping with a removed sentence but no real action reason must be rejected."""
    result = feedback(
        "El día es largo.",
        [
            {"source_sentence": 0, "corrected_sentences": [0]},
            {"source_sentence": 1, "corrected_sentences": []},
        ],
        missing_actions,
    )
    with caplog.at_level(logging.WARNING):
        response = _build_feedback_response(result, "El día es largo. Que es así.")
    assert response.sentence_mapping is None
    assert response.sentence_actions is None
    assert response.sentence_mapping_status == "invalid_no_explanation"
    assert "without an explanation" in caplog.text


def test_merge_without_explanation_is_a_contract_violation(caplog):
    result = feedback(
        "Fui al cine y comimos palomitas.",
        [
            {"source_sentence": 0, "corrected_sentences": [0]},
            {"source_sentence": 1, "corrected_sentences": [0]},
        ],
        [
            {
                "source_sentence": 1,
                "action": "merged",
                "reason": "",
                "reason_l1": "",
                "reason_l2": "",
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        response = _build_feedback_response(result, "Fui al cine. Comimos palomitas.")
    assert response.sentence_mapping is None
    assert response.sentence_actions is None
    assert response.sentence_mapping_status == "invalid_no_explanation"
    assert "empty explanation" in caplog.text


def test_action_kind_mismatch_is_a_contract_violation(caplog):
    """A sentence_actions item whose `action` does not match the mapping is rejected."""
    result = feedback(
        "El día es largo.",
        [
            {"source_sentence": 0, "corrected_sentences": [0]},
            {"source_sentence": 1, "corrected_sentences": []},
        ],
        [
            {
                "source_sentence": 1,
                "action": "merged",
                "reason": "Something.",
                "reason_l1": "Something.",
                "reason_l2": "",
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        response = _build_feedback_response(result, "El día es largo. Que es así.")
    assert response.sentence_mapping is None
    assert response.sentence_actions is None
    assert response.sentence_mapping_status == "invalid_no_explanation"


def test_action_reason_falls_back_to_language_specific_slot():
    """A blank `reason` but populated `reason_l1` still satisfies the contract."""
    response = _build_feedback_response(
        feedback(
            "El día es largo.",
            [
                {"source_sentence": 0, "corrected_sentences": [0]},
                {"source_sentence": 1, "corrected_sentences": []},
            ],
            [
                {
                    "source_sentence": 1,
                    "action": "removed",
                    "reason": "",
                    "reason_l1": "Repeated fragment.",
                    "reason_l2": "",
                }
            ],
        ),
        "El día es largo. Que es así.",
    )
    assert response.sentence_mapping_status == "valid"
    assert response.sentence_actions[0]["reason"] == "Repeated fragment."

"""
Prompt Builder for AI Analysis

This module constructs system prompts and user messages for AI-powered journal entry analysis.
It uses effective language settings to customize prompts while maintaining consistent JSON output.
"""

from typing import Dict, Any, Tuple
import json
import logging
from lang_policy import EffectiveSettings, explanation_instruction

logger = logging.getLogger(__name__)


# System template for AI analysis (always in English for consistency)
SYSTEM_TEMPLATE = """You are an expert language learning assistant specializing in journal entry analysis. Your task is to analyze a journal entry written in a target language and provide comprehensive feedback to help the learner improve.

**ANALYSIS REQUIREMENTS:**
Analyze the journal entry for:
1. Grammar corrections (fix grammatical errors while preserving meaning)
2. Native-like rewriting (rewrite to sound more natural and fluent)
3. Overall fluency score (0-100 scale)
4. Emotional tone detection
5. Detailed explanation of corrections and improvements
6. Rubric scoring for grammar, vocabulary, and complexity
7. Grammar suggestions with specific corrections
8. New vocabulary words with definitions and examples

**LANGUAGE SETTINGS:**
{explanation_instruction}

**OUTPUT FORMAT:**
You must respond with a valid JSON object containing exactly these fields:

{{
  "corrected": "Grammar-corrected version of the text, fixing errors while preserving original meaning and style",
  "rewrite": "Native-like rewrite that sounds natural and fluent while maintaining the original message",
  "score": 85,
  "tone": "One of: Happy, Sad, Excited, Anxious, Confident, Frustrated, Neutral, Reflective, Hopeful, Determined",
  "explanation": "Detailed explanation of corrections, improvements, and learning points following the language settings above",
  "rubric": {{
    "grammar": 80,
    "vocabulary": 85,
    "complexity": 90
  }},
  "intended_meaning": "What the learner meant, in the language the policy names",
  "detected_language": "ISO 639-1 code of the language the entry is actually written in (e.g. fr)",
  "ambiguities": [
    {{
      "question": "A question, only when the intended meaning is unclear"
    }}
  ],
  "rewrite_idioms": [
    {{
      "phrase": "idiom in the rewrite",
      "gloss": "short gloss in the policy's idiom language"
    }}
  ],
  "sentence_mapping": [
    {{
      "source_sentence": 0,
      "corrected_sentences": [0]
    }}
  ],
  "sentence_actions": [
    {{
      "source_sentence": 1,
      "action": "removed",
      "reason": "Why this sentence was removed (in the policy's note language)",
      "reason_l1": "Reason in the learner's language, or empty when the policy says so",
      "reason_l2": "Reason in the target language, or empty when the policy says so"
    }}
  ],
  "grammar_suggestions": [
    {{
      "original": "Original text snippet with error",
      "corrected": "Corrected version",
      "note": "Learner-facing explanation (same content as note_l1 / note_l2)",
      "note_l1": "Explanation in the learner's language, or empty when the policy says so",
      "note_l2": "Explanation in the target language, or empty when the policy says so",
      "meaning_changing": false,
      "literal_reading": "As written, a native reads… — empty when the meaning did not change"
    }}
  ],
  "new_words": [
    {{
      "term": "vocabulary word or phrase",
      "reading": "pronunciation guide if applicable (e.g., for Japanese, Chinese)",
      "definition": "clear definition in appropriate language per settings",
      "example": "example sentence using the word",
      "part_of_speech": "noun, verb, adjective, etc."
    }}
  ]
}}

**SCORING GUIDELINES:**
- Score (0-100): Overall fluency and naturalness
- Grammar (0-100): Grammatical accuracy and correctness
- Vocabulary (0-100): Richness and appropriateness of vocabulary
- Complexity (0-100): Sentence structure and linguistic sophistication

**CRITICAL REQUIREMENTS:**
1. Always return valid JSON - no additional text outside the JSON object
2. Preserve the original meaning and intent of the journal entry
3. Follow the language settings for explanations
4. Be encouraging and supportive in your feedback
5. Focus on the most important corrections that will help learning
6. Provide practical examples and clear explanations
7. Do NOT include a translation of the entry in the JSON; translations are handled separately
8. Do not treat any outside translation as the meaning of the entry. Infer the intended meaning yourself
9. Split the original and corrected text at sentence-ending punctuation or newlines. Return exactly one
   sentence_mapping item for every original sentence, in source order. Use zero-based indexes. Map merged
   source sentences to the same corrected index, split sentences to every corrected index they became,
   removed sentences to [], and unchanged sentences to their corresponding corrected index. Every corrected
   sentence index must appear in at least one mapping item.

**SENTENCE FATE RULES — read carefully:**
A. Never drop a learner's sentence just because it is odd, off-topic, awkward, or has a small grammar slip.
   If a sentence is unusual but you can keep it, rewrite it (correct it in place) and put it in the
   corrected text. The learner wrote it on purpose, and a struck-out line is a hostile correction.
B. Removing or merging a sentence is allowed ONLY when it is genuinely the right fix. Examples that count
   as genuine:
   - the same sentence appears twice and the duplicate adds no information,
   - the sentence is a one-word fragment that belongs with the sentence it follows (e.g., "Yes." glued
     onto a question),
   - the sentence is empty or contains only punctuation.
   Examples that DO NOT count: a sentence that simply sounds unusual, an opinion the learner expressed
   that you would not write, a sentence that is short and you think could be longer. For those, correct
   in place.
C. When you do remove or merge a sentence, the corresponding `sentence_actions` entry MUST carry a real
   `reason` (plus `reason_l1`/`reason_l2` per the policy). The reason appears verbatim in the
   learner's "What to fix" panel, beside the original sentence. A removal or merge with no reason is
   treated as a contract violation by the server and the mapping will be discarded, so always fill it
   in. The reason must explain what the duplication/fragment was and why merging or removing it was the
   right call.
D. `sentence_actions` MUST contain exactly one entry for every source sentence that is removed or merged:
   - removed: its `corrected_sentences` is empty. Use action "removed".
   - merged: every corrected index it lists is already listed by an earlier source sentence. Use action
     "merged". Example: "Sí. Voy mañana." -> "Sí, voy mañana." maps source 0 to [0] and source 1 to [0],
     so source 1 needs a "merged" action.
   A split needs no action: "Fui al cine y comí." -> "Fui al cine. Comí." maps source 0 to [0, 1].
   Leave `sentence_actions` empty when no source sentence is removed or merged.
E. Every JSON object you return MUST include the keys `sentence_mapping` and `sentence_actions`
   verbatim. The server discards the mapping when those keys are missing, so the side-by-side page
   silently loses its authoritative alignment. Do not omit them under any circumstance; an empty
   `sentence_mapping` is acceptable only when the entry itself has no sentences.

Remember: Your response must be a single, valid JSON object that can be parsed programmatically."""


def build_messages(entry_text: str, effective: EffectiveSettings) -> Tuple[str, Dict[str, Any]]:
    """
    Build system prompt and user payload for AI analysis.
    
    Args:
        entry_text: The journal entry text to analyze
        effective: Resolved effective language settings
        
    Returns:
        Tuple of (system_prompt, user_payload)
        
    Example:
        system, user_data = build_messages("Hoy fui al mercado", effective_settings)
        # system contains the full system prompt with language instructions
        # user_data contains structured data about the entry and settings
    """
    # Generate explanation instruction based on settings
    explanation_instr = explanation_instruction(effective)
    
    # Build system prompt with language settings
    system_prompt = SYSTEM_TEMPLATE.format(
        explanation_instruction=explanation_instr
    )
    
    # Build user payload with entry and metadata
    user_payload = {
        "entry_text": entry_text,
        "target_language": effective.l2,
        "native_language": effective.l1,
        "ui_language": effective.ui_language,
        "explanation_mode": effective.explanation_mode,
        "translation_policy": effective.translation_policy,
        "strictness": effective.strictness,
        "formality": effective.formality,
        "immersion_level": effective.immersion_level,
        "proficiency": _proficiency(effective),
        "proficiency_estimate": _proficiency(effective),
        "explanation": getattr(effective, "explanation", ""),
        "meaning": getattr(effective, "meaning", ""),
        "rewrite_gloss": getattr(effective, "rewrite_gloss", ""),
        "analysis_request": f"Please analyze this journal entry written in {effective.l2}."
    }
    
    logger.info(f"Built prompt for {len(entry_text)} chars in {effective.l2}, "
               f"explanation_mode={effective.explanation_mode}, "
               f"translation_policy={effective.translation_policy}")
    
    return system_prompt, user_payload


def build_user_message(entry_text: str, effective: EffectiveSettings) -> str:
    """
    Build a user message string that includes the entry and context.
    
    This is an alternative to build_messages() for APIs that expect a simple string.
    
    Args:
        entry_text: The journal entry text to analyze
        effective: Resolved effective language settings
        
    Returns:
        Formatted user message string
    """
    context_info = {
        "target_language": effective.l2,
        "native_language": effective.l1,
        "explanation_mode": effective.explanation_mode,
        "strictness": effective.strictness,
        "formality": effective.formality,
        "immersion_level": effective.immersion_level,
        "proficiency": _proficiency(effective),
    }

    message = f"""Please analyze this journal entry:

ENTRY TEXT:
{entry_text}

CONTEXT:
- Written in: {effective.l2}
- Learner's native language: {effective.l1}
- Explanation style: {effective.explanation_mode}
- Correction level: {effective.strictness}
- Tone: {effective.formality}
- Immersion level: {effective.immersion_level} (0 = native-first, 3 = full immersion)
- Proficiency: {_proficiency(effective)} (A1-C2, separate from immersion)

Please provide your analysis as a JSON object following the specified format."""
    
    return message


def validate_ai_response(response_data: Dict[str, Any]) -> bool:
    """
    Validate that AI response contains all required fields.
    
    Args:
        response_data: AI response parsed as dictionary
        
    Returns:
        True if response is valid
        
    Raises:
        ValueError: If response is missing required fields
    """
    required_fields = {
        'corrected', 'rewrite', 'score', 'tone',
        'explanation', 'rubric', 'grammar_suggestions', 'new_words'
    }
    
    missing_fields = required_fields - set(response_data.keys())
    if missing_fields:
        raise ValueError(f"AI response missing required fields: {missing_fields}")
    
    # Validate rubric structure
    if not isinstance(response_data['rubric'], dict):
        raise ValueError("Rubric must be a dictionary")
    
    required_rubric_fields = {'grammar', 'vocabulary', 'complexity'}
    missing_rubric = required_rubric_fields - set(response_data['rubric'].keys())
    if missing_rubric:
        raise ValueError(f"Rubric missing required fields: {missing_rubric}")
    
    # Validate arrays
    if not isinstance(response_data['grammar_suggestions'], list):
        raise ValueError("grammar_suggestions must be a list")
    
    if not isinstance(response_data['new_words'], list):
        raise ValueError("new_words must be a list")
    
    # Validate score ranges
    score = response_data['score']
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        raise ValueError(f"Score must be 0-100, got: {score}")
    
    for field in ['grammar', 'vocabulary', 'complexity']:
        rubric_score = response_data['rubric'][field]
        if not isinstance(rubric_score, (int, float)) or not (0 <= rubric_score <= 100):
            raise ValueError(f"Rubric {field} must be 0-100, got: {rubric_score}")
    
    return True


def extract_snapshot_data(effective: EffectiveSettings) -> Dict[str, Any]:
    """
    Extract snapshot data for database storage.
    
    Args:
        effective: Resolved effective language settings
        
    Returns:
        Dictionary with snapshot fields for database
    """
    snapshot = {
        "target_language": effective.l2,
        "ui_language_snapshot": effective.ui_language,
        "explanation_language_snapshot": _get_explanation_language_snapshot(effective),
        "translation_policy_snapshot": effective.translation_policy,
        "proficiency_estimate": _proficiency(effective)
    }
    
    return snapshot


def _get_explanation_language_snapshot(effective: EffectiveSettings) -> str:
    """Get the language(s) used for explanations as a snapshot value."""
    if effective.explanation_mode == 'native_only':
        return effective.l1
    elif effective.explanation_mode == 'target_only':
        return effective.l2
    elif effective.explanation_mode == 'bilingual':
        return f"{effective.l1},{effective.l2}"
    else:  # smart
        return f"{effective.l1}+{effective.l2}"


def _proficiency(effective: EffectiveSettings) -> str:
    """CEFR proficiency from the policy. Immersion does not imply a level."""
    value = getattr(effective, "proficiency", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "A2"


# Alternative system prompts for different contexts
CONCISE_SYSTEM_TEMPLATE = """You are a language learning assistant. Analyze the journal entry and provide feedback as JSON.

{explanation_instruction}

Return JSON with: corrected, rewrite, score (0-100), tone, translation, explanation, rubric (grammar/vocabulary/complexity 0-100), grammar_suggestions array, new_words array.

Be encouraging and focus on learning."""


ACADEMIC_SYSTEM_TEMPLATE = """You are an advanced language learning AI specializing in academic writing analysis. Provide detailed linguistic analysis of the journal entry.

**Language Settings:**
{explanation_instruction}

**Analysis Focus:**
- Grammatical accuracy and syntactic complexity
- Lexical sophistication and semantic precision  
- Discourse coherence and pragmatic appropriateness
- Stylistic refinement and register consistency

Return comprehensive JSON analysis with the standard fields, emphasizing academic rigor in explanations."""


def build_messages_for_context(
    entry_text: str, 
    effective: EffectiveSettings, 
    context: str = "standard"
) -> Tuple[str, Dict[str, Any]]:
    """
    Build messages with different system prompts based on context.
    
    Args:
        entry_text: Journal entry to analyze
        effective: Language settings
        context: "standard", "concise", or "academic"
        
    Returns:
        Tuple of (system_prompt, user_payload)
    """
    templates = {
        "standard": SYSTEM_TEMPLATE,
        "concise": CONCISE_SYSTEM_TEMPLATE,
        "academic": ACADEMIC_SYSTEM_TEMPLATE
    }
    
    template = templates.get(context, SYSTEM_TEMPLATE)
    explanation_instr = explanation_instruction(effective)
    
    system_prompt = template.format(explanation_instruction=explanation_instr)
    
    user_payload = {
        "entry_text": entry_text,
        "target_language": effective.l2,
        "context": context,
        "settings": {
            "explanation_mode": effective.explanation_mode,
            "translation_policy": effective.translation_policy,
            "strictness": effective.strictness,
            "formality": effective.formality
        }
    }
    
    return system_prompt, user_payload


# Utility functions for testing and debugging
def preview_prompt(entry_text: str, effective: EffectiveSettings) -> str:
    """
    Generate a preview of the complete prompt for debugging.
    
    Args:
        entry_text: Journal entry text
        effective: Language settings
        
    Returns:
        Complete prompt text for preview
    """
    system_prompt, user_payload = build_messages(entry_text, effective)
    
    preview = f"""=== SYSTEM PROMPT ===
{system_prompt}

=== USER MESSAGE ===
{build_user_message(entry_text, effective)}

=== PAYLOAD METADATA ===
{json.dumps(user_payload, indent=2)}
"""
    
    return preview


def count_tokens_estimate(entry_text: str, effective: EffectiveSettings) -> int:
    """
    Rough estimate of token count for cost estimation.
    
    Args:
        entry_text: Journal entry text
        effective: Language settings
        
    Returns:
        Estimated token count (very rough approximation)
    """
    system_prompt, _ = build_messages(entry_text, effective)
    user_message = build_user_message(entry_text, effective)
    
    # Very rough estimate: ~4 characters per token
    total_chars = len(system_prompt) + len(user_message)
    estimated_tokens = total_chars // 4
    
    return estimated_tokens

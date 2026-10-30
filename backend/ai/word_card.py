"""Policy-aware Gemini vocabulary cards."""

from __future__ import annotations

import os
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from ai.gemini import generate_structured
from learning_policy import LANG_NAMES, LearningPolicy

GEMINI_MODEL_WORD_CARD = os.getenv(
    "GEMINI_MODEL_WORD_CARD",
    "gemini-3.5-flash-lite",
)


class OtherSense(BaseModel):
    """Another common sense of the saved lemma."""

    meaning: str = Field(description="Short meaning, in the definition language")
    example: str = Field(description="Short target-language example of this other sense")


class WordCard(BaseModel):
    """The structured card returned by Gemini Flash-Lite."""

    model_config = ConfigDict(populate_by_name=True)

    lemma: str = Field(
        description="Dictionary form: infinitive, masculine singular, or the full fixed phrase"
    )
    surface: str = Field(description="The form exactly as it appears in the sentence")
    is_phrase: bool
    part_of_speech: str
    gender: str = Field(description="m/f for nouns, otherwise empty")
    sense_in_context: str = Field(
        description="What the word means in this sentence, in the definition language"
    )
    gloss_l1: str = Field(
        description="A 1-4 word native-language gloss, empty when the policy forbids L1"
    )
    other_senses: List[OtherSense] = Field(
        description="Zero to two other common senses, never rare invented senses"
    )
    usage_register: str = Field(
        alias="register",
        serialization_alias="register",
        description="neutral / informal / formal / literary / regional",
    )
    cefr: str = Field(description="Estimated CEFR level of this sense: A1-C2")
    frequency_band: str = Field(description="top1k / top3k / top5k / top10k / rare")
    examples: List[str] = Field(
        description="Exactly two new target-language examples at the learner's proficiency"
    )
    example_translations: List[str] = Field(
        description="Native-language translations, parallel to examples. Empty when the policy forbids L1."
    )
    collocations: List[str] = Field(description="Three common collocations or patterns")
    word_family: List[str] = Field(description="Up to three related words with the same root")
    common_mistake: str = Field(
        description="One typical learner mistake, in the policy's explanation language"
    )
    memory_hook: str = Field(
        description="A short mnemonic, in the policy's explanation language"
    )


def _language_name(code: str) -> str:
    base = (code or "").split("-")[0].lower()
    return LANG_NAMES.get(base, code)


def _language_rule(policy: LearningPolicy) -> str:
    l1 = _language_name(policy.l1)
    l2 = _language_name(policy.l2)
    rules = {
        "l1": (
            f"Write sense_in_context, other_senses meanings, common_mistake, and memory_hook "
            f"in simple {l1}. gloss_l1 must be a short {l1} gloss. example_translations must "
            f"translate each example into {l1}."
        ),
        "l1_plus_l2": (
            f"Write the card explanations in simple {l1}, while naturally retaining the {l2} "
            f"term where useful. gloss_l1 must be a short {l1} gloss. example_translations must "
            f"translate each example into {l1}."
        ),
        "l2_plus_l1": (
            f"Write sense_in_context and other_senses meanings first in clear learner's-dictionary "
            f"{l2}. Write common_mistake and memory_hook in accessible {l2}. gloss_l1 must be a "
            f"short {l1} gloss for an optional reveal. example_translations must translate each "
            f"example into {l1} for an optional reveal."
        ),
        "l2": (
            f"Write everything in clear learner's-dictionary {l2}, with no {l1}. gloss_l1 must "
            "be an empty string. example_translations must be an empty array."
        ),
    }
    return rules[policy.vocab_def]


def build_word_card_prompts(
    term: str,
    source_sentence: str,
    policy: LearningPolicy,
) -> tuple[str, str]:
    """Build the emitted prompt contract from a resolved LearningPolicy."""
    system_prompt = (
        "You write one vocabulary card for a language learner who saved a word from a sentence "
        "they read or wrote. Explain the sense used in that sentence first. Be accurate; never "
        "invent rare senses. Return all arrays, using an empty array when nothing applies. "
        f"The learner's proficiency is {policy.proficiency}. {_language_rule(policy)}"
    )
    user_prompt = (
        f"Target language: {_language_name(policy.l2)}\n"
        f"Saved word: {term}\n"
        f"Sentence: {source_sentence or term}"
    )
    return system_prompt, user_prompt


async def generate_word_card(
    term: str,
    source_sentence: str,
    policy: LearningPolicy,
) -> WordCard:
    """Generate one structured Flash-Lite card for a saved word in context."""
    system_prompt, user_prompt = build_word_card_prompts(term, source_sentence, policy)
    return await generate_structured(
        system_prompt,
        user_prompt,
        WordCard,
        timeout=30.0,
        model=GEMINI_MODEL_WORD_CARD,
        use_thinking=False,
    )


def card_policy_snapshot(policy: LearningPolicy) -> dict:
    """Store the policy fields needed to render the card without re-resolving a level."""
    return {
        "v": policy.v,
        "level": policy.immersion_level,
        "l1": policy.l1,
        "l2": policy.l2,
        "proficiency": policy.proficiency,
        "vocab_def": policy.vocab_def,
        "model": GEMINI_MODEL_WORD_CARD,
    }


__all__ = [
    "GEMINI_MODEL_WORD_CARD",
    "OtherSense",
    "WordCard",
    "build_word_card_prompts",
    "card_policy_snapshot",
    "generate_word_card",
]

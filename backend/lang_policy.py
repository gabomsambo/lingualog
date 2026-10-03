"""
Language Policy Resolver

This module handles the resolution of effective language settings for journal entry processing.
It combines user profile settings with request-specific overrides to determine the final
language preferences for AI analysis.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import logging

from learning_policy import (
    IMMERSION_MAP,
    resolve_policy,
)

logger = logging.getLogger(__name__)


@dataclass
class EffectiveSettings:
    """
    Effective language settings resolved from user profile and request overrides.
    
    This dataclass represents the final language configuration that will be used
    for processing a journal entry, including AI prompting and feedback generation.
    """
    l1: str  # Native language (L1)
    l2: str  # Target language (L2) - language being learned
    explanation_mode: str  # How to present explanations
    translation_policy: str  # When/how to provide translations
    strictness: str  # Correction strictness level
    formality: str  # Formality level for corrections
    immersion_level: int  # Immersion level 0-3
    ui_language: str  # Interface language for this request
    # Filled by resolve_effective from LearningPolicy. Empty explanation keeps the
    # legacy instruction text for callers that build EffectiveSettings by hand.
    proficiency: str = "A2"
    explanation: str = ""
    meaning: str = ""
    rewrite_gloss: str = ""
    vocab_def: str = ""
    quiz: str = ""
    v: int = 1
    explanation_source: str = ""
    immersion_source: str = ""

# Default settings fallback
DEFAULT_SETTINGS = {
    'interface_lang': 'en',
    'native_lang': 'en',
    'default_target_lang': 'es',
    'explanation_mode': 'bilingual',
    'immersion_level': 1,
    'strictness': 'medium',
    'formality': 'neutral'
}


def resolve_effective(
    profile: Optional[Dict[str, Any]] = None, 
    overrides: Optional[Dict[str, Any]] = None
) -> EffectiveSettings:
    """
    Resolve effective language settings by combining profile and overrides.
    
    Priority order: overrides > profile > defaults
    
    Args:
        profile: User profile settings from database (user_settings table)
        overrides: Request-specific overrides (from API request)
        
    Returns:
        EffectiveSettings with resolved values
        
    Example:
        profile = {
            'native_lang': 'en',
            'default_target_lang': 'es', 
            'interface_lang': 'en',
            'explanation_mode': 'bilingual',
            'immersion_level': 2,
            'strictness': 'medium',
            'formality': 'neutral'
        }
        
        overrides = {
            'target_language': 'fr',  # Learning French for this entry
            'strictness': 'strict'    # Want stricter corrections
        }
        
        effective = resolve_effective(profile, overrides)
        # effective.l2 == 'fr', effective.strictness == 'strict'
    """
    # The profile dict is the caller's already-loaded settings. Pass it through
    # so a missing explanation_mode key stays "not explicit" (the level decides).
    # language_profile=None skips the database; per-language rows are loaded by
    # resolve_policy when the server calls it directly.
    requested_l2 = None
    if overrides:
        requested_l2 = overrides.get("target_language") or overrides.get("language")
    policy = resolve_policy(
        None,
        requested_l2,
        overrides,
        settings=profile,
        language_profile=None,
    )
    effective = EffectiveSettings(
        l1=policy.l1,
        l2=policy.l2,
        explanation_mode=policy.explanation_mode,
        translation_policy=policy.translation_policy,
        strictness=policy.strictness,
        formality=policy.formality,
        immersion_level=policy.immersion_level,
        ui_language=policy.ui_language,
        proficiency=policy.proficiency,
        explanation=policy.explanation,
        meaning=policy.meaning,
        rewrite_gloss=policy.rewrite_gloss,
        vocab_def=policy.vocab_def,
        quiz=policy.quiz,
        v=policy.v,
        explanation_source=policy.explanation_source,
        immersion_source=policy.immersion_source,
    )
    logger.info(
        "Resolved effective settings via LearningPolicy: L1=%s L2=%s explanation=%s "
        "translation=%s strictness=%s immersion=%s source=%s",
        effective.l1,
        effective.l2,
        effective.explanation_mode,
        effective.translation_policy,
        effective.strictness,
        effective.immersion_level,
        effective.explanation_source,
    )
    return effective


def explanation_instruction(effective: EffectiveSettings) -> str:
    """
    Generate explanation instruction text for AI prompts based on effective settings.
    
    Args:
        effective: Resolved effective settings
        
    Returns:
        Instruction text to include in AI prompts
        
    Example:
        effective = EffectiveSettings(l1='en', l2='es', explanation_mode='bilingual', ...)
        instruction = explanation_instruction(effective)
        # Returns: "Provide explanations in both English and Spanish. Be helpful and encouraging."
    """
    # Language code to name mapping
    lang_names = {
        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'it': 'Italian',
        'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese',
        'ar': 'Arabic', 'hi': 'Hindi', 'th': 'Thai', 'vi': 'Vietnamese', 'nl': 'Dutch',
        'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'pl': 'Polish'
    }
    
    # A resolved LearningPolicy carries the explanation flag. That path is the
    # only level-to-behaviour wording. Hand-built settings keep the legacy text.
    if getattr(effective, "explanation", ""):
        from learning_policy import feedback_prompt_rules
        return feedback_prompt_rules(effective)

    # Get language names, fallback to codes if not found
    l1_name = lang_names.get(effective.l1, effective.l1)
    l2_name = lang_names.get(effective.l2, effective.l2)
    
    # Base instruction components
    explanations = {
        'native_only': f"Provide all explanations in {l1_name} only.",
        'target_only': f"Provide all explanations in {l2_name} only.",
        'bilingual': f"Provide explanations in both {l1_name} and {l2_name}.",
        'smart': f"Provide explanations primarily in {l1_name}, with key terms in {l2_name}."
    }
    
    strictness_instructions = {
        'gentle': "Be encouraging and focus on positive reinforcement. Only point out major errors.",
        'medium': "Provide balanced feedback with both corrections and encouragement.",
        'strict': "Be thorough in corrections and point out all errors, including minor ones.",
        'pedantic': "Provide extremely detailed corrections including style and advanced grammar rules."
    }
    
    formality_instructions = {
        'casual': "Use a friendly, conversational tone.",
        'neutral': "Use a professional but approachable tone.",
        'formal': "Use a formal, academic tone.",
        'academic': "Use scholarly language appropriate for academic writing."
    }
    
    # Build instruction
    instruction_parts = [
        explanations.get(effective.explanation_mode, explanations['bilingual']),
        strictness_instructions.get(effective.strictness, strictness_instructions['medium']),
        formality_instructions.get(effective.formality, formality_instructions['neutral'])
    ]

    # Add immersion context
    if effective.immersion_level <= 1:
        instruction_parts.append("The learner is a beginner, so be extra clear and supportive.")
    elif effective.immersion_level >= 3:
        instruction_parts.append("The learner is advanced, so you can use more sophisticated language.")
    
    instruction = " ".join(instruction_parts)
    
    logger.debug(f"Generated explanation instruction: {instruction}")
    
    return instruction


def get_explanation_language(effective: EffectiveSettings) -> str:
    """
    Determine the primary language for explanations based on effective settings.
    
    Args:
        effective: Resolved effective settings
        
    Returns:
        Language code for explanations (l1, l2, or 'mixed')
    """
    if effective.explanation_mode == 'native_only':
        return effective.l1
    elif effective.explanation_mode == 'target_only':
        return effective.l2
    else:  # bilingual or smart
        return 'mixed'


def should_include_translation(effective: EffectiveSettings) -> bool:
    """
    Determine if translations should be included based on effective settings.
    
    Args:
        effective: Resolved effective settings
        
    Returns:
        True if translations should be included
    """
    return effective.translation_policy in ['automatic', 'L2_to_L1', 'smart']


# Validation functions
def validate_language_code(lang_code: str) -> bool:
    """Validate that a language code follows expected format (e.g., 'en', 'es-MX')."""
    if not lang_code:
        return False
    
    # Basic validation - 2-letter code, optionally followed by country code
    import re
    return bool(re.match(r'^[a-z]{2}(-[A-Z]{2})?$', lang_code))


def validate_effective_settings(effective: EffectiveSettings) -> bool:
    """
    Validate that effective settings are consistent and valid.
    
    Args:
        effective: Settings to validate
        
    Returns:
        True if settings are valid
        
    Raises:
        ValueError: If settings are invalid
    """
    # Validate language codes
    if not validate_language_code(effective.l1):
        raise ValueError(f"Invalid L1 language code: {effective.l1}")
    
    if not validate_language_code(effective.l2):
        raise ValueError(f"Invalid L2 language code: {effective.l2}")
    
    if not validate_language_code(effective.ui_language):
        raise ValueError(f"Invalid UI language code: {effective.ui_language}")
    
    # Validate enum values
    valid_explanation_modes = {'native_only', 'target_only', 'bilingual', 'smart'}
    if effective.explanation_mode not in valid_explanation_modes:
        raise ValueError(f"Invalid explanation_mode: {effective.explanation_mode}")
    
    valid_strictness = {'gentle', 'medium', 'strict', 'pedantic'}
    if effective.strictness not in valid_strictness:
        raise ValueError(f"Invalid strictness: {effective.strictness}")
    
    valid_formality = {'casual', 'neutral', 'formal', 'academic'}
    if effective.formality not in valid_formality:
        raise ValueError(f"Invalid formality: {effective.formality}")
    
    valid_translation_policies = {'none', 'on_demand', 'automatic', 'smart', 'L2_to_L1', 'omit'}
    if effective.translation_policy not in valid_translation_policies:
        raise ValueError(f"Invalid translation_policy: {effective.translation_policy}")
    
    # Validate immersion level
    if not (0 <= effective.immersion_level <= 3):
        raise ValueError(f"Invalid immersion_level: {effective.immersion_level} (must be 0-3)")
    
    return True

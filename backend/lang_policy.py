"""
Language Policy Resolver

This module handles the resolution of effective language settings for journal entry processing.
It combines user profile settings with request-specific overrides to determine the final
language preferences for AI analysis.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import logging

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


# Immersion level mapping (0-3)
# Format: level -> (explanation_language, translation_policy)
# Matches plan specification from MULTI_LINGUAL_PROBLEM.md
IMMERSION_MAP = {
    0: ('native', 'L2_to_L1'),     # Level 0: Native-First - Maximum L1 support, always show translations
    1: ('native', 'on_demand'),    # Level 1: Guided Bilingual - L1 explanations, translations on-demand
    2: ('bilingual', 'on_demand'), # Level 2: Balanced Immersion - Bilingual explanations, translations on-demand
    3: ('target', 'omit'),         # Level 3: Full Immersion - L2 only, no translations
}

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
    # Start with defaults
    settings = DEFAULT_SETTINGS.copy()
    
    # Apply profile settings if available
    if profile:
        settings.update({
            'interface_lang': profile.get('interface_lang', settings['interface_lang']),
            'native_lang': profile.get('native_lang', settings['native_lang']),
            'default_target_lang': profile.get('default_target_lang', settings['default_target_lang']),
            'explanation_mode': profile.get('explanation_mode', settings['explanation_mode']),
            'immersion_level': profile.get('immersion_level', settings['immersion_level']),
            'strictness': profile.get('strictness', settings['strictness']),
            'formality': profile.get('formality', settings['formality'])
        })
    
    # Apply request overrides if available
    if overrides:
        # Map common request field names to settings keys
        override_mapping = {
            'target_language': 'default_target_lang',
            'language': 'default_target_lang',  # Alternative field name
            'ui_language': 'interface_lang',
            'explanation_mode': 'explanation_mode',
            'strictness': 'strictness',
            'formality': 'formality',
            'immersion_level': 'immersion_level'
        }
        
        for override_key, value in overrides.items():
            if override_key in override_mapping and value is not None:
                settings_key = override_mapping[override_key]
                settings[settings_key] = value
            elif override_key in settings and value is not None:
                settings[override_key] = value
    
    # Determine translation policy based on immersion level
    immersion_level = settings['immersion_level']
    explanation_lang, translation_policy = IMMERSION_MAP.get(
        immersion_level, 
        IMMERSION_MAP[1]  # Default to level 1 if invalid
    )
    
    # Override explanation mode based on immersion if not explicitly set
    if not overrides or 'explanation_mode' not in overrides:
        if explanation_lang == 'native':
            settings['explanation_mode'] = 'native_only'
        elif explanation_lang == 'target':
            settings['explanation_mode'] = 'target_only'
        elif explanation_lang == 'bilingual':
            settings['explanation_mode'] = 'bilingual'
    
    # Create effective settings
    effective = EffectiveSettings(
        l1=settings['native_lang'],
        l2=settings['default_target_lang'],
        explanation_mode=settings['explanation_mode'],
        translation_policy=translation_policy,
        strictness=settings['strictness'],
        formality=settings['formality'],
        immersion_level=immersion_level,
        ui_language=settings['interface_lang']
    )
    
    logger.info(f"Resolved effective settings: L1={effective.l1}, L2={effective.l2}, "
               f"explanation={effective.explanation_mode}, translation={effective.translation_policy}, "
               f"strictness={effective.strictness}, immersion={effective.immersion_level}")
    
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
    
    translation_instructions = {
        'none': "Do not provide any translations.",
        'on_demand': "Only provide translations when specifically helpful for understanding.",
        'automatic': "Always provide translations for the corrected and rewritten versions.",
        'smart': "Provide translations strategically to enhance learning.",
        'omit': "Do not provide any translations.",
        'L2_to_L1': f"Always provide translations from {l2_name} to {l1_name}."
    }
    
    # Build instruction
    instruction_parts = [
        explanations.get(effective.explanation_mode, explanations['bilingual']),
        strictness_instructions.get(effective.strictness, strictness_instructions['medium']),
        formality_instructions.get(effective.formality, formality_instructions['neutral'])
    ]
    
    # Add translation instruction
    translation_part = translation_instructions.get(
        effective.translation_policy, 
        translation_instructions['on_demand']
    )
    instruction_parts.append(translation_part)
    
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
    
    valid_translation_policies = {'none', 'on_demand', 'automatic', 'smart', 'L2_to_L1'}
    if effective.translation_policy not in valid_translation_policies:
        raise ValueError(f"Invalid translation_policy: {effective.translation_policy}")
    
    # Validate immersion level
    if not (0 <= effective.immersion_level <= 3):
        raise ValueError(f"Invalid immersion_level: {effective.immersion_level} (must be 0-3)")
    
    return True

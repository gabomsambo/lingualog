"""
Unit tests for language policy resolution.

Tests the lang_policy module functionality including immersion mapping,
settings resolution, and override precedence.
"""

import pytest
from lang_policy import (
    EffectiveSettings,
    resolve_effective,
    explanation_instruction,
    IMMERSION_MAP,
    validate_effective_settings,
    get_explanation_language,
    should_include_translation
)


class TestImmersionMapping:
    """Test immersion level mapping to explanation language and translation policy."""
    
    def test_immersion_level_0_mapping(self):
        """Test that immersion level 0 maps to maximum native language support."""
        profile = {
            'native_lang': 'en',
            'default_target_lang': 'es',
            'immersion_level': 0
        }
        
        effective = resolve_effective(profile)
        
        assert effective.immersion_level == 0
        # Level 0 should use native explanations and L2_to_L1 translation
        expected_explanation, expected_translation = IMMERSION_MAP[0]
        assert expected_explanation == 'native'
        assert expected_translation == 'L2_to_L1'
        assert effective.translation_policy == 'L2_to_L1'
        # Should override to native_only explanation mode
        assert effective.explanation_mode == 'native_only'
    
    def test_immersion_level_3_mapping(self):
        """Test that immersion level 3 maps to target language only."""
        profile = {
            'native_lang': 'en',
            'default_target_lang': 'fr',
            'immersion_level': 3
        }
        
        effective = resolve_effective(profile)
        
        assert effective.immersion_level == 3
        # Level 3 should use target language and omit translations
        expected_explanation, expected_translation = IMMERSION_MAP[3]
        assert expected_explanation == 'target'
        assert expected_translation == 'omit'
        assert effective.translation_policy == 'omit'
        assert effective.explanation_mode == 'target_only'
    
    def test_immersion_map_level_3_direct_validation(self):
        """Direct test that IMMERSION_MAP[3] returns the expected values."""
        explanation_lang, translation_policy = IMMERSION_MAP[3]
        assert translation_policy == 'omit'
        assert explanation_lang == 'target'  # This maps to 'target_only' in resolve_effective
        
        # Also test that these are applied correctly in resolve_effective
        profile = {
            'immersion_level': 3,
            'native_lang': 'en',
            'default_target_lang': 'es'
        }
        effective = resolve_effective(profile, {})
        
        assert effective.translation_policy == 'omit'
        assert effective.explanation_mode == 'target_only'
        assert effective.immersion_level == 3
    
    def test_immersion_level_2_bilingual(self):
        """Test that immersion level 2 uses bilingual explanations."""
        profile = {
            'native_lang': 'ja',
            'default_target_lang': 'en',
            'immersion_level': 2
        }
        
        effective = resolve_effective(profile)
        
        assert effective.immersion_level == 2
        expected_explanation, expected_translation = IMMERSION_MAP[2]
        assert expected_explanation == 'bilingual'
        assert expected_translation == 'on_demand'
        assert effective.translation_policy == 'on_demand'
        assert effective.explanation_mode == 'bilingual'


class TestOverridesPrecedence:
    """Test that overrides take precedence over profile settings and defaults."""
    
    def test_overrides_beat_profile(self):
        """Test that request overrides take precedence over profile settings."""
        profile = {
            'native_lang': 'en',
            'default_target_lang': 'es',
            'interface_lang': 'en',
            'explanation_mode': 'bilingual',
            'strictness': 'medium',
            'formality': 'neutral',
            'immersion_level': 1
        }
        
        overrides = {
            'target_language': 'fr',  # Override Spanish with French
            'strictness': 'strict',   # Override medium with strict
            'immersion_level': 3      # Override level 1 with level 3
        }
        
        effective = resolve_effective(profile, overrides)
        
        # Overrides should win
        assert effective.l2 == 'fr'  # French, not Spanish
        assert effective.strictness == 'strict'  # Strict, not medium
        assert effective.immersion_level == 3  # Level 3, not 1
        
        # Non-overridden profile values should remain
        assert effective.l1 == 'en'
        assert effective.formality == 'neutral'
    
    def test_profile_beats_defaults(self):
        """Test that profile settings take precedence over defaults."""
        profile = {
            'native_lang': 'ja',
            'default_target_lang': 'ko',
            'interface_lang': 'ja',
            'explanation_mode': 'smart',
            'strictness': 'gentle',
            'formality': 'casual',
            'immersion_level': 3
        }

        effective = resolve_effective(profile, None)

        # Profile values should override defaults
        assert effective.l1 == 'ja'  # Not default 'en'
        assert effective.l2 == 'ko'  # Not default 'es'
        assert effective.ui_language == 'ja'  # Not default 'en'
        assert effective.strictness == 'gentle'  # Not default 'medium'
        assert effective.formality == 'casual'  # Not default 'neutral'
        assert effective.immersion_level == 3  # Not default 1
    
    def test_defaults_when_no_profile(self):
        """Test that defaults are used when no profile is provided."""
        effective = resolve_effective(None, None)
        
        # Should use all defaults
        assert effective.l1 == 'en'
        assert effective.l2 == 'es'
        assert effective.ui_language == 'en'
        assert effective.explanation_mode == 'smart'  # Level 1 names grammar in L2
        assert effective.strictness == 'medium'
        assert effective.formality == 'neutral'
        assert effective.immersion_level == 1
    
    def test_complex_precedence_chain(self):
        """Test complex precedence with all three sources: overrides > profile > defaults."""
        profile = {
            'native_lang': 'zh',        # Override default 'en'
            'default_target_lang': 'ja', # Override default 'es'
            'strictness': 'strict',     # Override default 'medium'
            # Missing: formality (should use default 'neutral')
        }
        
        overrides = {
            'target_language': 'ko',    # Override profile 'ja'
            'formality': 'formal',      # Override default 'neutral'
            # Missing: strictness (should use profile 'strict')
        }
        
        effective = resolve_effective(profile, overrides)
        
        # Overrides win over profile
        assert effective.l2 == 'ko'  # Override wins
        assert effective.formality == 'formal'  # Override wins
        
        # Profile wins over defaults
        assert effective.l1 == 'zh'  # Profile wins
        assert effective.strictness == 'strict'  # Profile wins
        
        # Defaults used when missing from both
        assert effective.immersion_level == 1  # Default


class TestExplanationInstructions:
    """Test explanation instruction generation."""
    
    def test_bilingual_explanation_instruction(self):
        """Test bilingual explanation instruction."""
        effective = EffectiveSettings(
            l1='en', l2='es', explanation_mode='bilingual',
            translation_policy='on_demand', strictness='medium',
            formality='neutral', immersion_level=2, ui_language='en'
        )
        
        instruction = explanation_instruction(effective)
        
        assert 'both English and Spanish' in instruction
        assert 'balanced feedback' in instruction
        assert 'professional but approachable' in instruction
    
    def test_target_only_explanation_instruction(self):
        """Test target language only explanation instruction."""
        effective = EffectiveSettings(
            l1='en', l2='fr', explanation_mode='target_only',
            translation_policy='omit', strictness='strict',
            formality='formal', immersion_level=3, ui_language='en'
        )

        instruction = explanation_instruction(effective)

        assert 'French only' in instruction
        assert 'thorough in corrections' in instruction
        assert 'formal, academic tone' in instruction
        assert 'advanced' in instruction  # High immersion level
    
    def test_gentle_beginner_instruction(self):
        """Test gentle instruction for beginners."""
        effective = EffectiveSettings(
            l1='en', l2='es', explanation_mode='native_only',
            translation_policy='L2_to_L1', strictness='gentle',
            formality='casual', immersion_level=0, ui_language='en'
        )
        
        instruction = explanation_instruction(effective)
        
        assert 'English only' in instruction
        assert 'encouraging' in instruction
        assert 'major errors' in instruction  # Gentle strictness
        assert 'friendly, conversational' in instruction
        assert 'beginner' in instruction


class TestValidation:
    """Test validation functions."""
    
    def test_valid_effective_settings(self):
        """Test validation of valid settings."""
        effective = EffectiveSettings(
            l1='en', l2='es', explanation_mode='bilingual',
            translation_policy='on_demand', strictness='medium',
            formality='neutral', immersion_level=2, ui_language='en'
        )
        
        assert validate_effective_settings(effective) is True
    
    def test_invalid_language_codes(self):
        """Test validation fails for invalid language codes."""
        with pytest.raises(ValueError, match="Invalid L1 language code"):
            effective = EffectiveSettings(
                l1='english', l2='es', explanation_mode='bilingual',
                translation_policy='on_demand', strictness='medium',
                formality='neutral', immersion_level=2, ui_language='en'
            )
            validate_effective_settings(effective)
    
    def test_invalid_immersion_level(self):
        """Test validation fails for invalid immersion level."""
        with pytest.raises(ValueError, match="Invalid immersion_level"):
            effective = EffectiveSettings(
                l1='en', l2='es', explanation_mode='bilingual',
                translation_policy='on_demand', strictness='medium',
                formality='neutral', immersion_level=10, ui_language='en'
            )
            validate_effective_settings(effective)
    
    def test_invalid_explanation_mode(self):
        """Test validation fails for invalid explanation mode."""
        with pytest.raises(ValueError, match="Invalid explanation_mode"):
            effective = EffectiveSettings(
                l1='en', l2='es', explanation_mode='invalid_mode',
                translation_policy='on_demand', strictness='medium',
                formality='neutral', immersion_level=2, ui_language='en'
            )
            validate_effective_settings(effective)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_explanation_language(self):
        """Test explanation language detection."""
        # Native only
        effective = EffectiveSettings(
            l1='en', l2='es', explanation_mode='native_only',
            translation_policy='on_demand', strictness='medium',
            formality='neutral', immersion_level=1, ui_language='en'
        )
        assert get_explanation_language(effective) == 'en'
        
        # Target only
        effective.explanation_mode = 'target_only'
        assert get_explanation_language(effective) == 'es'
        
        # Bilingual/smart
        effective.explanation_mode = 'bilingual'
        assert get_explanation_language(effective) == 'mixed'
    
    def test_should_include_translation(self):
        """Test translation inclusion logic."""
        # Should include
        effective = EffectiveSettings(
            l1='en', l2='es', explanation_mode='bilingual',
            translation_policy='automatic', strictness='medium',
            formality='neutral', immersion_level=2, ui_language='en'
        )
        assert should_include_translation(effective) is True
        
        # Should not include
        effective.translation_policy = 'none'
        assert should_include_translation(effective) is False
        
        effective.translation_policy = 'omit'
        assert should_include_translation(effective) is False


# Integration tests
class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_realistic_beginner_scenario(self):
        """Test realistic scenario for a beginner user."""
        profile = {
            'native_lang': 'en',
            'default_target_lang': 'es',
            'interface_lang': 'en',
            'explanation_mode': 'bilingual',
            'explanation_mode_explicit': True,
            'immersion_level': 1,
            'strictness': 'gentle',
            'formality': 'casual'
        }
        
        # User wants to practice French for this entry
        overrides = {
            'target_language': 'fr'
        }
        
        effective = resolve_effective(profile, overrides)
        
        assert effective.l1 == 'en'
        assert effective.l2 == 'fr'  # Override worked
        # Saved explanation_mode is an explicit choice and beats the level.
        assert effective.explanation_mode == 'bilingual'
        assert effective.explanation_source == 'saved_explanation_mode'
        assert effective.translation_policy == 'on_demand'
        assert effective.strictness == 'gentle'
        assert effective.formality == 'casual'
        
        # Test instruction generation
        instruction = explanation_instruction(effective)
        assert 'note_l1' in instruction
        assert 'encouraging' in instruction
        assert 'friendly' in instruction
    
    def test_realistic_advanced_scenario(self):
        """Test realistic scenario for an advanced user."""
        profile = {
            'native_lang': 'ja',
            'default_target_lang': 'en',
            'interface_lang': 'ja',
            'explanation_mode': 'smart',
            'explanation_mode_explicit': True,
            'immersion_level': 3,
            'strictness': 'strict',
            'formality': 'academic'
        }

        # User wants stricter feedback for this entry
        overrides = {
            'strictness': 'pedantic'
        }

        effective = resolve_effective(profile, overrides)

        assert effective.l1 == 'ja'
        assert effective.l2 == 'en'
        # Saved "smart" is explicit, so it overrides the level-3 note language.
        assert effective.explanation_mode == 'smart'
        assert effective.explanation_source == 'saved_explanation_mode'
        assert effective.translation_policy == 'omit'
        assert effective.strictness == 'pedantic'  # Override worked
        assert effective.formality == 'academic'

        # Test instruction generation
        instruction = explanation_instruction(effective)
        assert 'Japanese' in instruction
        assert 'extremely detailed' in instruction
        assert 'scholarly' in instruction

-- Migration: Add multilingual preferences and entry snapshots
-- Created: 2025-09-15
-- Description: Adds language preference columns to user_settings and snapshot columns to journal_entries
-- This migration is idempotent and can be run multiple times safely

-- =============================================
-- Part 1: User Settings Multilingual Preferences
-- =============================================

-- Add interface language preference (defaults to existing app_language if available)
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS interface_lang text NOT NULL DEFAULT 'en';

-- Update existing rows to use their current app_language as interface_lang
-- This ensures continuity for existing users
UPDATE public.user_settings 
SET interface_lang = COALESCE(app_language, 'en')
WHERE interface_lang = 'en' AND app_language IS NOT NULL AND app_language != 'en';

-- Add native language (different from target languages - this is the user's first language)
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS native_lang text NOT NULL DEFAULT 'en';

-- Update existing rows to use their current native_language value if it exists
UPDATE public.user_settings 
SET native_lang = COALESCE(native_language, 'en')
WHERE native_lang = 'en' AND native_language IS NOT NULL AND native_language != 'en';

-- Add default target language (primary language they're learning)
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS default_target_lang text;

-- Update existing rows to use the first target language as default
UPDATE public.user_settings 
SET default_target_lang = target_languages[1]
WHERE default_target_lang IS NULL AND target_languages IS NOT NULL AND array_length(target_languages, 1) > 0;

-- Add explanation mode preference (how AI explanations are presented)
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS explanation_mode text NOT NULL DEFAULT 'bilingual'
CHECK (explanation_mode IN ('native_only', 'target_only', 'bilingual', 'smart'));

-- Add immersion level (1-5 scale, affects how much native language is used)
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS immersion_level smallint NOT NULL DEFAULT 1
CHECK (immersion_level >= 1 AND immersion_level <= 5);

-- Add correction strictness level
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS strictness text NOT NULL DEFAULT 'medium'
CHECK (strictness IN ('gentle', 'medium', 'strict', 'pedantic'));

-- Add formality preference for corrections and suggestions
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS formality text NOT NULL DEFAULT 'neutral'
CHECK (formality IN ('casual', 'neutral', 'formal', 'academic'));

-- =============================================
-- Part 2: Journal Entries Snapshot Columns
-- =============================================

-- Add target language for the specific entry
ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS target_language text NOT NULL DEFAULT 'en';

-- Update existing entries to use their current language field if available
UPDATE public.journal_entries 
SET target_language = COALESCE(language, 'en')
WHERE target_language = 'en' AND language IS NOT NULL AND language != 'en';

-- Add UI language snapshot (what interface language was used when creating)
ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS ui_language_snapshot text;

-- Add explanation language snapshot (what language explanations were given in)
ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS explanation_language_snapshot text;

-- Add translation policy snapshot (how translations were handled for this entry)
ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS translation_policy_snapshot text
CHECK (translation_policy_snapshot IS NULL OR translation_policy_snapshot IN ('none', 'on_demand', 'automatic', 'smart'));

-- Add proficiency estimate at time of entry creation
ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS proficiency_estimate text
CHECK (proficiency_estimate IS NULL OR proficiency_estimate IN ('beginner', 'elementary', 'intermediate', 'advanced', 'native'));

-- =============================================
-- Part 3: Create helpful indexes for performance
-- =============================================

-- Index for querying entries by target language
CREATE INDEX IF NOT EXISTS idx_journal_entries_target_language 
ON public.journal_entries(target_language);

-- Index for querying entries by proficiency level
CREATE INDEX IF NOT EXISTS idx_journal_entries_proficiency 
ON public.journal_entries(proficiency_estimate) 
WHERE proficiency_estimate IS NOT NULL;

-- Index for user settings language preferences
CREATE INDEX IF NOT EXISTS idx_user_settings_languages 
ON public.user_settings(interface_lang, native_lang, default_target_lang);

-- =============================================
-- Part 4: Add helpful comments for documentation
-- =============================================

COMMENT ON COLUMN public.user_settings.interface_lang IS 'Language used for the app interface (UI language)';
COMMENT ON COLUMN public.user_settings.native_lang IS 'User''s native/first language';
COMMENT ON COLUMN public.user_settings.default_target_lang IS 'Primary language the user is learning';
COMMENT ON COLUMN public.user_settings.explanation_mode IS 'How AI explanations are presented: native_only, target_only, bilingual, or smart';
COMMENT ON COLUMN public.user_settings.immersion_level IS 'Immersion level 1-5, affects how much native language is used in learning';
COMMENT ON COLUMN public.user_settings.strictness IS 'Correction strictness: gentle, medium, strict, or pedantic';
COMMENT ON COLUMN public.user_settings.formality IS 'Formality level for corrections: casual, neutral, formal, or academic';

COMMENT ON COLUMN public.journal_entries.target_language IS 'Language this entry was written in or practicing';
COMMENT ON COLUMN public.journal_entries.ui_language_snapshot IS 'UI language when this entry was created';
COMMENT ON COLUMN public.journal_entries.explanation_language_snapshot IS 'Language used for AI explanations for this entry';
COMMENT ON COLUMN public.journal_entries.translation_policy_snapshot IS 'Translation policy in effect when entry was created';
COMMENT ON COLUMN public.journal_entries.proficiency_estimate IS 'Estimated user proficiency level when entry was created';

-- =============================================
-- Part 5: Data integrity and validation
-- =============================================

-- Ensure target_language is a valid language code (basic validation)
ALTER TABLE public.journal_entries 
ADD CONSTRAINT IF NOT EXISTS chk_target_language_format 
CHECK (target_language ~ '^[a-z]{2}(-[A-Z]{2})?$');

-- Ensure interface_lang is a valid language code
ALTER TABLE public.user_settings 
ADD CONSTRAINT IF NOT EXISTS chk_interface_lang_format 
CHECK (interface_lang ~ '^[a-z]{2}(-[A-Z]{2})?$');

-- Ensure native_lang is a valid language code
ALTER TABLE public.user_settings 
ADD CONSTRAINT IF NOT EXISTS chk_native_lang_format 
CHECK (native_lang ~ '^[a-z]{2}(-[A-Z]{2})?$');

-- Ensure default_target_lang is a valid language code when not null
ALTER TABLE public.user_settings 
ADD CONSTRAINT IF NOT EXISTS chk_default_target_lang_format 
CHECK (default_target_lang IS NULL OR default_target_lang ~ '^[a-z]{2}(-[A-Z]{2})?$');

-- =============================================
-- Migration Complete
-- =============================================

-- Log migration completion (if logging table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_log') THEN
        INSERT INTO migration_log (version, name, applied_at) 
        VALUES ('002', 'multilingual_preferences', NOW());
    END IF;
END $$;

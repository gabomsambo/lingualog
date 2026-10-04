-- =============================================
-- Migration: one language model in Settings
-- Created: 2026-10-04
-- Description:
--   user_settings.native_lang is the instruction language ("explain things to me in").
--   user_language_profiles is the list of studied languages; default_target_lang marks one.
--   Removing a studied language sets active = false. The row, its level and proficiency,
--   and every entry in that language stay. Re-adding sets active = true again.
--   journal_entries.detected_language is the language Gemini read the entry as;
--   detected_language_kept records that the learner chose to keep the entry's language.
--   Legacy native_language and target_languages are copied forward where safe and
--   then left unused. They are not dropped here.
-- =============================================

BEGIN;

ALTER TABLE public.user_language_profiles
ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN public.user_language_profiles.active IS
  'False after the learner removes the language in Settings. The profile and entries are kept; re-adding restores them.';

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS detected_language text;

ALTER TABLE public.journal_entries
DROP CONSTRAINT IF EXISTS chk_detected_language_format;

ALTER TABLE public.journal_entries
ADD CONSTRAINT chk_detected_language_format
CHECK (detected_language IS NULL OR detected_language ~ '^[a-z]{2}$');

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS detected_language_kept boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.journal_entries.detected_language IS
  'ISO 639-1 code of the language the entry is written in, as read by the tutor. Null when unknown.';
COMMENT ON COLUMN public.journal_entries.detected_language_kept IS
  'True after the learner chose to keep the entry''s language despite a detected mismatch.';

-- Languages in the legacy list stay studied. The native language there may be the untouched
-- column default ({es}), not a choice, so it is only kept when it already has a profile or is
-- the default target language (inserted below). Learning one's own language is added in Settings.
INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency, active)
SELECT DISTINCT s.user_id, legacy.l2, s.immersion_level, 'A2', true
FROM public.user_settings s
CROSS JOIN LATERAL unnest(s.target_languages) AS legacy(l2)
WHERE legacy.l2 ~ '^[a-z]{2}(-[A-Z]{2})?$'
  AND split_part(legacy.l2, '-', 1) IS DISTINCT FROM split_part(s.native_lang, '-', 1)
ON CONFLICT (user_id, l2) DO NOTHING;

-- The default target language is always a studied language.
INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency, active)
SELECT user_id, default_target_lang, immersion_level, 'A2', true
FROM public.user_settings
WHERE default_target_lang IS NOT NULL
ON CONFLICT (user_id, l2) DO UPDATE SET active = true;

-- native_lang has been the visible, used field since 2025-09; native_language was only
-- re-saved unchanged. native_lang wins. Report rows that disagree instead of overwriting.
DO $$
DECLARE
  disagreeing integer;
BEGIN
  SELECT count(*) INTO disagreeing
  FROM public.user_settings
  WHERE native_language IS DISTINCT FROM native_lang;
  RAISE NOTICE 'user_settings rows where legacy native_language differs from native_lang (kept native_lang): %',
    disagreeing;
END $$;

COMMENT ON COLUMN public.user_settings.native_language IS
  'Legacy. Superseded by native_lang; no longer read or written. Safe to drop later.';
COMMENT ON COLUMN public.user_settings.target_languages IS
  'Legacy. Superseded by user_language_profiles (active rows); no longer read or written. Safe to drop later.';

CREATE OR REPLACE FUNCTION public.save_user_settings(
  p_user_id uuid,
  p_settings jsonb,
  p_profiles jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  IF p_profiles IS NOT NULL AND jsonb_array_length(p_profiles) > 0 THEN
    INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency, active)
    SELECT p_user_id, p.l2, p.immersion_level, p.proficiency, coalesce(p.active, true)
    FROM jsonb_to_recordset(p_profiles)
      AS p(l2 text, immersion_level smallint, proficiency text, active boolean)
    ON CONFLICT (user_id, l2) DO UPDATE
    SET immersion_level = excluded.immersion_level,
        proficiency = excluded.proficiency,
        active = excluded.active;
  END IF;

  IF p_settings IS NOT NULL AND p_settings <> '{}'::jsonb THEN
    UPDATE public.user_settings s
    SET (
      native_language, target_languages, email_notifications, push_notifications,
      daily_reminders, weekly_progress, reminder_time, theme, app_language,
      sound_effects, animations, difficulty_level, daily_goal, weekly_goal,
      auto_save, show_hints, public_profile, share_progress, analytics_opt_in,
      interface_lang, native_lang, default_target_lang, explanation_mode,
      explanation_mode_explicit, immersion_level, strictness, formality
    ) = (
      SELECT
        r.native_language, r.target_languages, r.email_notifications, r.push_notifications,
        r.daily_reminders, r.weekly_progress, r.reminder_time, r.theme, r.app_language,
        r.sound_effects, r.animations, r.difficulty_level, r.daily_goal, r.weekly_goal,
        r.auto_save, r.show_hints, r.public_profile, r.share_progress, r.analytics_opt_in,
        r.interface_lang, r.native_lang, r.default_target_lang, r.explanation_mode,
        r.explanation_mode_explicit, r.immersion_level, r.strictness, r.formality
      FROM jsonb_populate_record(s, p_settings) AS r
    )
    WHERE s.user_id = p_user_id;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'No settings found to update for user %', p_user_id;
    END IF;
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.save_user_settings(uuid, jsonb, jsonb) FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.save_user_settings(uuid, jsonb, jsonb) TO service_role;

COMMIT;

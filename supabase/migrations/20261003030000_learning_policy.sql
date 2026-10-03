-- =============================================
-- Migration: LearningPolicy, one profile per target language
-- Version: 006
-- Created: 2026-10-03
-- Description:
--   user_language_profiles stores immersion and proficiency per target language.
--   journal_entries.policy_snapshot stores the resolved policy (v: 1).
--   Existing *_snapshot columns stay.
--   user_settings.explanation_mode_explicit marks a learner's own explanation
--   choice; existing rows start false so the immersion level decides.
--   The proficiency case below is a one-time seed from the old immersion
--   heuristic. Runtime resolution does not derive proficiency from immersion.
-- =============================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_language_profiles (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  l2 text NOT NULL,
  immersion_level smallint NOT NULL DEFAULT 1,
  proficiency text NOT NULL DEFAULT 'A2',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT user_language_profiles_pkey PRIMARY KEY (user_id, l2),
  CONSTRAINT user_language_profiles_l2_format
    CHECK (l2 ~ '^[a-z]{2}(-[A-Z]{2})?$'),
  CONSTRAINT user_language_profiles_immersion_level_check
    CHECK (immersion_level >= 0 AND immersion_level <= 3),
  CONSTRAINT user_language_profiles_proficiency_check
    CHECK (proficiency IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2'))
);

DROP TRIGGER IF EXISTS set_user_language_profiles_updated_at ON public.user_language_profiles;
CREATE TRIGGER set_user_language_profiles_updated_at
BEFORE UPDATE ON public.user_language_profiles
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.user_language_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_language_profiles_select_own" ON public.user_language_profiles;
CREATE POLICY "user_language_profiles_select_own"
ON public.user_language_profiles FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_language_profiles_insert_own" ON public.user_language_profiles;
CREATE POLICY "user_language_profiles_insert_own"
ON public.user_language_profiles FOR INSERT
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_language_profiles_update_own" ON public.user_language_profiles;
CREATE POLICY "user_language_profiles_update_own"
ON public.user_language_profiles FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_language_profiles_delete_own" ON public.user_language_profiles;
CREATE POLICY "user_language_profiles_delete_own"
ON public.user_language_profiles FOR DELETE
USING (auth.uid() = user_id);

COMMENT ON TABLE public.user_language_profiles IS
  'Immersion level and CEFR proficiency for one target language. Proficiency is not derived from immersion.';
COMMENT ON COLUMN public.user_language_profiles.immersion_level IS
  'How much of the learner''s own language they want while practising this one. 0 native-first … 3 immersive.';
COMMENT ON COLUMN public.user_language_profiles.proficiency IS
  'Self-reported CEFR band (A1-C2) for this language. Independent of immersion_level.';

-- One-time copy of today's account-wide immersion onto the default target language.
INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency)
SELECT
  user_id,
  default_target_lang,
  immersion_level,
  CASE immersion_level
    WHEN 0 THEN 'A1'
    WHEN 1 THEN 'A2'
    WHEN 2 THEN 'B1'
    ELSE 'B2'
  END
FROM public.user_settings
WHERE default_target_lang IS NOT NULL
ON CONFLICT (user_id, l2) DO NOTHING;

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS policy_snapshot jsonb;

COMMENT ON COLUMN public.journal_entries.policy_snapshot IS
  'Resolved LearningPolicy (v: 1) at the time the entry was written. History renders from this snapshot.';

ALTER TABLE public.journal_entries
DROP CONSTRAINT IF EXISTS journal_entries_proficiency_estimate_check;

ALTER TABLE public.journal_entries
ADD CONSTRAINT journal_entries_proficiency_estimate_check
CHECK (
  proficiency_estimate IS NULL
  OR proficiency_estimate IN (
    'beginner', 'elementary', 'intermediate', 'advanced', 'native',
    'A1', 'A2', 'B1', 'B2', 'C1', 'C2'
  )
);

ALTER TABLE public.user_settings
DROP CONSTRAINT IF EXISTS user_settings_explanation_mode_check;

ALTER TABLE public.user_settings
ADD CONSTRAINT user_settings_explanation_mode_check
CHECK (explanation_mode IN ('native_only', 'target_only', 'bilingual', 'smart', 'level'));

ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS explanation_mode_explicit boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.user_settings.explanation_mode IS
  'Note-language mode. It overrides the immersion level only when explanation_mode_explicit is true.';
COMMENT ON COLUMN public.user_settings.explanation_mode_explicit IS
  'True only after the learner picks an explanation mode in Settings. The column default is not a choice.';

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, username)
  VALUES (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'username', new.raw_user_meta_data ->> 'full_name')
  )
  ON CONFLICT (id) DO UPDATE
  SET email = excluded.email;

  INSERT INTO public.user_settings (user_id, native_language, native_lang, default_target_lang, interface_lang, app_language)
  VALUES (new.id, 'en', 'en', 'es', 'en', 'en')
  ON CONFLICT (user_id) DO NOTHING;

  INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency)
  VALUES (new.id, 'es', 1, 'A2')
  ON CONFLICT (user_id, l2) DO NOTHING;

  RETURN new;
END;
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'migration_log'
    ) THEN
        INSERT INTO public.migration_log (version, name, applied_at)
        VALUES ('006', 'learning_policy', NOW())
        ON CONFLICT (version) DO NOTHING;
    END IF;
END $$;

COMMIT;

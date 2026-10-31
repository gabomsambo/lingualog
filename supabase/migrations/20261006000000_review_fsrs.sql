-- =============================================
-- Migration: Vocabulary V3 - review with FSRS
-- Created: 2026-10-31
-- Description:
--   vocab_cards holds the FSRS scheduling state of one review card. A studied
--   word has a recognition card; a production card is added once recognition
--   is stable. The columns mirror py-fsrs 6.3.2 (FSRS-6); stability_fast stays
--   NULL until FSRS-7. reps and lapses are tracked here because py-fsrs does not.
--   vocab_review_logs is the append-only raw log (the source of truth for
--   re-optimising and exporting). user_fsrs_params holds per-learner optimised
--   parameters; NULL means the library defaults.
--   user_language_profiles gains desired_retention next to daily_new_words, and
--   save_user_settings saves both. apply_card_review writes a card update and
--   its log row in one transaction.
-- =============================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.vocab_cards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  word_id uuid NOT NULL REFERENCES public.user_vocabulary(id) ON DELETE CASCADE,
  language text NOT NULL,
  card_type text NOT NULL,
  state smallint NOT NULL DEFAULT 1,
  step smallint,
  stability double precision,
  difficulty double precision,
  stability_fast double precision,
  due timestamptz NOT NULL DEFAULT now(),
  last_review timestamptz,
  first_reviewed_at timestamptz,
  reps integer NOT NULL DEFAULT 0,
  lapses integer NOT NULL DEFAULT 0,
  fsrs_version text NOT NULL DEFAULT 'fsrs-6',
  suspended_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vocab_cards_card_type_check CHECK (card_type IN ('recognition', 'production')),
  CONSTRAINT vocab_cards_state_check CHECK (state IN (1, 2, 3)),
  CONSTRAINT vocab_cards_word_type_key UNIQUE (word_id, card_type)
);

COMMENT ON TABLE public.vocab_cards IS
  'FSRS state of one review card. state follows py-fsrs: 1 Learning, 2 Review, 3 Relearning.';
COMMENT ON COLUMN public.vocab_cards.first_reviewed_at IS
  'When the card was first reviewed. Counts a recognition card against the per-language daily new-word limit.';
COMMENT ON COLUMN public.vocab_cards.suspended_at IS
  'Set while the word is known-by-tap, ignored or back in New. A suspended card is never offered.';

CREATE INDEX IF NOT EXISTS idx_vocab_cards_user_language_due
  ON public.vocab_cards (user_id, language, due)
  WHERE suspended_at IS NULL;

CREATE TABLE IF NOT EXISTS public.vocab_review_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  card_id uuid NOT NULL REFERENCES public.vocab_cards(id) ON DELETE CASCADE,
  language text NOT NULL,
  rating smallint NOT NULL,
  reviewed_at timestamptz NOT NULL DEFAULT now(),
  duration_ms integer,
  source text NOT NULL DEFAULT 'review',
  CONSTRAINT vocab_review_logs_rating_check CHECK (rating BETWEEN 1 AND 4),
  CONSTRAINT vocab_review_logs_source_check CHECK (source IN ('review', 'challenge_use', 'practice'))
);

COMMENT ON TABLE public.vocab_review_logs IS
  'Append-only raw review log. Rating is 1 Again or 3 Good; the two-button session never writes 2 or 4.';

CREATE INDEX IF NOT EXISTS idx_vocab_review_logs_user_language_time
  ON public.vocab_review_logs (user_id, language, reviewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_vocab_review_logs_card
  ON public.vocab_review_logs (card_id, reviewed_at);

CREATE TABLE IF NOT EXISTS public.user_fsrs_params (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  l2 text NOT NULL,
  parameters double precision[],
  optimized_at timestamptz,
  n_reviews integer NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, l2)
);

COMMENT ON TABLE public.user_fsrs_params IS
  'Per-learner FSRS parameters from a later optimisation. NULL parameters mean the library defaults. The learner-set desired retention lives on user_language_profiles.';

DO $$
DECLARE
  table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['vocab_cards', 'vocab_review_logs', 'user_fsrs_params'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_select_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR SELECT USING (auth.uid() = user_id)',
      table_name || '_select_own', table_name
    );
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_insert_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR INSERT WITH CHECK (auth.uid() = user_id)',
      table_name || '_insert_own', table_name
    );
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_update_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)',
      table_name || '_update_own', table_name
    );
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_delete_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR DELETE USING (auth.uid() = user_id)',
      table_name || '_delete_own', table_name
    );
  END LOOP;
END $$;

ALTER TABLE public.user_language_profiles
  ADD COLUMN IF NOT EXISTS desired_retention double precision NOT NULL DEFAULT 0.90;

ALTER TABLE public.user_language_profiles
  DROP CONSTRAINT IF EXISTS user_language_profiles_desired_retention_check,
  ADD CONSTRAINT user_language_profiles_desired_retention_check
    CHECK (desired_retention BETWEEN 0.80 AND 0.95);

COMMENT ON COLUMN public.user_language_profiles.desired_retention IS
  'FSRS target recall probability for this language. Adjustable 0.80-0.95; above 0.97 the review workload becomes overwhelming.';

-- Words already in study before review existed get their recognition card now.
INSERT INTO public.vocab_cards (user_id, word_id, language, card_type)
SELECT v.user_id, v.id, v.language, 'recognition'
FROM public.user_vocabulary v
WHERE v.status = 'learning'
ON CONFLICT (word_id, card_type) DO NOTHING;

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

    -- Review settings are only written when the payload carries them.
    UPDATE public.user_language_profiles l
    SET daily_new_words = coalesce(p.daily_new_words, l.daily_new_words),
        desired_retention = coalesce(p.desired_retention, l.desired_retention)
    FROM jsonb_to_recordset(p_profiles)
      AS p(l2 text, daily_new_words smallint, desired_retention double precision)
    WHERE l.user_id = p_user_id
      AND l.l2 = p.l2
      AND (p.daily_new_words IS NOT NULL OR p.desired_retention IS NOT NULL);
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

-- One transaction for a review: advance the card and append its log row. The card only
-- moves when it still belongs to the caller, is not suspended and has the reps the
-- scheduler saw, so a retry or a second tab cannot apply the same review twice.
-- Returns the updated card, or NULL when nothing matched.
CREATE OR REPLACE FUNCTION public.apply_card_review(
  p_user_id uuid,
  p_card_id uuid,
  p_expected_reps integer,
  p_card jsonb,
  p_log jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  updated public.vocab_cards;
BEGIN
  UPDATE public.vocab_cards c
  SET state = (p_card ->> 'state')::smallint,
      step = (p_card ->> 'step')::smallint,
      stability = (p_card ->> 'stability')::double precision,
      difficulty = (p_card ->> 'difficulty')::double precision,
      due = (p_card ->> 'due')::timestamptz,
      last_review = (p_card ->> 'last_review')::timestamptz,
      first_reviewed_at = coalesce(c.first_reviewed_at, (p_card ->> 'last_review')::timestamptz),
      reps = c.reps + 1,
      lapses = c.lapses + coalesce((p_card ->> 'lapsed')::boolean::int, 0),
      updated_at = now()
  WHERE c.id = p_card_id
    AND c.user_id = p_user_id
    AND c.suspended_at IS NULL
    AND c.reps = p_expected_reps
  RETURNING * INTO updated;

  IF updated.id IS NULL THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.vocab_review_logs (user_id, card_id, language, rating, reviewed_at, duration_ms, source)
  VALUES (
    p_user_id,
    p_card_id,
    updated.language,
    (p_log ->> 'rating')::smallint,
    (p_log ->> 'reviewed_at')::timestamptz,
    (p_log ->> 'duration_ms')::integer,
    coalesce(p_log ->> 'source', 'review')
  );

  RETURN to_jsonb(updated);
END;
$$;

REVOKE ALL ON FUNCTION public.apply_card_review(uuid, uuid, integer, jsonb, jsonb) FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.apply_card_review(uuid, uuid, integer, jsonb, jsonb) TO service_role;

COMMIT;

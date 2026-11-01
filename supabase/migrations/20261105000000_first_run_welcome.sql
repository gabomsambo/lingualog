BEGIN;

ALTER TABLE public.user_language_profiles
  ADD COLUMN IF NOT EXISTS onboarded_at timestamptz,
  ADD COLUMN IF NOT EXISTS goal text;

ALTER TABLE public.user_language_profiles
  DROP CONSTRAINT IF EXISTS user_language_profiles_goal_check,
  ADD CONSTRAINT user_language_profiles_goal_check
    CHECK (goal IS NULL OR goal IN ('class', 'exam', 'trip', 'work', 'just_for_me'));

COMMENT ON COLUMN public.user_language_profiles.onboarded_at IS
  'When the learner completed their first successful entry. Existing profiles are backfilled.';
COMMENT ON COLUMN public.user_language_profiles.goal IS
  'Optional first-run reason for learning this language: class, exam, trip, work, or just_for_me.';

UPDATE public.user_language_profiles
SET onboarded_at = now()
WHERE onboarded_at IS NULL;

-- New accounts get an un-onboarded default-language profile. Existing accounts and
-- their backfilled timestamps are left alone.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, username)
  VALUES (
    NEW.id,
    coalesce(NEW.email, ''),
    coalesce(NEW.raw_user_meta_data ->> 'username', NEW.raw_user_meta_data ->> 'full_name')
  )
  ON CONFLICT (id) DO UPDATE SET email = excluded.email;

  INSERT INTO public.user_settings (
    user_id, native_language, native_lang, default_target_lang, interface_lang, app_language
  )
  VALUES (NEW.id, 'en', 'en', 'es', 'en', 'en')
  ON CONFLICT (user_id) DO NOTHING;

  INSERT INTO public.user_language_profiles (user_id, l2, immersion_level, proficiency)
  SELECT user_id, default_target_lang, 0, 'A1'
  FROM public.user_settings
  WHERE user_id = NEW.id AND default_target_lang IS NOT NULL
  ON CONFLICT (user_id, l2) DO NOTHING;

  RETURN NEW;
END;
$$;

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
    INSERT INTO public.user_language_profiles (
      user_id, l2, immersion_level, proficiency, active, goal
    )
    SELECT
      p_user_id, p.l2, p.immersion_level, p.proficiency, coalesce(p.active, true), p.goal
    FROM jsonb_to_recordset(p_profiles) AS p(
      l2 text,
      immersion_level smallint,
      proficiency text,
      active boolean,
      goal text
    )
    ON CONFLICT (user_id, l2) DO UPDATE
    SET immersion_level = excluded.immersion_level,
        proficiency = excluded.proficiency,
        active = excluded.active,
        goal = coalesce(excluded.goal, user_language_profiles.goal);

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

COMMIT;

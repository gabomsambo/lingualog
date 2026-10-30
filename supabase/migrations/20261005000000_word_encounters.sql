-- =============================================
-- Migration: Vocabulary V2 - encounters, daily new-word cap
-- Created: 2026-10-30
-- Description:
--   word_encounters logs every place a learner meets a word (lookups now,
--   reading marks and entry usage later). word_id stays NULL until the word
--   is saved; a lookup's card is cached on the encounter so a later save
--   costs no model call.
--   user_language_profiles.daily_new_words caps how many words a day enter
--   study per language (the review call: 10 new words a day).
--   user_vocabulary.study_started_at marks when a word entered study so the
--   cap can count today's starts.
-- =============================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.word_encounters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  word_id uuid REFERENCES public.user_vocabulary(id) ON DELETE SET NULL,
  language text NOT NULL,
  lemma text NOT NULL,
  sense text,
  surface text NOT NULL,
  sentence text,
  kind text NOT NULL,
  source_type text NOT NULL,
  source_id uuid,
  page integer,
  card jsonb,
  card_status text NOT NULL DEFAULT 'ok',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT word_encounters_kind_check
    CHECK (kind IN ('lookup', 'read', 'entry_text', 'entry_fix', 'entry_rewrite', 'used_ok', 'used_error')),
  CONSTRAINT word_encounters_source_type_check
    CHECK (source_type IN ('entry', 'book_session', 'manual')),
  CONSTRAINT word_encounters_card_status_check
    CHECK (card_status IN ('ok', 'failed'))
);

COMMENT ON TABLE public.word_encounters IS
  'Every place the learner met a word. word_id links to the notebook once saved; card caches a lookup so saving costs no model call.';
COMMENT ON COLUMN public.word_encounters.kind IS
  'How the word was met: a lookup, reading, the learner''s own text, a fix, the rewrite, or a later writing use.';
COMMENT ON COLUMN public.word_encounters.card IS
  'The lookup card, cached per user x lemma x sense. Never holds provider error text; failures store NULL with card_status failed.';

CREATE INDEX IF NOT EXISTS idx_word_encounters_user_language_lemma
  ON public.word_encounters (user_id, language, lemma, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_word_encounters_word
  ON public.word_encounters (word_id)
  WHERE word_id IS NOT NULL;

ALTER TABLE public.word_encounters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "word_encounters_select_own" ON public.word_encounters;
CREATE POLICY "word_encounters_select_own"
ON public.word_encounters FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "word_encounters_insert_own" ON public.word_encounters;
CREATE POLICY "word_encounters_insert_own"
ON public.word_encounters FOR INSERT
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "word_encounters_update_own" ON public.word_encounters;
CREATE POLICY "word_encounters_update_own"
ON public.word_encounters FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "word_encounters_delete_own" ON public.word_encounters;
CREATE POLICY "word_encounters_delete_own"
ON public.word_encounters FOR DELETE
USING (auth.uid() = user_id);

ALTER TABLE public.user_language_profiles
  ADD COLUMN IF NOT EXISTS daily_new_words smallint NOT NULL DEFAULT 10;

ALTER TABLE public.user_language_profiles
  DROP CONSTRAINT IF EXISTS user_language_profiles_daily_new_words_check,
  ADD CONSTRAINT user_language_profiles_daily_new_words_check
    CHECK (daily_new_words BETWEEN 1 AND 100);

COMMENT ON COLUMN public.user_language_profiles.daily_new_words IS
  'How many words a day may enter study for this language. Words over the cap stay New until tomorrow.';

ALTER TABLE public.user_vocabulary
  ADD COLUMN IF NOT EXISTS study_started_at timestamptz;

COMMENT ON COLUMN public.user_vocabulary.study_started_at IS
  'When the word entered study (triage "Study"). Drives the per-language daily new-word cap.';

COMMIT;

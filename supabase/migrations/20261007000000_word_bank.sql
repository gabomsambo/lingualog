-- =============================================
-- Migration: Vocabulary V4 - the word bank and "used it" mastery
-- Created: 2026-10-31
-- Description:
--   journal_entries.target_words remembers which notebook words the learner chose
--   to write an entry with (so a retried analysis checks the same words) and
--   target_word_uses keeps the tutor's checked verdict per word, plus what the use
--   did to the word. Neither column holds provider error text: a failed analysis
--   stores only the chosen words.
--   Uses in the learner's own entries are word_encounters of kind used_ok /
--   used_error (both kinds already exist); two partial indexes keep "which words did
--   this entry use" and "on how many days was this word used correctly" cheap.
-- =============================================

BEGIN;

ALTER TABLE public.journal_entries
  ADD COLUMN IF NOT EXISTS target_words jsonb,
  ADD COLUMN IF NOT EXISTS target_word_uses jsonb;

COMMENT ON COLUMN public.journal_entries.target_words IS
  'Notebook words chosen from the word bank for this entry: [{word_id, lemma, term, challenge}]. NULL when none were chosen.';
COMMENT ON COLUMN public.journal_entries.target_word_uses IS
  'Checked verdict per target word: [{word_id, term, status, form_in_text, fix, note, sentence, word_status, became_mastered, use_days, credited}]. status is used_correctly, used_with_error, not_used or unclear.';

CREATE INDEX IF NOT EXISTS idx_word_encounters_entry_uses
  ON public.word_encounters (user_id, source_id)
  WHERE kind IN ('used_ok', 'used_error');

CREATE INDEX IF NOT EXISTS idx_word_encounters_correct_uses
  ON public.word_encounters (word_id, created_at)
  WHERE kind = 'used_ok';

COMMIT;

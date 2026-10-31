-- =============================================
-- Migration: Vocabulary V6 - progress, lists and export
-- Created: 2026-11-03
-- Description:
--   V6 computes notebook counts, lists and exports from the V1-V3 tables and
--   adds no storage for them. The one stored piece is the optional placement
--   check: a vocabulary-size estimate (an estimate, never a score) with the
--   sample words the learner tapped, kept per language profile so the later
--   book-mode coverage estimate can seed "known" from it.
-- =============================================

BEGIN;

ALTER TABLE public.user_language_profiles
  ADD COLUMN IF NOT EXISTS placement jsonb;

COMMENT ON COLUMN public.user_language_profiles.placement IS
  'Optional vocabulary-size placement check: {v, estimate, sample_size, known, checked_at}. An estimate, never a score.';

COMMIT;

-- =============================================
-- Migration: Add journal entry analysis status columns
-- Version: 005
-- Created: 2026-10-03
-- Description:
--   Adds honest failure tracking for AI feedback:
--   - analysis_status: 'ok', 'failed', 'mock', or 'legacy'
--     (pre-existing rows are backfilled as 'legacy'; new inserts must set it explicitly)
--   - analysis_model: model/provider used for the analysis
--   - analysis_error_code: stable error code when analysis fails
-- =============================================

BEGIN;

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS analysis_status text DEFAULT 'legacy';

ALTER TABLE public.journal_entries
ALTER COLUMN analysis_status DROP DEFAULT;

ALTER TABLE public.journal_entries
ALTER COLUMN analysis_status SET NOT NULL;

ALTER TABLE public.journal_entries
DROP CONSTRAINT IF EXISTS journal_entries_analysis_status_check;

ALTER TABLE public.journal_entries
ADD CONSTRAINT journal_entries_analysis_status_check
CHECK (analysis_status IN ('ok', 'failed', 'mock', 'legacy'));

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS analysis_model text;

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS analysis_error_code text;

COMMENT ON COLUMN public.journal_entries.analysis_status IS 'Lifecycle state of AI feedback: ok, failed, mock, or legacy (pre-migration rows of unknown provenance)';
COMMENT ON COLUMN public.journal_entries.analysis_model IS 'Model/provider that produced the analysis';
COMMENT ON COLUMN public.journal_entries.analysis_error_code IS 'Stable error code when analysis_status is failed';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'migration_log'
    ) THEN
        INSERT INTO public.migration_log (version, name, applied_at)
        VALUES ('005', 'add_analysis_status', NOW())
        ON CONFLICT (version) DO NOTHING;
    END IF;
END $$;

COMMIT;

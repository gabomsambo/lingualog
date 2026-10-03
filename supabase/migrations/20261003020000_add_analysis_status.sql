-- =============================================
-- Migration: Add journal entry analysis status columns
-- Version: 006
-- Created: 2026-10-03
-- Description:
--   Adds honest failure tracking for AI feedback:
--   - analysis_status: 'ok', 'failed', or 'mock'
--   - analysis_model: model/provider used for the analysis
--   - analysis_error_code: stable error code when analysis fails
-- =============================================

BEGIN;

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS analysis_status text DEFAULT 'ok'
CHECK (analysis_status IN ('ok', 'failed', 'mock'));

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS analysis_model text;

ALTER TABLE public.journal_entries
ADD COLUMN IF NOT EXISTS analysis_error_code text;

COMMENT ON COLUMN public.journal_entries.analysis_status IS 'Lifecycle state of AI feedback: ok, failed, or mock';
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

-- =============================================
-- Migration: Fix Translation Policy Constraint
-- Version: 004
-- Created: 2025-01-05
-- Description:
--   Fixes translation_policy_snapshot constraint to allow 'L2_to_L1' and 'omit'
--   values used by the immersion level system.
--   - Level 0 (Native-First) uses 'L2_to_L1'
--   - Level 3 (Full Immersion) uses 'omit'
-- =============================================

BEGIN;

-- Step 1: Drop old constraint that only allowed ('none', 'on_demand', 'automatic', 'smart')
ALTER TABLE public.journal_entries
DROP CONSTRAINT IF EXISTS journal_entries_translation_policy_snapshot_check;

-- Step 2: Add new constraint with all valid translation policies
-- Valid values from lang_policy.py IMMERSION_MAP:
--   - 'L2_to_L1' (Level 0: Native-First - always show translation)
--   - 'on_demand' (Level 1-2: show translation behind toggle)
--   - 'omit' (Level 3: Full Immersion - no translation)
--   - Legacy: 'none', 'automatic', 'smart' (kept for backward compatibility)
ALTER TABLE public.journal_entries
ADD CONSTRAINT journal_entries_translation_policy_snapshot_check
CHECK (
  translation_policy_snapshot IS NULL OR
  translation_policy_snapshot IN ('none', 'on_demand', 'automatic', 'smart', 'L2_to_L1', 'omit')
);

-- Step 3: Log migration completion
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'migration_log'
    ) THEN
        INSERT INTO public.migration_log (version, name, applied_at)
        VALUES ('004', 'fix_translation_policy_constraint', NOW())
        ON CONFLICT (version) DO NOTHING;
    END IF;
END $$;

COMMIT;

-- =============================================
-- Verification Queries (Run these after migration to verify success)
-- =============================================

-- Check the new constraint
-- SELECT constraint_name, check_clause
-- FROM information_schema.check_constraints
-- WHERE constraint_name = 'journal_entries_translation_policy_snapshot_check';
-- Expected: constraint includes 'L2_to_L1' and 'omit'

-- Test inserting with L2_to_L1 (should succeed after migration)
-- This would be set by immersion level 0 entries

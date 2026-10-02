-- =============================================
-- Migration: Fix Immersion Level Constraint (0-3)
-- Version: 003
-- Created: 2025-01-05
-- Description:
--   Fixes critical bug where immersion level 0 (Native-First) is rejected by database.
--   Changes constraint from (1-5) to (0-3) to match plan specification and frontend UI.
--   Migrates any existing users with level > 3 to level 3 for backward compatibility.
-- =============================================

BEGIN;

-- Step 1: Migrate existing data with invalid levels
-- Update any users with immersion_level > 3 to level 3 (Full Immersion)
-- This ensures no constraint violation when we add the new constraint
UPDATE public.user_settings
SET immersion_level = 3
WHERE immersion_level > 3;

-- Step 2: Drop old constraint (1-5 range)
ALTER TABLE public.user_settings
DROP CONSTRAINT IF EXISTS user_settings_immersion_level_check;

-- Step 3: Add correct constraint (0-3 range)
-- Level 0: Native-First
-- Level 1: Guided Bilingual
-- Level 2: Balanced Immersion
-- Level 3: Full Immersion
ALTER TABLE public.user_settings
ADD CONSTRAINT user_settings_immersion_level_check
CHECK (immersion_level >= 0 AND immersion_level <= 3);

-- Step 4: Log migration completion
-- Only insert if migration_log table exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'migration_log'
    ) THEN
        INSERT INTO public.migration_log (version, name, applied_at)
        VALUES ('003', 'fix_immersion_levels', NOW())
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
-- WHERE constraint_name = 'user_settings_immersion_level_check';
-- Expected: ((immersion_level >= 0) AND (immersion_level <= 3))

-- Check for any remaining invalid levels (should return 0 rows)
-- SELECT user_id, immersion_level
-- FROM public.user_settings
-- WHERE immersion_level < 0 OR immersion_level > 3;

-- Test inserting level 0 (should succeed)
-- UPDATE public.user_settings SET immersion_level = 0 WHERE user_id = '[test-user-id]';

-- Test inserting level 4 (should fail with constraint violation)
-- UPDATE public.user_settings SET immersion_level = 4 WHERE user_id = '[test-user-id]';

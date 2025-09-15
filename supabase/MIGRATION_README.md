# Supabase Migrations Guide

This document explains how to apply database migrations to the LinguaLog Supabase project.

## Overview

Migrations are stored in the `supabase/sql/` directory and should be applied in order. Each migration is designed to be idempotent (safe to run multiple times).

## Migration Files

- `001_create_journal_entries.sql` - Initial journal entries table
- `002_multilingual_preferences.sql` - **NEW** Multilingual preferences and entry snapshots

## How to Apply Migrations

### Method 1: Supabase Dashboard (Recommended)

1. **Open Supabase Dashboard**
   - Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
   - Select your LinguaLog project

2. **Navigate to SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Apply Migration**
   - Copy the contents of `002_multilingual_preferences.sql`
   - Paste into the SQL editor
   - Click "Run" to execute the migration

4. **Verify Success**
   - Check that no errors are returned
   - Verify new columns exist in the "Table Editor"

### Method 2: Supabase CLI

If you have the Supabase CLI installed:

```bash
# Navigate to project root
cd /path/to/lingualog

# Apply migration
supabase db push --local  # For local development
# OR
supabase db push          # For production (be careful!)
```

### Method 3: Direct SQL Execution

For advanced users with direct database access:

```bash
# Connect to your Supabase database
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"

# Run the migration
\i supabase/sql/002_multilingual_preferences.sql
```

## Migration 002: Multilingual Preferences

### What This Migration Does

#### User Settings Table Extensions
Adds the following columns to `user_settings`:

- `interface_lang` (text, default: 'en') - UI language preference
- `native_lang` (text, default: 'en') - User's native language  
- `default_target_lang` (text, nullable) - Primary learning language
- `explanation_mode` (text, default: 'bilingual') - How AI explanations are presented
- `immersion_level` (smallint, default: 1) - Immersion level 1-5
- `strictness` (text, default: 'medium') - Correction strictness level
- `formality` (text, default: 'neutral') - Formality preference

#### Journal Entries Table Extensions
Adds the following columns to `journal_entries`:

- `target_language` (text, default: 'en') - Language for this entry
- `ui_language_snapshot` (text, nullable) - UI language when created
- `explanation_language_snapshot` (text, nullable) - Explanation language used
- `translation_policy_snapshot` (text, nullable) - Translation policy in effect
- `proficiency_estimate` (text, nullable) - User's estimated proficiency level

### Data Preservation

✅ **This migration is safe and preserves all existing data:**

- Existing `user_settings` rows remain intact
- Existing `journal_entries` remain intact  
- New columns have sensible defaults
- Existing values are migrated where applicable (e.g., `app_language` → `interface_lang`)

### Validation Rules

The migration includes data validation:
- Language codes must follow ISO format (e.g., 'en', 'es-ES')
- Enum values are validated (e.g., strictness: gentle/medium/strict/pedantic)
- Immersion level must be 1-5
- All constraints have descriptive names for easy maintenance

### Performance Considerations

- New indexes are created for frequently queried columns
- Migration runs quickly even on large datasets
- No blocking operations that would cause downtime

## Rollback (If Needed)

If you need to rollback this migration:

⚠️ **Warning**: Rolling back will lose the new multilingual preference data!

```sql
-- Remove added columns from user_settings
ALTER TABLE public.user_settings 
DROP COLUMN IF EXISTS interface_lang,
DROP COLUMN IF EXISTS native_lang,
DROP COLUMN IF EXISTS default_target_lang,
DROP COLUMN IF EXISTS explanation_mode,
DROP COLUMN IF EXISTS immersion_level,
DROP COLUMN IF EXISTS strictness,
DROP COLUMN IF EXISTS formality;

-- Remove added columns from journal_entries  
ALTER TABLE public.journal_entries
DROP COLUMN IF EXISTS target_language,
DROP COLUMN IF EXISTS ui_language_snapshot,
DROP COLUMN IF EXISTS explanation_language_snapshot,
DROP COLUMN IF EXISTS translation_policy_snapshot,
DROP COLUMN IF EXISTS proficiency_estimate;

-- Remove indexes
DROP INDEX IF EXISTS idx_journal_entries_target_language;
DROP INDEX IF EXISTS idx_journal_entries_proficiency;
DROP INDEX IF EXISTS idx_user_settings_languages;
```

## Verification Steps

After applying the migration, verify it worked correctly:

### 1. Check New Columns Exist

```sql
-- Check user_settings columns
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'user_settings' 
AND column_name IN ('interface_lang', 'native_lang', 'default_target_lang', 'explanation_mode', 'immersion_level', 'strictness', 'formality');

-- Check journal_entries columns  
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'journal_entries'
AND column_name IN ('target_language', 'ui_language_snapshot', 'explanation_language_snapshot', 'translation_policy_snapshot', 'proficiency_estimate');
```

### 2. Verify Data Integrity

```sql
-- Check that existing data is preserved
SELECT COUNT(*) FROM user_settings; -- Should match pre-migration count
SELECT COUNT(*) FROM journal_entries; -- Should match pre-migration count

-- Check default values are applied
SELECT interface_lang, native_lang, explanation_mode, immersion_level, strictness, formality
FROM user_settings LIMIT 5;
```

### 3. Test New Functionality

```sql
-- Test inserting new user settings
INSERT INTO user_settings (user_id, interface_lang, native_lang, default_target_lang, explanation_mode, immersion_level, strictness, formality)
VALUES (gen_random_uuid(), 'es', 'en', 'es', 'bilingual', 3, 'medium', 'neutral');

-- Test inserting new journal entry
INSERT INTO journal_entries (user_id, original_text, target_language, ui_language_snapshot, proficiency_estimate)
VALUES (gen_random_uuid(), 'Test entry', 'es', 'en', 'intermediate');
```

## Troubleshooting

### Common Issues

1. **"Column already exists" errors**
   - This is normal and expected - the migration uses `IF NOT EXISTS`
   - The migration is idempotent and safe to re-run

2. **"Check constraint violation" errors**  
   - Verify language codes follow the correct format (e.g., 'en', 'es-MX')
   - Check enum values match exactly (case-sensitive)

3. **"Relation does not exist" errors**
   - Ensure you're connected to the correct database
   - Verify table names match your schema

### Getting Help

If you encounter issues:

1. Check the Supabase dashboard logs
2. Verify your database connection
3. Ensure you have the necessary permissions
4. Contact the development team with specific error messages

## Next Steps

After applying this migration:

1. Update your application code to use the new columns
2. Test the multilingual functionality thoroughly  
3. Update API endpoints to handle new language preferences
4. Consider adding frontend UI for the new settings

---

**Migration Author**: LinguaLog Development Team  
**Created**: 2025-09-15  
**Version**: 002  
**Status**: Ready for production ✅

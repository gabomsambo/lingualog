name: "Multilingual Immersion System Fix & Language Switching Enhancement"
description: |
  Fix critical immersion level inconsistencies (0-3 standardization) and enhance
  language switching to support seamless multi-language learning with progress tracking per language.

---

## Goal

**Feature Goal**: Standardize immersion levels to 0-3 across the entire stack and enable seamless language switching where users can learn multiple languages over time, with progress tracked separately per language.

**Deliverable**:
- Database constraint allows immersion level 0-3 (currently blocks 0)
- Backend code removes unused levels 4-5
- Users can switch `default_target_lang` in settings and see entries filtered by that language
- Switching back to a previous language restores that language's entries and progress

**Success Definition**:
- User can set immersion level to 0 (Native-First) without database errors
- Frontend slider (0-3) matches backend validation (0-3) matches database constraints (0-3)
- User learning Spanish can switch to French in settings, create French entries, then switch back to Spanish and see their Spanish entries
- No breaking changes to existing entries or user data

---

## Why

**Problems Solved**:
1. **Critical Bug**: Users cannot select immersion level 0 (Native-First) - frontend allows it but database rejects it
2. **Confusion**: 3 different immersion ranges across codebase (0-3, 1-5, 0-5)
3. **Dead Code**: Levels 4-5 exist in backend but are unreachable and duplicate level 3 behavior
4. **UX Gap**: Users can't easily switch between learning different languages without losing progress

**User Impact**:
- Beginners need level 0 (Native-First) for maximum support - currently broken
- Polyglots learning multiple languages need clear language switching - currently confusing with array UI
- Existing users won't notice changes (backward compatible)

**Business Value**:
- Matches plan specification (MULTI_LINGUAL_PROBLEM.md)
- Enables polyglot users to use one app for multiple languages
- Reduces support tickets about "can't select level 0"

---

## What

### User-Visible Behavior

**Before (Broken)**:
1. User moves slider to "0 - Native First" in settings
2. Clicks "Save Changes"
3. ❌ Error: Database constraint violation (immersion_level must be >= 1)

**After (Fixed)**:
1. User moves slider to "0 - Native First" in settings
2. Clicks "Save Changes"
3. ✅ Saves successfully, all future entries use Native-First explanations

**New Language Switching Flow**:
1. User learning Spanish (has 50 Spanish entries)
2. Goes to Settings → Changes "Default Target Language" from Spanish to French
3. Dashboard now shows 0 entries (fresh start for French)
4. User creates 10 French entries over time
5. User switches back to Spanish in Settings
6. Dashboard shows original 50 Spanish entries
7. User can switch between languages anytime, progress is preserved

### Technical Requirements

1. **Database Migration**: Alter `user_settings.immersion_level` constraint from `>= 1 AND <= 5` to `>= 0 AND <= 3`
2. **Backend Code**: Remove levels 4-5 from `IMMERSION_MAP` and related functions
3. **Tests**: Update to only test levels 0-3
4. **Frontend**: Already correct (0-3 slider), but deprecate `targetLanguages` array UI
5. **Backward Compatibility**: Migrate any users with level > 3 to level 3

### Success Criteria
- [ ] Database accepts immersion level 0
- [ ] All tests pass with 0-3 range
- [ ] User can save settings with level 0 via frontend
- [ ] Backend validation rejects level 4 or 5
- [ ] User can switch default_target_lang and see filtered entries
- [ ] No data loss for existing entries
- [ ] Existing users with level 4-5 auto-migrate to 3

---

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window

- file: MULTILINGUAL_ANALYSIS.md
  why: Complete analysis of current vs desired state, includes all inconsistencies
  critical: Section on "Immersion Level Range Confusion" - shows exact problem

- file: MULTI_LINGUAL_PROBLEM.md
  why: Original plan specification with 0-3 immersion table
  critical: "Immersion slider → output languages" table (lines 23-29)

- file: backend/lang_policy.py
  why: Contains IMMERSION_MAP that needs levels 4-5 removed
  pattern: Lines 35-43 define the map, lines 128-142 use it
  critical: DEFAULT_SETTINGS at line 46 has immersion_level: 1

- file: backend/prompt_builder.py
  why: Uses immersion levels for proficiency estimation
  pattern: _estimate_proficiency_level() function at lines 253-270
  critical: Has hardcoded logic for levels 4-5 that needs removal

- file: supabase/sql/002_multilingual_preferences.sql
  why: Current migration with WRONG constraint
  pattern: Line 44-46 has CHECK constraint that needs fixing
  critical: Also has default value setup

- file: backend/tests/test_lang_policy.py
  why: Comprehensive tests that validate immersion behavior
  pattern: Tests levels 0, 1, 2, 3, 4 - need to remove level 4 tests
  critical: Lines 267-270 test invalid immersion level 10

- file: frontend/v0_lingua-log/app/(app)/settings/page.tsx
  why: Settings UI with slider already correctly set to 0-3
  pattern: Line 551-567 - slider max={3} min={0}
  critical: Line 172-177 loads settings, must handle legacy data

- file: backend/server.py
  why: Uses resolve_effective() and saves entries with snapshots
  pattern: Lines 238-306 - journal entry endpoint
  critical: Line 302 saves snapshot_data which includes immersion level

- file: backend/database.py
  why: Defines save/fetch functions for entries and settings
  pattern: fetch_entries() at line 174 - filters by user_id only
  critical: Can be enhanced to filter by language for language switching

- url: https://supabase.com/docs/guides/database/tables#check-constraints
  why: How to alter CHECK constraints in Supabase/Postgres
  section: "Altering constraints"

- url: https://www.postgresql.org/docs/current/ddl-constraints.html
  why: Postgres constraint documentation
  section: "Check Constraints"
```

### Current Codebase Structure (Relevant Files)

```bash
backend/
├── lang_policy.py              # IMMERSION_MAP (lines 35-43) - MODIFY
├── prompt_builder.py           # Proficiency estimation (lines 253-270) - MODIFY
├── server.py                   # Entry creation endpoint (lines 238-306) - VERIFY
├── database.py                 # DB operations - ENHANCE for filtering
├── models.py                   # Request models - VERIFY
└── tests/
    └── test_lang_policy.py     # Immersion tests - MODIFY

supabase/
└── sql/
    ├── 002_multilingual_preferences.sql  # Current migration - REFERENCE
    └── 003_fix_immersion_levels.sql      # New migration - CREATE

frontend/v0_lingua-log/
└── app/(app)/
    ├── settings/
    │   └── page.tsx            # Settings UI (lines 551-567) - VERIFY/MODIFY
    └── dashboard/
        └── page.tsx            # Dashboard - ENHANCE for language filtering
```

### Desired Codebase (Files to Add)

```bash
supabase/sql/
└── 003_fix_immersion_levels.sql   # Migration to fix constraint + migrate data

PRPs/ai_docs/
└── immersion_levels_spec.md       # Document the 0-3 levels for future reference
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Supabase/Postgres constraint modification requires DROP then ADD
# Can't ALTER constraint in-place - must drop old, add new

# GOTCHA: Migration must handle existing data with levels 4-5
# UPDATE before adding new constraint to avoid violation

# PATTERN: Supabase migrations are idempotent - use IF NOT EXISTS, IF EXISTS

# CRITICAL: Frontend may have cached user settings with level 4-5
# Backend validation will catch and convert to 3

# GOTCHA: Tests use pytest - not unittest
# Import pattern: from lang_policy import resolve_effective, IMMERSION_MAP

# PATTERN: Database functions return dict, not Pydantic models
# Server converts to models for API response

# CRITICAL: User entries have target_language field (per-entry)
# User settings have default_target_lang (user preference)
# These are separate - entry language is immutable, setting is changeable

# GOTCHA: Language switching works via filtering, not data deletion
# fetch_entries() can filter by language if we add that parameter
```

---

## Implementation Blueprint

### Data Models and Structure

**No new models needed** - using existing:

```python
# backend/models.py (existing - verify only)
class JournalEntryRequest(BaseModel):
    text: str
    language: str  # Per-entry target language (immutable)
    target_language: Optional[str]  # Override for this entry
    immersion_level: Optional[int] = Field(None, ge=0, le=3)  # ← Verify range

# Effective settings (existing)
@dataclass
class EffectiveSettings:
    l1: str
    l2: str
    immersion_level: int  # Will be 0-3 after fix
    # ... other fields
```

**Database Schema (modified)**:

```sql
-- user_settings table (MODIFY constraint)
ALTER TABLE user_settings
  DROP CONSTRAINT IF EXISTS user_settings_immersion_level_check;

ALTER TABLE user_settings
  ADD CONSTRAINT user_settings_immersion_level_check
  CHECK (immersion_level >= 0 AND immersion_level <= 3);

-- journal_entries table (no changes - already has target_language)
-- Each entry stores which language it was written in
```

---

### Implementation Tasks (Dependency-Ordered)

```yaml
Task 1: Create Database Migration (003_fix_immersion_levels.sql)
PRIORITY: CRITICAL - Must run before code changes to avoid constraint violations
CREATE supabase/sql/003_fix_immersion_levels.sql:
  - DROP old constraint: user_settings_immersion_level_check (1-5)
  - UPDATE existing data: SET immersion_level = 3 WHERE immersion_level > 3
  - ADD new constraint: CHECK (immersion_level >= 0 AND immersion_level <= 3)
  - UPDATE default value if needed
  - Add transaction wrapper for safety
  PATTERN: Follow 002_multilingual_preferences.sql structure
  VERIFY: Idempotent (use IF EXISTS, IF NOT EXISTS)

Task 2: Update IMMERSION_MAP in lang_policy.py
MODIFY backend/lang_policy.py:
  - FIND: IMMERSION_MAP dictionary (lines 35-43)
  - REMOVE: entries for keys 4 and 5
  - KEEP: Only 0, 1, 2, 3 entries
  - VERIFY: Comments explain each level clearly
  PATTERN: Should match MULTI_LINGUAL_PROBLEM.md table exactly

Task 3: Update Proficiency Estimation in prompt_builder.py
MODIFY backend/prompt_builder.py:
  - FIND: _estimate_proficiency_level() function (lines 253-270)
  - REMOVE: elif branches for immersion == 4 and == 5
  - SIMPLIFY: immersion 3 → "intermediate", no need for 4-5 logic
  - UPDATE: docstring to reflect 0-3 range
  PATTERN: Simple if/elif chain based on immersion level

Task 4: Update Validation in models.py
MODIFY backend/models.py:
  - FIND: JournalEntryRequest class (line 13)
  - VERIFY: immersion_level field has Field(None, ge=0, le=3)
  - ADD if missing: ge=0, le=3 constraint
  PATTERN: Uses Pydantic Field validators

Task 5: Update Tests to Remove Level 4-5 References
MODIFY backend/tests/test_lang_policy.py:
  - FIND: test_immersion_level_2_bilingual() (around line 78)
  - REMOVE: Any tests referencing level 4 or 5
  - VERIFY: test_realistic_advanced_scenario() uses valid level (3 or lower)
  - ADD: New test for level 0 specifically (test_immersion_level_0_native_first)
  PATTERN: Follow existing test structure with profile + overrides

Task 6: Add Language Filtering to fetch_entries (Enhancement)
MODIFY backend/database.py:
  - FIND: fetch_entries() function (line 174)
  - ADD: Optional language parameter: language: Optional[str] = None
  - ADD: Filter logic: if language: query = query.eq("target_language", language)
  - PRESERVE: Existing user_id filtering
  PATTERN: Follow existing Supabase query builder pattern

Task 7: Update Dashboard to Filter by Current Language (Frontend Enhancement)
MODIFY frontend/v0_lingua-log/app/(app)/dashboard/page.tsx:
  - FIND: fetchEntries() call
  - ADD: Pass current default_target_lang as filter
  - PATTERN: Get from user settings loaded at app startup
  - ENHANCE: Add language switcher dropdown in dashboard header (optional)

Task 8: Deprecate targetLanguages Array UI (Settings Cleanup)
MODIFY frontend/v0_lingua-log/app/(app)/settings/page.tsx:
  - FIND: "Target Languages" section with badges (lines 572-612)
  - HIDE: This entire section (comment out or conditional render)
  - KEEP: Database field for backward compatibility
  - ADD: Helper text explaining language switching via "Default Target Language"
  PATTERN: Use conditional rendering: {false && <section>...</section>}

Task 9: Add Migration Log Entry
MODIFY supabase/sql/003_fix_immersion_levels.sql:
  - ADD: Migration log insert at end
  - PATTERN: Same as 002_multilingual_preferences.sql (lines 153-159)
  - VERIFY: Migration version is "003"

Task 10: Create Documentation Reference
CREATE PRPs/ai_docs/immersion_levels_spec.md:
  - DOCUMENT: 0-3 levels with names and behaviors
  - COPY: Table from MULTI_LINGUAL_PROBLEM.md
  - ADD: Code references to IMMERSION_MAP
  - PURPOSE: Single source of truth for future developers
```

---

### Task 1 Pseudocode: Database Migration

```sql
-- 003_fix_immersion_levels.sql
-- Migration: Fix immersion level constraint to match plan (0-3)
-- Created: 2025-01-XX
-- Description: Fixes critical bug where level 0 is rejected by database

BEGIN;

-- Step 1: Migrate existing data with invalid levels
UPDATE public.user_settings
SET immersion_level = 3
WHERE immersion_level > 3;
-- This ensures no constraint violation when we add new constraint

-- Step 2: Drop old constraint
ALTER TABLE public.user_settings
DROP CONSTRAINT IF EXISTS user_settings_immersion_level_check;

-- Step 3: Add correct constraint (0-3 instead of 1-5)
ALTER TABLE public.user_settings
ADD CONSTRAINT user_settings_immersion_level_check
CHECK (immersion_level >= 0 AND immersion_level <= 3);

-- Step 4: Log migration completion
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_log') THEN
        INSERT INTO migration_log (version, name, applied_at)
        VALUES ('003', 'fix_immersion_levels', NOW());
    END IF;
END $$;

COMMIT;
```

---

### Task 2 Pseudocode: Update IMMERSION_MAP

```python
# backend/lang_policy.py

# BEFORE (WRONG - has 6 levels):
IMMERSION_MAP = {
    0: ('native', 'L2_to_L1'),
    1: ('native', 'on_demand'),
    2: ('bilingual', 'on_demand'),
    3: ('target', 'omit'),
    4: ('target', 'omit'),         # REMOVE
    5: ('target', 'omit'),         # REMOVE
}

# AFTER (CORRECT - only 4 levels matching plan):
IMMERSION_MAP = {
    0: ('native', 'L2_to_L1'),     # Level 0: Native-First
    1: ('native', 'on_demand'),    # Level 1: Guided Bilingual
    2: ('bilingual', 'on_demand'), # Level 2: Balanced Immersion
    3: ('target', 'omit'),         # Level 3: Full Immersion
}

# Update docstring to clarify valid range
"""
Immersion level mapping (0-3):
- 0: Native-First - Maximum L1 support, always show translations
- 1: Guided Bilingual - L1 explanations, translations on-demand
- 2: Balanced Immersion - Bilingual explanations, translations on-demand
- 3: Full Immersion - L2 only, no translations
"""
```

---

### Task 3 Pseudocode: Update Proficiency Estimation

```python
# backend/prompt_builder.py

# BEFORE (lines 253-270):
def _estimate_proficiency_level(effective: EffectiveSettings) -> str:
    immersion = effective.immersion_level

    if immersion <= 1:
        return "beginner"
    elif immersion == 2:
        return "elementary"
    elif immersion == 3:
        return "intermediate"
    elif immersion == 4:          # REMOVE
        return "advanced"          # REMOVE
    else:  # immersion == 5       # REMOVE
        return "advanced"          # REMOVE

# AFTER (simplified):
def _estimate_proficiency_level(effective: EffectiveSettings) -> str:
    """
    Estimate proficiency level based on immersion setting.

    Valid immersion levels: 0-3
    Returns: beginner, elementary, intermediate, or advanced
    """
    immersion = effective.immersion_level

    if immersion == 0:
        return "beginner"         # Native-First users are beginners
    elif immersion == 1:
        return "elementary"       # Guided Bilingual
    elif immersion == 2:
        return "intermediate"     # Balanced Immersion
    else:  # immersion == 3
        return "advanced"         # Full Immersion users are advanced
```

---

### Task 6 Pseudocode: Add Language Filtering

```python
# backend/database.py - ENHANCE fetch_entries()

# BEFORE:
def fetch_entries(user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    # Only filters by user_id

# AFTER:
def fetch_entries(
    user_id: Optional[str] = None,
    language: Optional[str] = None,  # NEW parameter
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Fetch journal entries filtered by user and optionally by language.

    Args:
        user_id: Filter by user
        language: Filter by target_language (e.g., 'es', 'fr', 'ja')
        limit: Max entries to return

    Returns:
        List of entry dicts, sorted by created_at desc
    """
    supabase = create_supabase_client()
    query = supabase.table(JOURNAL_ENTRIES_TABLE).select("*")

    if user_id:
        query = query.eq("user_id", user_id)

    # NEW: Filter by language if specified
    if language:
        query = query.eq("target_language", language)

    query = query.limit(limit)
    response = query.execute()

    results = response.data
    results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return results
```

---

### Task 7 Pseudocode: Dashboard Language Filtering

```typescript
// frontend/v0_lingua-log/app/(app)/dashboard/page.tsx

// BEFORE: Fetch all entries
const entries = await getEntries(userId)

// AFTER: Fetch entries for current target language only
const userSettings = await getUserSettings()
const currentLanguage = userSettings.default_target_lang

const entries = await getEntries(userId, {
  language: currentLanguage  // NEW filter parameter
})

// OPTIONAL: Add language switcher in dashboard
<Select
  value={currentLanguage}
  onValueChange={(newLang) => {
    // Update user settings with new default_target_lang
    // Re-fetch entries for new language
    await updateUserSettings({ default_target_lang: newLang })
    setCurrentLanguage(newLang)
  }}
>
  {userSettings.target_languages.map(lang => (
    <SelectItem value={lang}>{LANGUAGES[lang].name}</SelectItem>
  ))}
</Select>
```

---

### Integration Points

```yaml
DATABASE:
  - migration: "supabase/sql/003_fix_immersion_levels.sql"
  - run_after: "002_multilingual_preferences.sql"
  - affects: "user_settings.immersion_level constraint"
  - data_migration: "UPDATE immersion_level > 3 to 3"

CONFIG:
  - no changes needed
  - existing DEFAULT_SETTINGS already has immersion_level: 1

ROUTES:
  - no new routes
  - existing /log-entry uses resolve_effective()
  - existing /user/settings validates immersion level
  - enhance /entries to accept language query param (optional)

FRONTEND:
  - Settings page: Already correct slider (0-3)
  - Settings page: Hide target_languages array UI
  - Dashboard: Add language filter to API call
  - Dashboard: Optional language switcher dropdown

TESTS:
  - backend/tests/test_lang_policy.py: Remove level 4-5 tests
  - backend/tests/test_lang_policy.py: Add explicit level 0 test
  - No new test files needed
```

---

## Validation Loop

### Level 1: Syntax & Type Checking

```bash
# CRITICAL: Run these FIRST before any testing

# Type check backend changes
cd backend
mypy lang_policy.py prompt_builder.py database.py models.py

# Expected: No errors
# If errors: Read carefully, fix type hints, re-run

# Lint backend changes
ruff check lang_policy.py prompt_builder.py database.py --fix

# Expected: Auto-fixes applied, no remaining errors
```

### Level 2: Unit Tests

```bash
# Run existing lang_policy tests (will fail until Task 5 complete)
cd backend
pytest tests/test_lang_policy.py -v

# Expected after Task 5:
# ✓ test_immersion_level_0_mapping
# ✓ test_immersion_level_3_mapping
# ✓ test_realistic_beginner_scenario (uses level 0 or 1)
# ✓ test_realistic_advanced_scenario (uses level 3, not 4)
# ✗ No tests for level 4 or 5

# Add new test for level 0 Native-First
# In test_lang_policy.py, add:
def test_immersion_level_0_native_first():
    """Test that level 0 maps to Native-First behavior."""
    profile = {
        'native_lang': 'en',
        'default_target_lang': 'es',
        'immersion_level': 0
    }

    effective = resolve_effective(profile)

    assert effective.immersion_level == 0
    assert effective.translation_policy == 'L2_to_L1'
    assert effective.explanation_mode == 'native_only'
```

### Level 3: Database Migration Test

```bash
# CRITICAL: Test migration on development database FIRST

# Connect to Supabase dev instance
psql postgresql://[dev-connection-string]

# Run migration manually
\i supabase/sql/003_fix_immersion_levels.sql

# Verify constraint
SELECT constraint_name, check_clause
FROM information_schema.check_constraints
WHERE constraint_name = 'user_settings_immersion_level_check';

# Expected output:
# check_clause: ((immersion_level >= 0) AND (immersion_level <= 3))

# Test inserting level 0 (should succeed)
UPDATE user_settings SET immersion_level = 0 WHERE user_id = '[test-user-id]';

# Test inserting level 4 (should fail)
UPDATE user_settings SET immersion_level = 4 WHERE user_id = '[test-user-id]';
# Expected: ERROR: new row violates check constraint

# Rollback test changes
ROLLBACK;
```

### Level 4: Integration Test - Settings Update

```bash
# Start backend server
cd backend
uvicorn backend.server:app --reload --port 8000

# Test updating user settings to level 0 (previously broken)
curl -X PUT http://localhost:8000/user/settings \
  -H "Content-Type: application/json" \
  -H "X-User-ID: [test-user-id]" \
  -d '{
    "immersion_level": 0,
    "native_lang": "en",
    "default_target_lang": "es"
  }'

# Expected: 200 OK with updated settings
# Verify: immersion_level is 0 in response

# Test invalid level (should fail validation)
curl -X PUT http://localhost:8000/user/settings \
  -H "Content-Type: application/json" \
  -H "X-User-ID: [test-user-id]" \
  -d '{"immersion_level": 5}'

# Expected: 422 Unprocessable Entity
# Error message about immersion_level must be 0-3
```

### Level 5: Integration Test - Language Switching

```bash
# Prerequisite: User has entries in both Spanish and French

# 1. Get user settings (current language)
curl http://localhost:8000/user/settings \
  -H "X-User-ID: [test-user-id]"

# Note default_target_lang (e.g., "es")

# 2. Fetch entries (should show Spanish entries)
curl http://localhost:8000/entries?language=es \
  -H "X-User-ID: [test-user-id]"

# Expected: Array of entries where target_language = "es"

# 3. Switch to French
curl -X PUT http://localhost:8000/user/settings \
  -H "Content-Type: application/json" \
  -H "X-User-ID: [test-user-id]" \
  -d '{"default_target_lang": "fr"}'

# 4. Fetch entries again (should show French entries)
curl http://localhost:8000/entries?language=fr \
  -H "X-User-ID: [test-user-id]"

# Expected: Array of entries where target_language = "fr"
# Should be different entries than step 2

# 5. Switch back to Spanish
curl -X PUT http://localhost:8000/user/settings \
  -H "Content-Type: application/json" \
  -H "X-User-ID: [test-user-id]" \
  -d '{"default_target_lang": "es"}'

# 6. Fetch Spanish entries again
curl http://localhost:8000/entries?language=es \
  -H "X-User-ID: [test-user-id]"

# Expected: Same Spanish entries from step 2 (progress preserved)
```

### Level 6: Frontend Test

```bash
# Start frontend dev server
cd frontend/v0_lingua-log
npm run dev

# Manual browser test:
# 1. Navigate to http://localhost:5173/settings
# 2. Move "Immersion Level" slider to 0 (Native-First)
# 3. Click "Save Changes"
# 4. Verify: No error toast, success message appears
# 5. Refresh page
# 6. Verify: Slider still at 0 (persisted)

# Test language switching:
# 1. Change "Default Target Language" to French
# 2. Save settings
# 3. Go to Dashboard
# 4. Verify: Shows "0 entries" or only French entries
# 5. Create a new French entry
# 6. Go back to Settings, change to Spanish
# 7. Go to Dashboard
# 8. Verify: Shows Spanish entries (French entry not visible)
```

---

## Final Validation Checklist

### Code Quality
- [ ] All tests pass: `cd backend && pytest tests/test_lang_policy.py -v`
- [ ] No type errors: `cd backend && mypy lang_policy.py prompt_builder.py`
- [ ] No linting errors: `cd backend && ruff check .`
- [ ] Migration is idempotent (can run multiple times safely)

### Functionality
- [ ] User can save immersion level 0 via frontend settings
- [ ] User cannot save immersion level 4 or 5 (validation error)
- [ ] Database constraint allows 0-3, rejects outside range
- [ ] IMMERSION_MAP only has 4 entries (0, 1, 2, 3)
- [ ] Proficiency estimation doesn't reference levels 4-5
- [ ] Tests only cover levels 0-3

### Language Switching
- [ ] User can change default_target_lang in settings
- [ ] Dashboard filters entries by current target language
- [ ] Switching languages shows different entry sets
- [ ] Switching back to previous language restores those entries
- [ ] New entries use current default_target_lang
- [ ] No data loss when switching languages

### Backward Compatibility
- [ ] Existing users with level 4-5 auto-migrate to 3
- [ ] Migration log entry created successfully
- [ ] No breaking changes to API contracts
- [ ] Frontend handles missing language gracefully

### Documentation
- [ ] PRPs/ai_docs/immersion_levels_spec.md created
- [ ] Migration SQL has clear comments
- [ ] Code comments updated for 0-3 range

---

## Anti-Patterns to Avoid

### Database
- ❌ Don't skip the UPDATE before adding constraint (will fail for existing level 4-5 users)
- ❌ Don't forget transaction wrapper (migration should be atomic)
- ❌ Don't hardcode migration version number in multiple places

### Code
- ❌ Don't leave dead code for levels 4-5 "just in case"
- ❌ Don't add new immersion levels without updating all 3 places (DB, backend, frontend)
- ❌ Don't change default immersion level without considering UX impact

### Testing
- ❌ Don't skip testing level 0 specifically (it was previously broken)
- ❌ Don't assume migration worked - verify constraint in database
- ❌ Don't test only happy path - test invalid levels too

### Language Switching
- ❌ Don't delete entries when switching languages (filter, don't delete)
- ❌ Don't modify target_language on existing entries (it's immutable)
- ❌ Don't confuse default_target_lang (setting) with target_language (entry field)

---

## Success Metrics

**Confidence Score**: 9/10 for one-pass implementation success

**Why High Confidence**:
- Clear, specific tasks with exact file locations and line numbers
- Existing test infrastructure to validate changes
- Well-understood problem with documented current state
- Small, focused scope (bug fix + enhancement, not rewrite)
- Backward compatible (no breaking changes)

**Remaining Risk (1 point)**:
- Migration timing coordination (need to deploy DB migration before code)
- Testing on production data (should test on staging first)

**Mitigation**:
- Deploy migration to staging first
- Verify no users have level > 3 in production (query first)
- Have rollback plan (migration reversal script)

---

## Deployment Plan

### Pre-Deployment Checks
1. Query production `user_settings` for any `immersion_level > 3`
2. If found, notify users or auto-migrate in maintenance window
3. Test full flow on staging environment

### Deployment Order (CRITICAL)
1. **First**: Deploy database migration (003_fix_immersion_levels.sql)
2. **Wait**: Verify migration succeeded (check constraint in DB)
3. **Then**: Deploy backend code changes
4. **Then**: Deploy frontend code changes
5. **Finally**: Monitor logs for validation errors

### Rollback Plan
If issues arise:
1. Revert backend/frontend deployments
2. Run rollback migration:
```sql
ALTER TABLE user_settings DROP CONSTRAINT user_settings_immersion_level_check;
ALTER TABLE user_settings ADD CONSTRAINT user_settings_immersion_level_check
  CHECK (immersion_level >= 1 AND immersion_level <= 5);
```
3. Notify users to avoid level 0 temporarily

---

## Notes for Implementer

**Start Here**: Read MULTILINGUAL_ANALYSIS.md fully to understand the problem context.

**Testing Strategy**: Run tests after each task to catch issues early. Don't wait until end.

**Migration Safety**: The database migration is the most critical piece. Test thoroughly on dev/staging before production.

**Language Switching**: The architecture already supports this (entries have target_language field). We're just adding filtering to make it user-visible.

**Target Languages Array**: We're keeping it in the database for backward compatibility, but hiding it from UI. Don't delete the field or data.

**Questions During Implementation**: If uncertain, check MULTI_LINGUAL_PROBLEM.md for the original plan specification.

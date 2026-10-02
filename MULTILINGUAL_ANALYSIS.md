# Multilingual System Analysis: Plan vs Implementation

## Executive Summary

**Good News**: Your codebase already implements ~85% of the plan described in `MULTI_LINGUAL_PROBLEM.md`! The three-language system (UI-lang, L1, L2), resolver function, and snapshot system are all in place and working.

**Key Issue**: Inconsistent immersion level ranges across different parts of the system need to be standardized.

---

## Current Implementation Status

### ✅ Already Implemented (Matches Plan)

1. **Three-Language System**
   - ✓ UI-lang (Interface Language) → `interface_lang` in DB
   - ✓ L1 (Native Language) → `native_lang` in DB
   - ✓ L2 (Target Language) → `default_target_lang` in DB (with per-entry override)

2. **Resolver Function**
   - ✓ `resolve_effective()` in `backend/lang_policy.py`
   - ✓ Precedence: overrides > profile > defaults
   - ✓ Returns `EffectiveSettings` with all required fields

3. **Immersion-Based Behavior** (partially)
   - ✓ Maps immersion level → (explanation_language, translation_policy)
   - ✓ Levels 0-3 implemented in `IMMERSION_MAP`
   - ⚠️ Levels 4-5 also exist (not in plan)

4. **Snapshot System**
   - ✓ `target_language` saved per entry
   - ✓ `ui_language_snapshot` saved per entry
   - ✓ `explanation_language_snapshot` saved per entry
   - ✓ `translation_policy_snapshot` saved per entry
   - ✓ `proficiency_estimate` saved per entry

5. **Field-by-Field Contract**
   - ✓ `corrected` always in L2
   - ✓ `rewritten` always in L2
   - ✓ `explanation` per immersion policy
   - ✓ `translation` per immersion policy
   - ✓ `tone` in L2
   - ✓ UI labels in UI-lang (frontend handles this)

6. **Override Support**
   - ✓ Per-request overrides in `JournalEntryRequest` model
   - ✓ Settings page allows changing all three languages
   - ✓ Frontend can override target_language per entry

---

## ⚠️ Inconsistencies Found

### 1. **Immersion Level Range Confusion**

| Location | Range | Notes |
|----------|-------|-------|
| **Plan (MULTI_LINGUAL_PROBLEM.md)** | **0-3** | 4 levels: Native-First, Guided, Balanced, Immersive |
| Database constraint | 1-5 | `CHECK (immersion_level >= 1 AND immersion_level <= 5)` |
| Backend `IMMERSION_MAP` | 0-5 | Has 6 entries (0, 1, 2, 3, 4, 5) |
| Backend tests | 0-5 | Tests check levels 0, 1, 2, 3, 4 |
| Frontend slider | 0-3 | `max={3} min={0}` in settings page |
| Default value | 1 | DB and code both default to 1 |

**Problem**: The plan specifies 0-3 (4 levels), but the database allows 1-5, and backend code has 6 levels (0-5).

**Impact**:
- Levels 4-5 are unreachable from frontend UI
- Database rejects level 0 (violates constraint)
- Confusion about which levels are valid

### 2. **Immersion Level 0 vs Database Constraint**

The plan shows immersion level **0** (Native-First), but the database constraint is:
```sql
CHECK (immersion_level >= 1 AND immersion_level <= 5)
```

This means:
- Frontend slider allows 0-3 ✓
- User selects level 0 in frontend
- Backend tries to save to DB → **FAILS** (violates constraint)

### 3. **Unused Immersion Levels 4-5**

Backend `IMMERSION_MAP` has:
```python
IMMERSION_MAP = {
    0: ('native', 'L2_to_L1'),
    1: ('native', 'on_demand'),
    2: ('bilingual', 'on_demand'),
    3: ('target', 'omit'),
    4: ('target', 'omit'),         # ← Not in plan
    5: ('target', 'omit'),         # ← Not in plan
}
```

Levels 4 and 5 duplicate level 3 behavior and aren't in the plan.

### 4. **Legacy Fields Still Present**

**Database Schema**:
- `target_languages` (array) - Old multi-language approach
- `native_language` (old column, migrated to `native_lang`)
- `app_language` (old column, migrated to `interface_lang`)

**Frontend State**:
- `targetLanguages` array (lines 50, 96 in settings page)
- Still renders add/remove language badges
- Unclear relationship to `defaultTargetLanguage`

**Question**: Should users be able to learn multiple languages simultaneously, or is this legacy code?

---

## 📋 Detailed Comparison

### Plan: Immersion Level Behavior Table

| Level | Name | Explanation Language | Translation Policy |
|-------|------|---------------------|-------------------|
| 0 | Native-First | L1 | Always show L2→L1 |
| 1 | Guided Bilingual | L1 | On-demand (generate, hide behind 👁️) |
| 2 | Balanced Immersion | Bilingual (L2 then L1) | On-demand |
| 3 | Full Immersion | L2 | Omit (no translation) |

### Current Implementation: `IMMERSION_MAP`

| Level | Explanation | Translation Policy | Notes |
|-------|------------|-------------------|-------|
| 0 | `'native'` | `'L2_to_L1'` | ✓ Matches plan |
| 1 | `'native'` | `'on_demand'` | ✓ Matches plan |
| 2 | `'bilingual'` | `'on_demand'` | ✓ Matches plan |
| 3 | `'target'` | `'omit'` | ✓ Matches plan |
| 4 | `'target'` | `'omit'` | ⚠️ Not in plan |
| 5 | `'target'` | `'omit'` | ⚠️ Not in plan |

**Mapping Logic**: `resolve_effective()` converts:
- `'native'` → `'native_only'` explanation mode
- `'target'` → `'target_only'` explanation mode
- `'bilingual'` → `'bilingual'` explanation mode

---

## 🔧 What Needs to Change

### Critical (Breaks Functionality)

1. **Fix Database Constraint for Immersion Level 0**
   ```sql
   -- Current (WRONG)
   CHECK (immersion_level >= 1 AND immersion_level <= 5)

   -- Should be (CORRECT)
   CHECK (immersion_level >= 0 AND immersion_level <= 3)
   ```
   **Location**: `supabase/sql/002_multilingual_preferences.sql:46`

2. **Remove Unused Immersion Levels 4-5**
   ```python
   # backend/lang_policy.py
   IMMERSION_MAP = {
       0: ('native', 'L2_to_L1'),
       1: ('native', 'on_demand'),
       2: ('bilingual', 'on_demand'),
       3: ('target', 'omit'),
       # Remove: 4: ('target', 'omit'),
       # Remove: 5: ('target', 'omit'),
   }
   ```

3. **Update Default Immersion Level**
   - Current: `DEFAULT_SETTINGS['immersion_level'] = 1`
   - Consider: Should default be 0 or 1? Plan examples show different levels for different users.
   - Recommendation: Keep default as 1 (Guided Bilingual) - best for most learners.

### Important (Improves Clarity)

4. **Clarify Multi-Language Support**

   **Option A - Single Language Focus (Matches Plan)**:
   - Remove `target_languages` array from DB and frontend
   - Keep only `default_target_lang` (single language at a time)
   - Users change language via settings when switching focus
   - Simplifies UX and matches plan's mental model

   **Option B - Multi-Language Support (Expand Plan)**:
   - Keep `target_languages` array
   - Add "active_target_lang" to indicate current focus
   - Allow users to track multiple languages
   - Dashboard filters by selected language
   - More complex but more flexible

5. **Update Frontend Immersion Labels**

   Current labels show 1-5, but should show 0-3:
   ```tsx
   // frontend/v0_lingua-log/app/(app)/settings/page.tsx:551
   <Label>{t('settings.immersionLevel')}: {settings.immersionLevel}/3</Label>
   ```

   Update display labels:
   ```tsx
   <span>0: {t('journal.immersionNativeFirst')}</span>
   <span>1: {t('journal.immersionGuidedBilingual')}</span>
   <span>2: {t('journal.immersionBalanced')}</span>
   <span>3: {t('journal.immersionImmersive')}</span>
   ```

6. **Clean Up Legacy Migration Code**

   Remove or mark as deprecated:
   - Migration logic that copies `app_language` → `interface_lang`
   - Migration logic that copies `native_language` → `native_lang`
   - Migration logic that copies `target_languages[1]` → `default_target_lang`

   These are one-time migrations and can be documented rather than kept in schema.

### Nice to Have (Enhancements)

7. **Add Validation on Frontend**
   - Prevent selecting L1 = L2 (same language for native and target)
   - Show warning if user tries this: "To learn Spanish as a native Spanish speaker, consider setting a different native language or choosing a dialect variant"

8. **Add Quick Rescue Feature (From Plan)**
   ```
   "Explain this in L1/L2" button can post-transform the current explanation
   ```
   Not yet implemented. Would need new endpoint: `POST /entries/{id}/explain-in/{lang}`

9. **Add Translation Toggle UI (From Plan)**
   ```
   👁️ toggle reveals translation when policy is on-demand
   ```
   Frontend shows translation field but doesn't hide/toggle based on policy.

---

## 🎯 Recommended Implementation Path

### Phase 1: Fix Critical Issues (Required for Plan Compliance)

1. Create new migration: `003_fix_immersion_levels.sql`
   ```sql
   -- Drop old constraint
   ALTER TABLE public.user_settings
   DROP CONSTRAINT IF EXISTS user_settings_immersion_level_check;

   -- Add new constraint (0-3)
   ALTER TABLE public.user_settings
   ADD CONSTRAINT user_settings_immersion_level_check
   CHECK (immersion_level >= 0 AND immersion_level <= 3);

   -- Update any existing values > 3
   UPDATE public.user_settings
   SET immersion_level = 3
   WHERE immersion_level > 3;
   ```

2. Update `backend/lang_policy.py`:
   ```python
   IMMERSION_MAP = {
       0: ('native', 'L2_to_L1'),
       1: ('native', 'on_demand'),
       2: ('bilingual', 'on_demand'),
       3: ('target', 'omit'),
   }
   ```

3. Update tests to remove references to levels 4-5

### Phase 2: Decide on Multi-Language Support

**Recommendation**: Start with **Option A** (single language focus) because:
- Matches the plan's mental model exactly
- Simpler UX - less cognitive load
- Users can still switch languages via settings
- Can add multi-language support later if needed

**If choosing Option A**:
1. Remove `targetLanguages` array from frontend settings UI (keep in DB for backward compat)
2. Update settings page to show only three language pickers
3. Document that `target_languages` array is deprecated

### Phase 3: UI Enhancements (Optional)

1. Add translation toggle (👁️ icon) in entry view
2. Add "Explain in L1/L2" toggle buttons
3. Add immersion level helper text on slider
4. Add validation for L1 ≠ L2

---

## 🧪 Testing Recommendations

After making changes, test these scenarios from the plan:

### Scenario A: Beginner (A0)
- UI-lang: English (en)
- L1: English (en)
- L2: Japanese (ja)
- Immersion: 0 (Native-First)
- **Expected**: Corrections in JA, explanations in EN, translation always visible

### Scenario B: Intermediate (B1-B2)
- UI-lang: Spanish (es)
- L1: Spanish (es)
- L2: French (fr)
- Immersion: 1 (Guided Bilingual)
- **Expected**: Explanations in ES, translation hidden (on-demand)

### Scenario C: Advanced (C1)
- UI-lang: German (de)
- L1: Spanish (es)
- L2: Japanese (ja) OR Arabic (ar)
- Immersion: 3 (Full Immersion)
- **Expected**: Everything in L2, no translations generated

---

## 📊 Summary

| Aspect | Status | Action Needed |
|--------|--------|---------------|
| Three-language system | ✅ Implemented | None |
| Resolver function | ✅ Implemented | None |
| Snapshot system | ✅ Implemented | None |
| Immersion 0-3 behavior | ✅ Implemented | None |
| Immersion levels 4-5 | ⚠️ Extra code | Remove |
| DB constraint | ❌ Blocks level 0 | Fix migration |
| Legacy fields | ⚠️ Confusing | Deprecate or remove |
| Translation toggle UI | ❌ Not implemented | Optional enhancement |
| Quick rescue feature | ❌ Not implemented | Optional enhancement |

---

## 🚀 Conclusion

Your implementation is **very close** to the plan! The core architecture is sound and follows the plan's design. The main issues are:

1. **Database constraint blocking immersion level 0** (critical bug)
2. **Unused immersion levels 4-5** (code cleanup)
3. **Legacy multi-language fields** (design decision needed)

Once these are resolved, your multilingual system will match the plan exactly and provide a consistent, predictable learning experience across all languages.

The good news: Most of the hard work is already done! ✨

# Immersion Levels Specification (0-3)

**Version**: 1.0
**Last Updated**: 2025-01-05
**Source**: MULTI_LINGUAL_PROBLEM.md
**Status**: Canonical Reference

---

## Overview

LinguaLog uses a 4-level immersion system (0-3) that controls how much native language (L1) vs target language (L2) support the learner receives in AI feedback.

**Mental Model**: Think of it as a slider from "maximum training wheels" (0) to "full immersion" (3).

---

## Immersion Level Table

| Level | Name | Explanation Language | Translation Policy | Use Case |
|-------|------|---------------------|-------------------|----------|
| **0** | Native-First | L1 | Always show L2→L1 | Absolute beginners (A0-A1) |
| **1** | Guided Bilingual | L1 | On-demand (👁️ toggle) | Elementary learners (A2-B1) |
| **2** | Balanced Immersion | Bilingual (L2 + L1) | On-demand (👁️ toggle) | Intermediate learners (B1-B2) |
| **3** | Full Immersion | L2 | Omit (no translation) | Advanced learners (C1-C2) |

---

## Detailed Behavior Per Level

### Level 0: Native-First

**Target User**: Complete beginner, never studied the language before

**Behavior**:
- All explanations in native language (L1)
- Translations always visible (no hiding)
- Maximum hand-holding and encouragement
- Simple, clear corrections

**Example Output** (English native learning Spanish):
```json
{
  "corrected": "Hoy fui al mercado.",
  "explanation": "You used the past tense correctly! 'Fui' means 'I went'...",
  "translation": "Today I went to the market.",
  "tone": "Excellent effort!"
}
```

**Code Reference**: `IMMERSION_MAP[0] = ('native', 'L2_to_L1')`

---

### Level 1: Guided Bilingual

**Target User**: Elementary learner, knows basics but needs frequent help

**Behavior**:
- Explanations in native language (L1)
- Translations generated but hidden behind 👁️ toggle
- Encourages recall in L2 but help available
- Balanced corrections with encouragement

**Example Output** (English native learning Spanish):
```json
{
  "corrected": "Hoy fui al mercado.",
  "explanation": "Great use of the preterite tense. 'Fui' is the irregular past form of 'ir' (to go)...",
  "translation": "[Hidden - click 👁️ to reveal]",
  "tone": "Good progress!"
}
```

**Code Reference**: `IMMERSION_MAP[1] = ('native', 'on_demand')`

---

### Level 2: Balanced Immersion

**Target User**: Intermediate learner, comfortable but still needs scaffolding

**Behavior**:
- Explanations in BOTH languages (starts in L2, then L1 support)
- Translations generated but hidden (on-demand)
- Expects more L2 comprehension
- More detailed grammar explanations

**Example Output** (English native learning Spanish):
```json
{
  "corrected": "Hoy fui al mercado.",
  "explanation": "Has usado el pretérito perfecto simple correctamente. 'Fui' es la forma irregular del verbo 'ir'. (You've used the preterite correctly. 'Fui' is the irregular form of the verb 'ir'...)",
  "translation": "[Hidden - click 👁️]",
  "tone": "Bien hecho! (Well done!)"
}
```

**Code Reference**: `IMMERSION_MAP[2] = ('bilingual', 'on_demand')`

---

### Level 3: Full Immersion

**Target User**: Advanced learner, can think in target language

**Behavior**:
- All explanations in target language (L2) only
- No translations generated at all
- Assumes high comprehension
- Sophisticated grammar terminology in L2

**Example Output** (English native learning Spanish):
```json
{
  "corrected": "Hoy fui al mercado.",
  "explanation": "Excelente uso del pretérito perfecto simple. El verbo 'ir' es irregular en este tiempo verbal...",
  "translation": null,
  "tone": "Muy bien"
}
```

**Code Reference**: `IMMERSION_MAP[3] = ('target', 'omit')`

---

## Implementation Details

### Code Locations

**Backend**:
```python
# backend/lang_policy.py:35-43
IMMERSION_MAP = {
    0: ('native', 'L2_to_L1'),
    1: ('native', 'on_demand'),
    2: ('bilingual', 'on_demand'),
    3: ('target', 'omit'),
}
```

**Database**:
```sql
-- supabase/sql/003_fix_immersion_levels.sql
ALTER TABLE user_settings
ADD CONSTRAINT user_settings_immersion_level_check
CHECK (immersion_level >= 0 AND immersion_level <= 3);
```

**Frontend**:
```tsx
// frontend/v0_lingua-log/app/(app)/settings/page.tsx:551-567
<Slider
  value={[settings.immersionLevel]}
  max={3}
  min={0}
  step={1}
/>
```

### Proficiency Mapping

Immersion levels correlate (but don't strictly map) to proficiency:

```python
# backend/prompt_builder.py:253-270
def _estimate_proficiency_level(effective: EffectiveSettings) -> str:
    if effective.immersion_level == 0:
        return "beginner"
    elif effective.immersion_level == 1:
        return "elementary"
    elif effective.immersion_level == 2:
        return "intermediate"
    else:  # 3
        return "advanced"
```

**Note**: This is a heuristic. A beginner could choose level 2, but it would be harder for them.

---

## User Scenarios (From Plan)

### Scenario A: Absolute Beginner
- **Profile**: Never studied Japanese
- **Settings**: UI=English, L1=English, L2=Japanese, Immersion=0
- **Behavior**: All explanations in English, always show JA→EN translation
- **Why**: Minimize cognitive load, constant L2↔L1 mapping

### Scenario B: Intermediate Learner
- **Profile**: B1-B2 in French
- **Settings**: UI=Spanish, L1=Spanish, L2=French, Immersion=1
- **Behavior**: Explanations in Spanish, translation hidden but available
- **Why**: Practice recall in L2, keep L1 safety net

### Scenario C: Advanced Polyglot
- **Profile**: C1 in Japanese and Arabic
- **Settings**: UI=German, L1=Spanish, L2=Japanese, Immersion=3
- **Behavior**: Everything in Japanese, no translations
- **Why**: Maximum immersion, think in L2

---

## Validation Rules

### Backend Validation (Pydantic)
```python
# backend/models.py
immersion_level: Optional[int] = Field(None, ge=0, le=3)
```

### Database Validation (PostgreSQL)
```sql
CHECK (immersion_level >= 0 AND immersion_level <= 3)
```

### Frontend Validation (React)
```tsx
<Slider max={3} min={0} step={1} />
```

**All three MUST match** - this was the bug we're fixing.

---

## Historical Note

**Previous System** (WRONG):
- Database allowed 1-5
- Backend had levels 0-5 (6 levels)
- Frontend showed 0-3 (4 levels)
- **Result**: Level 0 was rejected by database, levels 4-5 were unreachable

**Current System** (CORRECT):
- All three layers standardized to 0-3
- Matches original plan specification
- 4 distinct immersion behaviors

---

## Future Considerations

**Do NOT add new levels without:**
1. Updating database constraint
2. Updating IMMERSION_MAP
3. Updating frontend slider
4. Updating this documentation
5. Considering if it's actually needed (4 levels covers most use cases)

**Alternative to adding levels:**
- Use other settings (strictness, formality) to fine-tune
- Levels 0-3 provide the skeleton, other settings add nuance

---

## Testing

**Test all 4 levels:**
```python
# backend/tests/test_lang_policy.py
def test_immersion_level_0_native_first()
def test_immersion_level_1_guided_bilingual()
def test_immersion_level_2_balanced()
def test_immersion_level_3_full_immersion()
```

**Test edge cases:**
- Invalid level (-1, 4, 10) → Should fail validation
- Switching levels mid-learning → Should apply to new entries only
- Snapshots preserve level → Old entries keep original level

---

## References

- **Plan Specification**: `MULTI_LINGUAL_PROBLEM.md:23-29`
- **Analysis**: `MULTILINGUAL_ANALYSIS.md:54-99`
- **Code**: `backend/lang_policy.py:35-43`
- **Migration**: `supabase/sql/003_fix_immersion_levels.sql`
- **Tests**: `backend/tests/test_lang_policy.py`

---

**Last Verified**: 2025-01-05
**Status**: ✅ Canonical - Do not create conflicting documentation

# 🌍 Complete Translation Audit & Fix Process

## Overview
This document provides a systematic approach to identify and fix untranslated content in a React/Next.js application with i18next internationalization. Follow these steps in order to ensure comprehensive translation coverage.

## Prerequisites
- Working React/Next.js app with i18next setup
- Translation resources in `i18n/i18n.ts` or similar
- Browser/testing environment available
- Access to edit translation files

---

## 🔍 **Phase 1: Setup & Initial Assessment**

### Step 1: Set Language to Non-English
**Why:** Makes untranslated keys stand out visually
**Action:**
1. Navigate to language switcher in app
2. Select Spanish/Arabic/any non-English language
3. Note: Untranslated content will appear as English or camelCase keys

### Step 2: Identify Target Pages for Audit
**Common high-priority pages:**
- Authentication pages (sign-in, sign-up)
- Main navigation/dashboard
- Content creation forms (new entry, compose)
- Settings/preferences
- User profile
- Data display pages (lists, stats)

---

## 🔧 **Phase 2: Systematic Page Audit**

### Step 3: For Each Target Page

#### 3.1 Navigate to Page
```
Open page in browser with non-English language selected
```

#### 3.2 Identify Untranslated Content
**Look for:**
- English text in a Spanish/other language interface
- camelCase strings (e.g., `userName`, `targetLanguage`)
- Raw translation keys (e.g., `auth.signIn`, `common.loading`)
- Mixed language content
- Form labels, buttons, placeholders
- Error messages
- Tooltips and help text

#### 3.3 Document Issues
**For each untranslated item, record:**
- Exact text displayed (e.g., `"signInWithPassword"`)
- Page location (e.g., Sign-in page header)
- Component context (e.g., button text, form label)
- Expected translation namespace (e.g., `auth`, `journal`, `settings`)

### Step 4: Check Interactive Elements
**Don't forget:**
- Dropdown options
- Collapsible/expandable sections
- Modal dialogs
- Toast notifications
- Form validation messages
- Loading states
- Empty states

---

## 🛠 **Phase 3: Translation Resource Updates**

### Step 5: Analyze Translation Keys Needed

#### 5.1 Determine Namespace
**Common namespaces:**
- `auth` - Authentication, sign-in, registration
- `common` - Shared UI elements, navigation, buttons
- `journal` - Content creation, writing interface
- `settings` - Configuration, preferences
- `feedback` - AI responses, scores, suggestions
- `vocabulary` - Word lists, learning content
- `stats` - Analytics, progress tracking

#### 5.2 Create Key Names
**Naming conventions:**
- Use camelCase: `targetLanguage`, `advancedOptions`
- Be descriptive: `submitAndAnalyze` not `submit`
- Include context: `emailRequired` not `required`
- For descriptions: add `Desc` suffix: `immersionLevelDesc`

### Step 6: Add English Translations

#### 6.1 Locate Translation File
```typescript
// File: i18n/i18n.ts
const resources = {
  en: {
    namespace: {
      // Add keys here
    }
  }
}
```

#### 6.2 Add Missing Keys
```typescript
// Example: Adding journal namespace keys
journal: {
  // Existing keys...
  targetLanguage: 'Target Language',
  wordCount: 'Word Count',
  submitAndAnalyze: 'Submit and Analyze',
  advancedOptions: 'Advanced Options',
  explanationMode: 'Explanation Mode',
  strictnessLevel: 'Strictness Level'
}
```

### Step 7: Add Non-English Translations

#### 7.1 Locate Target Language Section
```typescript
es: { // Spanish example
  namespace: {
    // Add corresponding translations
  }
}
```

#### 7.2 Provide Accurate Translations
```typescript
journal: {
  targetLanguage: 'Idioma Objetivo',
  wordCount: 'Recuento de Palabras', 
  submitAndAnalyze: 'Enviar y Analizar',
  advancedOptions: 'Opciones Avanzadas',
  explanationMode: 'Modo de Explicación',
  strictnessLevel: 'Nivel de Rigurosidad'
}
```

---

## ✅ **Phase 4: Verification & Testing**

### Step 8: Test Each Fixed Page

#### 8.1 Refresh Application
- Clear browser cache if needed
- Reload the page completely

#### 8.2 Verify Translations
**For each language:**
1. Switch to English - verify new keys show English text
2. Switch to target language - verify translations appear
3. Check that formatting/spacing looks correct
4. Verify special characters display properly

#### 8.3 Test Interactive Elements
- Click buttons with new translations
- Open dropdowns with translated options
- Test form submissions
- Verify error messages are translated

### Step 9: Edge Case Testing

#### 9.1 Pluralization
**Test with ICU format:**
```typescript
// Example: Test different counts
writingStreak: "You have {count, plural, =0 {no} one {# day} other {# days}} streak"
```

#### 9.2 Interpolation
**Test dynamic values:**
```typescript
// Example: Test with different languages
writeThoughtsIn: 'Write your thoughts in {language}...'
```

#### 9.3 Fallback Behavior
- Test with missing keys (should fallback to English)
- Test with malformed translation files

---

## 🔍 **Phase 5: Component-Level Verification**

### Step 10: Check Component Implementation

#### 10.1 Verify t() Function Usage
**Common issues:**
- Component not importing `useLocale` or `useTranslation`
- Hardcoded strings instead of `t()` calls
- Incorrect namespace in `t()` calls

#### 10.2 Component Pattern Check
```typescript
// Correct usage:
import { useLocale } from '@/i18n/LocaleProvider'

export function MyComponent() {
  const { t } = useLocale()
  
  return (
    <button>{t('namespace.keyName')}</button>
  )
}
```

#### 10.3 Common Component Issues
- Missing `t()` wrapper around strings
- Wrong namespace reference
- Missing translation keys in resources

---

## 📋 **Phase 6: Comprehensive Page Coverage**

### Step 11: Systematic Page Checklist

**Authentication Flow:**
- [ ] Sign-in page
- [ ] Sign-up page  
- [ ] Password reset
- [ ] Email verification

**Main Application:**
- [ ] Dashboard/home page
- [ ] Navigation menus
- [ ] Content creation forms
- [ ] Content viewing/editing
- [ ] Search functionality
- [ ] Filters and sorting

**User Management:**
- [ ] Profile page
- [ ] Settings page (all tabs)
- [ ] Preferences
- [ ] Account management

**Data Display:**
- [ ] Lists and tables
- [ ] Statistics/analytics
- [ ] Charts and graphs
- [ ] Empty states
- [ ] Loading states

**Interactive Features:**
- [ ] Modals and dialogs
- [ ] Notifications/toasts
- [ ] Form validation
- [ ] Error pages (404, 500)

---

## 🚨 **Common Pitfalls & Solutions**

### Issue: Keys Not Resolving
**Symptoms:** Seeing raw keys like `auth.signIn`
**Solutions:**
1. Check namespace prefix in component: `t('auth.signIn')`
2. Verify key exists in translation resources
3. Ensure component imports translation hook

### Issue: Mixed Languages
**Symptoms:** Some English, some Spanish on same page
**Solutions:**
1. Check for hardcoded strings in components
2. Verify all `t()` calls use correct namespace
3. Clear browser cache and reload

### Issue: Formatting Problems
**Symptoms:** Text overflow, weird spacing
**Solutions:**
1. Keep translations similar length to original
2. Test with longest language variant
3. Adjust CSS if needed for longer text

### Issue: Missing Context
**Symptoms:** Generic translations that don't fit context
**Solutions:**
1. Use descriptive key names with context
2. Add separate keys for different contexts
3. Include comments in translation files

---

## 📝 **Phase 7: Documentation & Maintenance**

### Step 12: Document New Keys
**Create reference:**
- List all namespaces and their purpose
- Document key naming conventions
- Provide translation guidelines

### Step 13: Set Up Validation
**Add tools:**
- ESLint rules for hardcoded strings
- Translation key extraction tools
- Missing translation detection

### Step 14: Future Process
**Establish workflow:**
1. New features must include translation keys
2. Translation review in PR process
3. Regular translation audits
4. User testing with different languages

---

## 🎯 **Success Criteria**

**Audit is complete when:**
- [ ] All user-facing text uses `t()` function
- [ ] No raw translation keys visible in UI
- [ ] All major pages translated in target languages
- [ ] Interactive elements properly translated
- [ ] Edge cases (plurals, interpolation) work
- [ ] Fallback behavior functions correctly
- [ ] No layout issues with translated text
- [ ] User testing confirms good experience

---

## 📚 **Quick Reference**

### Translation Function Usage
```typescript
// Basic usage
t('namespace.key')

// With interpolation
t('namespace.greeting', { name: 'John' })

// With pluralization
t('namespace.items', { count: 5 })

// With fallback
t('namespace.key', { defaultValue: 'Fallback text' })
```

### Common Namespace Organization
```
auth/          - Authentication, login, registration
common/        - Shared UI, navigation, generic buttons
journal/       - Content creation, writing interface  
settings/      - Configuration, preferences
feedback/      - AI responses, scores, suggestions
vocabulary/    - Word learning, definitions
stats/         - Analytics, progress tracking
errors/        - Error messages, validation
```

### File Structure
```
i18n/
├── i18n.ts           # Main configuration & inline resources
├── LocaleProvider.tsx # React context provider
├── languages.ts      # Language definitions
├── rtl.ts           # RTL language helper
└── pseudo.ts        # Pseudolocalization utility
```

This process ensures systematic, thorough translation coverage while maintaining code quality and user experience.

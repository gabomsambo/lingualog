# Multilingual Documentation

This document explains the multilingual architecture and internationalization (i18n) implementation in LinguaLog.

## Table of Contents

1. [Overview](#overview)
2. [Three Language Roles](#three-language-roles)
3. [Immersion Mapping System](#immersion-mapping-system)
4. [Adding New Locales](#adding-new-locales)
5. [Development Tools](#development-tools)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## Overview

LinguaLog supports multiple languages through a comprehensive i18n system that handles:

- **UI Localization**: Interface language selection (English, Spanish, Arabic, etc.)
- **Target Language Learning**: Language being practiced/learned
- **Native Language Support**: User's first language for explanations
- **RTL Language Support**: Right-to-left text direction for Arabic, Hebrew, etc.
- **Pseudo-localization**: Testing tool for i18n implementation
- **Language Policy Resolution**: Dynamic language behavior based on user settings

## Three Language Roles

The multilingual system recognizes three distinct language roles:

### 1. UI Language (`uiLang`)

The language used for the application interface (menus, buttons, labels).

- **Current Support**: English (`en`), Spanish (`es`), Arabic (`ar`)
- **Storage**: Browser localStorage and user preferences
- **Fallback**: English for missing translations
- **Detection**: Browser language → user preference → English

```typescript
// Access UI language
const { uiLang, setUiLang } = useLocale()

// Format dates/numbers in UI language
const { formatDateMediumShort, formatNumberScore } = useLocale().intl
```

### 2. Native Language (L1)

The user's first/native language, used for AI explanations and help text.

- **Purpose**: Provides explanations and assistance in user's strongest language
- **Configuration**: Set in user settings
- **Default**: English
- **Usage**: AI feedback, error messages, help content

### 3. Target Language (L2)

The language the user is actively learning and practicing.

- **Purpose**: Language for journal entries and language learning content
- **Selection**: Per-entry via dropdown in journal composer
- **Default**: User's configured `default_target_lang`
- **Attributes**: Sets `lang` and `dir` attributes on text inputs

```typescript
// Journal composer sets target language
<Textarea
  lang={targetLanguage}
  dir={isRTL(targetLanguage) ? 'rtl' : 'ltr'}
  placeholder={t('journal.writeThoughtsIn', { language: getLanguageDisplayName(targetLanguage) })}
/>
```

## Immersion Mapping System

The immersion system dynamically adjusts AI behavior based on the user's proficiency level:

### Immersion Levels

| Level | Name | Description | Explanation Mode | Translation Policy |
|-------|------|-------------|------------------|-------------------|
| 0 | Native-First | Maximum L1 support for beginners | `native_only` | `L2_to_L1` |
| 1 | Guided Bilingual | Native explanations, on-demand translations | `native_only` | `on_demand` |
| 2 | Balanced | Bilingual explanations | `bilingual` | `on_demand` |
| 3 | Immersive | Target language focus | `target_only` | `omit` |

### Implementation

The mapping is defined in `backend/lang_policy.py`:

```python
IMMERSION_MAP = {
    0: ('native_only', 'L2_to_L1'),
    1: ('native_only', 'on_demand'),
    2: ('bilingual', 'on_demand'),
    3: ('target_only', 'omit'),
}
```

### Usage in Journal Composer

Users can override immersion settings per journal entry via the Advanced Options panel:

```typescript
// Override immersion level for specific entry
const submissionOverrides: JournalEntryOverrides = {
  target_language: targetLanguage,
  immersion_level: 3, // Immersive mode
  explanation_mode: 'target_only',
  translation_policy: 'omit'
}
```

## Adding New Locales

To add support for a new language (e.g., French `fr`):

### 1. Create Locale Files

Create JSON files for each namespace:

```bash
mkdir frontend/v0_lingua-log/locales/fr
touch frontend/v0_lingua-log/locales/fr/common.json
touch frontend/v0_lingua-log/locales/fr/auth.json
touch frontend/v0_lingua-log/locales/fr/journal.json
touch frontend/v0_lingua-log/locales/fr/settings.json
touch frontend/v0_lingua-log/locales/fr/feedback.json
```

### 2. Add Translations

Copy structure from English and translate:

```json
// frontend/v0_lingua-log/locales/fr/common.json
{
  "appTitle": "LinguaLog",
  "loading": "Chargement...",
  "save": "Enregistrer",
  "cancel": "Annuler",
  // ... more translations
}
```

### 3. Update Language Configuration

Add to the centralized language list:

```typescript
// frontend/v0_lingua-log/i18n/languages.ts
export const LANGUAGES: Language[] = [
  // ... existing languages
  { code: "fr", name: "French", flag: "🇫🇷", nativeName: "Français" },
]
```

### 4. Configure RTL Support (if needed)

For right-to-left languages, update the RTL helper:

```typescript
// frontend/v0_lingua-log/i18n/rtl.ts
export const RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur']
```

### 5. Enable Dynamic Loading

The LocaleProvider automatically handles lazy loading:

```typescript
// Automatic lazy loading when language is selected
await loadLocaleBundle('fr')
```

### 6. Add to UI Language Options

Update the UI language selector:

```typescript
// frontend/v0_lingua-log/i18n/languages.ts
export function getUILanguages(): Language[] {
  return LANGUAGES.filter(lang => ['en', 'es', 'fr'].includes(lang.code))
}
```

## Development Tools

### Pseudo-localization

Test i18n implementation by expanding and bracketing strings:

1. **Enable**: Add `?pseudo=1` to any URL
2. **Visual**: Strings appear as `[Ñéẇ Éñţŕÿ ẋẋẋ]`
3. **Purpose**: Identify untranslated strings and layout issues

```typescript
// Access pseudo mode
const { isPseudo } = useLocale()

// Toggle pseudo in dev tools
const url = new URL(window.location.href)
url.searchParams.set('pseudo', '1')
window.location.href = url.toString()
```

### Linting

Prevent hardcoded strings with ESLint:

```bash
# Check for literal string violations
npm run lint:i18n

# Extract translatable strings
npm run i18n:extract

# Check for missing translations
npm run i18n:check
```

### Dev Language Switcher

A floating dev widget for testing language switching:

- **Location**: Bottom-right corner in development
- **Features**: 
  - UI language switching
  - Pseudo-localization toggle
  - Current language display
  - Fallback testing

## Testing

### E2E Tests

Multilingual smoke tests verify core functionality:

```typescript
// Run multilingual tests
npx playwright test multilingual.spec.ts

// Test specific scenarios
npx playwright test --grep "Spanish UI language"
npx playwright test --grep "pseudo-localization"
npx playwright test --grep "RTL"
```

### Backend Tests

Language policy resolution is tested:

```python
# Run backend i18n tests
python -m pytest backend/tests/test_lang_policy.py

# Test specific immersion mapping
python -m pytest backend/tests/test_lang_policy.py::TestImmersionMapping::test_immersion_map_level_3_direct_validation
```

### Manual Testing Checklist

1. **Language Switching**:
   - [ ] UI language changes affect interface text
   - [ ] Missing translations fall back to English
   - [ ] Language preference persists across sessions

2. **RTL Support**:
   - [ ] Arabic selection sets `html dir="rtl"`
   - [ ] Text inputs have correct `lang` and `dir` attributes
   - [ ] Layout doesn't break with RTL content

3. **Pseudo-localization**:
   - [ ] `?pseudo=1` shows bracketed/expanded text
   - [ ] All translatable strings are affected
   - [ ] Toggle works correctly

4. **Target Language**:
   - [ ] Journal textarea gets correct `lang` attribute
   - [ ] RTL target languages set `dir="rtl"`
   - [ ] Language selection persists in form

## Troubleshooting

### Common Issues

**Missing Translations**: 
- Check if key exists in namespace JSON file
- Verify correct namespace is imported
- Confirm fallback to English works

**RTL Layout Issues**:
- Ensure `dir` attribute is set on container elements
- Check CSS doesn't override text direction
- Test with actual RTL content

**Pseudo-localization Not Working**:
- Verify `?pseudo=1` parameter in URL
- Check browser console for pseudo toggle state
- Ensure `isPseudoEnabled()` function works

**Language Not Loading**:
- Check network tab for failed locale bundle requests
- Verify JSON files have correct syntax
- Confirm language code matches file structure

### Debug Commands

```bash
# Check current language state
console.log(i18n.language)

# List loaded namespaces
console.log(i18n.options.ns)

# Check if key exists
console.log(i18n.exists('common.appTitle'))

# Force reload language
i18n.changeLanguage('es')
```

### Performance Considerations

- **Lazy Loading**: Locale bundles load on-demand
- **Bundle Size**: Keep translations concise
- **Caching**: Translations cached in browser
- **Fallbacks**: Minimize fallback chain depth

## Architecture Notes

### File Structure

```
frontend/v0_lingua-log/
├── i18n/
│   ├── i18n.ts              # i18next configuration
│   ├── LocaleProvider.tsx   # React context provider
│   ├── languages.ts         # Language definitions
│   ├── rtl.ts               # RTL language detection
│   ├── pseudo.ts            # Pseudo-localization utils
│   └── intl.ts              # Intl formatting functions
├── locales/
│   ├── en/                  # English translations
│   ├── es/                  # Spanish translations
│   └── ar/                  # Arabic translations
└── components/
    └── dev-language-switcher.tsx
```

### Backend Integration

```
backend/
├── lang_policy.py           # Language policy resolution
├── prompt_builder.py        # AI prompt construction
└── tests/
    └── test_lang_policy.py  # Language policy tests
```

### Key Dependencies

- **i18next**: Core i18n framework
- **react-i18next**: React integration
- **i18next-icu**: ICU MessageFormat support
- **i18next-browser-languagedetector**: Browser language detection
- **eslint-plugin-i18next**: Linting for hardcoded strings

## Best Practices

1. **Always use `t()` for user-facing strings**
2. **Provide meaningful translation keys**
3. **Test with pseudo-localization**
4. **Support RTL languages from the start**
5. **Keep translations concise and clear**
6. **Use ICU MessageFormat for complex pluralization**
7. **Test fallback behavior regularly**
8. **Consider cultural context in translations**

## Contributing

When adding new features:

1. Add i18n keys to English locale files first
2. Use semantic, descriptive key names
3. Test with pseudo-localization
4. Add at least Spanish translations for UI elements
5. Consider RTL implications for layout
6. Update this documentation for new patterns

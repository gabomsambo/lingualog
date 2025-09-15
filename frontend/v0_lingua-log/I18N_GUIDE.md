# i18n Linting & Pseudolocalization Guide

This guide explains how to use the i18n linting and pseudolocalization features to prevent hardcoded strings and catch missing translations.

## 🔍 ESLint i18n Rules

### Configuration
- **File**: `.eslintrc.js`
- **Plugin**: `eslint-plugin-i18next`
- **Rule**: `i18next/no-literal-string`

### What it catches:
```tsx
// ❌ BAD - Hardcoded strings in JSX
<h1>Welcome to our app</h1>
<button>Click me</button>
<p>This will trigger an ESLint error</p>

// ✅ GOOD - Using translation functions
<h1>{t('common.welcome')}</h1>
<button>{t('common.clickMe')}</button>
<p>{t('messages.example')}</p>
```

### Whitelisted files:
- Configuration files (`*.config.js`)
- Test files (`*.test.tsx`, `*.spec.tsx`)
- Utility files (`lib/utils.ts`, `lib/auth.ts`)
- UI components (`components/ui/**`)
- i18n files (`i18n/**`)
- Type definitions (`types/**`)

### NPM Scripts:
```bash
# Run i18n-specific linting
npm run lint:i18n

# Extract translation keys from code
npm run i18n:extract

# Check if translations are up to date
npm run i18n:check
```

## 🎭 Pseudolocalization

### What it does:
- Converts normal text to accented characters
- Adds padding with bullet points (•)
- Wraps text in brackets [like this]
- Makes hardcoded strings obvious
- Helps identify layout issues with longer text

### Examples:
```
Original: "Save"
Pseudo:   "[Sávé•]"

Original: "Welcome to our application"
Pseudo:   "[Wélçómé tó óúr áppliçátión••••••••]"
```

### Usage:

#### 1. URL Parameter Method:
Add `?pseudo=1` to any URL:
```
http://localhost:3000?pseudo=1
http://localhost:3000/dashboard?pseudo=1
```

#### 2. Dev Language Switcher:
- Look for the floating "DEV" panel in bottom-right corner
- Click "Enable Pseudo" button
- All translated text will become pseudolocalized

#### 3. Programmatic Usage:
```tsx
import { pseudo, isPseudoEnabled, tPseudo } from '@/i18n/pseudo'

// Direct pseudolocalization
const fakeText = pseudo("Hello World") // "[Hélló Wórld•••]"

// Check if pseudo mode is active
const isActive = isPseudoEnabled()

// Enhanced translation with auto-pseudo
const text = tPseudo(t, 'common.save') // Automatically pseudo if ?pseudo=1
```

## 🧪 Testing

### Test Component:
Check `components/test-i18n-lint.tsx` for examples of:
- ❌ Strings that should trigger ESLint errors
- ✅ Correct usage with translation functions

### Running Tests:
1. Enable pseudo mode: add `?pseudo=1` to URL
2. Switch languages using dev panel
3. Check that:
   - Translated text shows brackets and accents
   - Hardcoded strings remain normal (indicating missing translations)
   - Layout handles longer pseudolocalized text

## 📝 Best Practices

### 1. Use translation keys everywhere:
```tsx
// Instead of:
<button>Save</button>

// Use:
<button>{t('common.save')}</button>
```

### 2. Organize translation keys by namespace:
```tsx
t('common.save')        // General UI
t('auth.signIn')        // Authentication
t('journal.newEntry')   // Journal features
t('settings.language')  // Settings
t('feedback.excellent') // Feedback system
```

### 3. Handle pluralization:
```tsx
t('items', { count: items.length })
```

### 4. Regularly run linting:
```bash
npm run lint:i18n
```

### 5. Test with pseudolocalization:
- Always test new features with `?pseudo=1`
- Check layouts handle longer text
- Verify all text is properly translated

## 🚀 Workflow

1. **Development**: Write code using `t()` functions
2. **Linting**: Run `npm run lint:i18n` to catch hardcoded strings
3. **Testing**: Use `?pseudo=1` to verify all text is translated
4. **Extraction**: Run `npm run i18n:extract` to update locale files
5. **Review**: Check git diff for new/changed translation keys

## 🔧 Configuration Files

- `.eslintrc.js` - ESLint rules for catching hardcoded strings
- `i18next-parser.config.js` - Key extraction configuration
- `i18n/pseudo.ts` - Pseudolocalization utility
- `i18n/LocaleProvider.tsx` - Enhanced with pseudo support

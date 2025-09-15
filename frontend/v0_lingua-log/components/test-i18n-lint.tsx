'use client'

import { useLocale } from '@/i18n/LocaleProvider'

// This component demonstrates ESLint i18n rule violations
// These hardcoded strings should trigger linting errors:

export function TestI18nLint() {
  const { t } = useLocale()

  return (
    <div className="p-4 space-y-4">
      {/* ❌ This should trigger ESLint error - hardcoded string */}
      <h1>Welcome to our app</h1>
      
      {/* ❌ This should trigger ESLint error - hardcoded string */}
      <p>This is a hardcoded message that should be flagged by ESLint</p>
      
      {/* ❌ This should trigger ESLint error - hardcoded button text */}
      <button className="px-4 py-2 bg-blue-500 text-white rounded">
        Click me
      </button>
      
      {/* ✅ This is correct - using translation function */}
      <h2>{t('common.appTitle')}</h2>
      
      {/* ✅ This is correct - using translation function */}
      <p>{t('common.loading')}</p>
      
      {/* ✅ This is correct - using translation function */}
      <button className="px-4 py-2 bg-green-500 text-white rounded">
        {t('common.save')}
      </button>
      
      {/* ❌ This should trigger ESLint error - mixed content */}
      <div>
        {t('common.appTitle')} - Additional hardcoded text
      </div>
    </div>
  )
}

'use client'

import { useLocale } from '@/i18n/LocaleProvider'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { isPseudoEnabled } from '@/i18n/pseudo'

// Available languages for testing
const AVAILABLE_LANGUAGES = [
  { code: 'en', label: 'English', flag: '🇺🇸' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
  { code: 'es-ES', label: 'Español (España)', flag: '🇪🇸' },
  { code: 'ar', label: 'العربية', flag: '🇸🇦' },
  { code: 'he', label: 'עברית', flag: '🇮🇱' }
]

export function DevLanguageSwitcher() {
  const { uiLang, setUiLang, t, isPseudo } = useLocale()

  // Only show in development
  if (process.env.NODE_ENV !== 'development') {
    return null
  }

  const handleLanguageChange = async (langCode: string) => {
    await setUiLang(langCode)
  }

  const togglePseudo = () => {
    const url = new URL(window.location.href)
    if (isPseudoEnabled()) {
      url.searchParams.delete('pseudo')
    } else {
      url.searchParams.set('pseudo', '1')
    }
    window.location.href = url.toString()
  }

  const currentLang = AVAILABLE_LANGUAGES.find(lang => lang.code === uiLang) || AVAILABLE_LANGUAGES[0]

  return (
    <div className="fixed bottom-4 right-4 z-50 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700" data-testid="dev-language-switcher">
      <div className="flex items-center gap-2 mb-2">
        <Badge variant="outline" className="text-xs">
          DEV
        </Badge>
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
          Language Switcher
        </span>
      </div>
      
      <Select value={uiLang} onValueChange={handleLanguageChange}>
        <SelectTrigger className="w-48">
          <SelectValue>
            <div className="flex items-center gap-2">
              <span>{currentLang.flag}</span>
              <span>{currentLang.label}</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {AVAILABLE_LANGUAGES.map((lang) => (
            <SelectItem key={lang.code} value={lang.code}>
              <div className="flex items-center gap-2">
                <span>{lang.flag}</span>
                <span>{lang.label}</span>
                <span className="text-xs text-gray-400">({lang.code})</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      
      <div className="mt-2 space-y-2">
        <Button
          onClick={togglePseudo}
          size="sm"
          variant={isPseudo ? "default" : "outline"}
          className="w-full"
        >
{isPseudo ? "Disable Pseudo" : "Enable Pseudo"}
        </Button>
        
        <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
          <div>Current: {uiLang}</div>
          <div>Dir: {typeof window !== 'undefined' ? document?.documentElement?.dir || 'ltr' : 'ltr'}</div>
          <div>Pseudo: {isPseudo ? 'ON' : 'OFF'}</div>
        </div>
        
        {/* Demo translated text */}
        <div className="text-xs border-t pt-2">
          <div className="font-medium mb-1">Demo:</div>
          <div>{t('common.appTitle')}</div>
          <div>{t('common.save')}</div>
          <div className="text-red-500">Fallback test: {t('common.testFallbackKey')}</div>
        </div>
      </div>
    </div>
  )
}

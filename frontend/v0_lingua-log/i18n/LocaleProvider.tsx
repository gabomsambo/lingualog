'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { isRTL } from './rtl'
import { isPseudoEnabled, tPseudo } from './pseudo'
import { createIntlFormatters } from './intl'
import i18n from './i18n'

interface LocaleContextType {
  uiLang: string
  setUiLang: (lang: string) => Promise<void>
  t: (key: string, options?: any) => string
  isPseudo: boolean
  intl: ReturnType<typeof createIntlFormatters>
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined)

interface LocaleProviderProps {
  children: ReactNode
}

// Cache for loaded locales to avoid duplicate imports
const loadedLocales = new Set<string>()

// Function to dynamically import locale bundles
async function loadLocaleBundle(lang: string): Promise<void> {
  // Extract base language (e.g., 'es' from 'es-ES')
  const baseLang = lang.split('-')[0]
  
  if (loadedLocales.has(baseLang) || !i18n) {
    return // Already loaded or i18n not available
  }

  try {
    // Load all namespace files for the language
    const namespaces = ['common', 'auth', 'journal', 'settings', 'feedback']
    
    const loadPromises = namespaces.map(async (ns) => {
      try {
        const module = await import(`../locales/${baseLang}/${ns}.json`)
        i18n.addResourceBundle(baseLang, ns, module.default, true, true)
      } catch (error) {
        console.warn(`Failed to load ${baseLang}/${ns}.json:`, error)
        // Fallback to English if locale file doesn't exist
        if (baseLang !== 'en') {
          const enModule = await import(`../locales/en/${ns}.json`)
          i18n.addResourceBundle(baseLang, ns, enModule.default, true, true)
        }
      }
    })

    await Promise.all(loadPromises)
    loadedLocales.add(baseLang)
    console.log(`Loaded locale bundle for: ${baseLang}`)
  } catch (error) {
    console.error(`Failed to load locale bundle for ${lang}:`, error)
  }
}

// Get default language based on resolution order
function getDefaultLanguage(): string {
  if (typeof window === 'undefined') {
    return 'en' // Server-side fallback
  }

  // 1. User setting (from localStorage)
  const savedLang = localStorage.getItem('uiLang')
  if (savedLang) return savedLang

  // 2. Navigator languages
  if (navigator.languages && navigator.languages.length > 0) {
    // Find first supported language
    for (const lang of navigator.languages) {
      const baseLang = lang.split('-')[0]
      if (['en', 'es', 'ar', 'he'].includes(baseLang)) {
        return lang
      }
    }
  }

  // 3. Fallback to English
  return 'en'
}

export function LocaleProvider({ children }: LocaleProviderProps) {
  const { t: originalT } = useTranslation()
  const [uiLang, setUiLangState] = useState<string>('en')
  const [mounted, setMounted] = useState(false)
  const [isPseudo, setIsPseudo] = useState(false)

  // Set mounted state on client and check for pseudo mode
  useEffect(() => {
    setMounted(true)
    const defaultLang = getDefaultLanguage()
    setUiLangState(defaultLang)
    setIsPseudo(isPseudoEnabled())
    
    // Listen for URL changes to update pseudo mode
    const handleLocationChange = () => {
      setIsPseudo(isPseudoEnabled())
    }
    
    window.addEventListener('popstate', handleLocationChange)
    return () => window.removeEventListener('popstate', handleLocationChange)
  }, [])

  // Update document lang and dir attributes
  useEffect(() => {
    if (mounted && typeof document !== 'undefined') {
      const baseLang = uiLang.split('-')[0]
      document.documentElement.lang = uiLang
      document.documentElement.dir = isRTL(baseLang) ? 'rtl' : 'ltr'
    }
  }, [uiLang, mounted])

  // Initialize with default language when mounted
  useEffect(() => {
    if (!mounted) return

    const initializeLanguage = async () => {
      const defaultLang = getDefaultLanguage()
      // Temporarily disable external bundle loading - using inline resources
      // await loadLocaleBundle(defaultLang)
      await i18n.changeLanguage(defaultLang.split('-')[0])
      setUiLangState(defaultLang)
    }

    initializeLanguage()
  }, [mounted])

  const setUiLang = async (lang: string): Promise<void> => {
    try {
      // Temporarily disable external bundle loading - using inline resources
      // await loadLocaleBundle(lang)
      
      // Change i18n language (only on client side)
      if (i18n) {
        const baseLang = lang.split('-')[0]
        await i18n.changeLanguage(baseLang)
      }
      
      // Update state
      setUiLangState(lang)
      
      // Save to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('uiLang', lang)
      }
      
      console.log(`Language changed to: ${lang}`)
    } catch (error) {
      console.error(`Failed to change language to ${lang}:`, error)
    }
  }

  // Enhanced translation function with pseudolocalization support
  const t = (key: string, options?: any): string => {
    // Handle namespace prefix: convert 'common.appTitle' to 'appTitle' with ns: 'common'
    let translationKey = key
    let namespace = 'common' // default
    
    if (key.includes('.')) {
      const [ns, k] = key.split('.', 2)
      namespace = ns
      translationKey = k
    }
    
    // Create enhanced originalT that handles namespaces correctly
    const enhancedT = (k: string, opts?: any) => {
      return originalT(k, { ...opts, ns: namespace })
    }
    
    return tPseudo(enhancedT, translationKey, options)
  }

  const contextValue: LocaleContextType = {
    uiLang,
    setUiLang,
    t,
    isPseudo,
    intl: createIntlFormatters(uiLang.split('-')[0])
  }

  return (
    <LocaleContext.Provider value={contextValue}>
      {children}
    </LocaleContext.Provider>
  )
}

export function useLocale(): LocaleContextType {
  const context = useContext(LocaleContext)
  if (context === undefined) {
    throw new Error('useLocale must be used within a LocaleProvider')
  }
  return context
}

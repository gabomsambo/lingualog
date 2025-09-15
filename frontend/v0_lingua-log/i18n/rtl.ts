/**
 * Helper function to determine if a language tag represents a right-to-left language
 * @param tag - Language tag (e.g., 'ar', 'he', 'fa', 'ur')
 * @returns true if the language is RTL, false otherwise
 */
export function isRTL(tag: string): boolean {
  const rtlLanguages = ['ar', 'he', 'fa', 'ur']
  
  // Extract the base language code (before any dash or underscore)
  const baseLanguage = tag.toLowerCase().split(/[-_]/)[0]
  
  return rtlLanguages.includes(baseLanguage)
}

/**
 * Get text direction for a given language tag
 * @param tag - Language tag
 * @returns 'rtl' or 'ltr'
 */
export function getTextDirection(tag: string): 'rtl' | 'ltr' {
  return isRTL(tag) ? 'rtl' : 'ltr'
}

/**
 * RTL languages supported by the application
 */
export const RTL_LANGUAGES = {
  ar: 'Arabic',
  he: 'Hebrew', 
  fa: 'Persian/Farsi',
  ur: 'Urdu'
} as const

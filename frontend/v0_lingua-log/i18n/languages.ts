/**
 * Centralized language definitions and utilities
 * This file contains all language mappings to avoid duplication across components
 */

export interface Language {
  code: string
  name: string
  flag: string
  nativeName?: string
}

/**
 * Complete language list with codes, English names, flags, and native names
 */
export const LANGUAGES: Language[] = [
  { code: "en", name: "English", flag: "🇺🇸", nativeName: "English" },
  { code: "es", name: "Spanish", flag: "🇪🇸", nativeName: "Español" },
  { code: "fr", name: "French", flag: "🇫🇷", nativeName: "Français" },
  { code: "de", name: "German", flag: "🇩🇪", nativeName: "Deutsch" },
  { code: "it", name: "Italian", flag: "🇮🇹", nativeName: "Italiano" },
  { code: "pt", name: "Portuguese", flag: "🇵🇹", nativeName: "Português" },
  { code: "ja", name: "Japanese", flag: "🇯🇵", nativeName: "日本語" },
  { code: "ko", name: "Korean", flag: "🇰🇷", nativeName: "한국어" },
  { code: "zh", name: "Chinese", flag: "🇨🇳", nativeName: "中文" },
  { code: "ru", name: "Russian", flag: "🇷🇺", nativeName: "Русский" },
  { code: "ar", name: "Arabic", flag: "🇸🇦", nativeName: "العربية" },
  { code: "hi", name: "Hindi", flag: "🇮🇳", nativeName: "हिन्दी" },
  { code: "th", name: "Thai", flag: "🇹🇭", nativeName: "ไทย" },
  { code: "vi", name: "Vietnamese", flag: "🇻🇳", nativeName: "Tiếng Việt" },
  { code: "nl", name: "Dutch", flag: "🇳🇱", nativeName: "Nederlands" },
  { code: "sv", name: "Swedish", flag: "🇸🇪", nativeName: "Svenska" },
  { code: "da", name: "Danish", flag: "🇩🇰", nativeName: "Dansk" },
  { code: "no", name: "Norwegian", flag: "🇳🇴", nativeName: "Norsk" },
  { code: "fi", name: "Finnish", flag: "🇫🇮", nativeName: "Suomi" },
  { code: "pl", name: "Polish", flag: "🇵🇱", nativeName: "Polski" },
]

/**
 * Get language by code
 */
export function getLanguageByCode(code: string): Language | undefined {
  return LANGUAGES.find(lang => lang.code === code)
}

/**
 * Get display name for a language code
 */
export function getLanguageDisplayName(code: string): string {
  const lang = getLanguageByCode(code)
  return lang ? lang.name : code
}

/**
 * Get native name for a language code
 */
export function getLanguageNativeName(code: string): string {
  const lang = getLanguageByCode(code)
  return lang ? (lang.nativeName || lang.name) : code
}

/**
 * Get flag emoji for a language code
 */
export function getLanguageFlag(code: string): string {
  const lang = getLanguageByCode(code)
  return lang ? lang.flag : '🌐'
}

/**
 * Get languages available for the UI (currently supported)
 */
export function getUILanguages(): Language[] {
  return LANGUAGES.filter(lang => ['en', 'es'].includes(lang.code))
}

/**
 * Get languages available for learning (target languages)
 */
export function getTargetLanguages(): Language[] {
  return LANGUAGES.filter(lang => !['en'].includes(lang.code)) // All except English for English speakers
}

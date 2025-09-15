/**
 * Pseudolocalization utility for identifying missing translations and layout issues
 */

// Character mappings for pseudolocalization
const PSEUDO_CHARS: Record<string, string> = {
  'a': 'á',
  'A': 'Á',
  'e': 'é',
  'E': 'É',
  'i': 'í',
  'I': 'Í',
  'o': 'ó',
  'O': 'Ó',
  'u': 'ú',
  'U': 'Ú',
  'c': 'ç',
  'C': 'Ç',
  'n': 'ñ',
  'N': 'Ñ',
  's': 'š',
  'S': 'Š',
  'z': 'ž',
  'Z': 'Ž'
}

/**
 * Apply pseudolocalization to a string
 * - Wraps text in brackets to make it visually distinct
 * - Replaces some ASCII characters with accented versions
 * - Adds padding to simulate longer translations
 * - Helps identify hardcoded strings and layout issues
 * 
 * @param str - The input string to pseudolocalize
 * @returns Pseudolocalized string with brackets and accented characters
 */
export function pseudo(str: string): string {
  if (!str || typeof str !== 'string') {
    return str
  }

  // Don't pseudolocalize strings that are already pseudolocalized
  if (str.startsWith('[') && str.endsWith(']')) {
    return str
  }

  // Don't pseudolocalize very short strings (likely identifiers)
  if (str.length <= 2) {
    return `[${str}]`
  }

  // Don't pseudolocalize strings that look like data/IDs
  if (/^[A-Z0-9_-]+$/i.test(str.trim())) {
    return str
  }

  // Don't pseudolocalize URLs or email addresses
  if (str.includes('http') || str.includes('@') || str.includes('www.')) {
    return str
  }

  // Apply character substitutions
  let pseudoStr = str
  for (const [ascii, accented] of Object.entries(PSEUDO_CHARS)) {
    pseudoStr = pseudoStr.replace(new RegExp(ascii, 'g'), accented)
  }

  // Add padding (approximately 30% longer to simulate common translation expansion)
  const padding = Math.max(1, Math.floor(pseudoStr.length * 0.3))
  const paddingStr = '•'.repeat(padding)

  // Wrap in brackets with padding
  return `[${pseudoStr}${paddingStr}]`
}

/**
 * Check if pseudolocalization is enabled based on URL parameters
 * @returns true if pseudo mode is active
 */
export function isPseudoEnabled(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  const urlParams = new URLSearchParams(window.location.search)
  return urlParams.get('pseudo') === '1'
}

/**
 * Enhanced translation function that applies pseudolocalization when enabled
 * This can be used as a wrapper around the standard t() function
 * 
 * @param translationFn - The original translation function
 * @param key - Translation key
 * @param options - Translation options
 * @returns Translated string, pseudolocalized if enabled
 */
export function tPseudo(
  translationFn: (key: string, options?: any) => string,
  key: string,
  options?: any
): string {
  const translated = translationFn(key, options)
  
  if (isPseudoEnabled()) {
    return pseudo(translated)
  }
  
  return translated
}

/**
 * Pseudolocalize all text content in an object (for bulk processing)
 * Useful for pseudolocalizing entire translation objects
 * 
 * @param obj - Object containing translation strings
 * @returns Object with pseudolocalized strings
 */
export function pseudoObject(obj: any): any {
  if (typeof obj === 'string') {
    return pseudo(obj)
  }
  
  if (Array.isArray(obj)) {
    return obj.map(pseudoObject)
  }
  
  if (obj && typeof obj === 'object') {
    const result: any = {}
    for (const [key, value] of Object.entries(obj)) {
      result[key] = pseudoObject(value)
    }
    return result
  }
  
  return obj
}

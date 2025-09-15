/**
 * Internationalization utilities using native Intl APIs
 * Provides locale-aware formatting for numbers, dates, and other data types
 */

/**
 * Format numbers with locale-specific formatting
 * @param value - Number to format
 * @param locale - Locale code (e.g., 'en', 'es', 'ar')
 * @param options - Intl.NumberFormat options
 * @returns Formatted number string
 */
export function formatNumber(
  value: number,
  locale: string,
  options?: Intl.NumberFormatOptions
): string {
  try {
    return new Intl.NumberFormat(locale, options).format(value)
  } catch (error) {
    // Fallback to English if locale is not supported
    return new Intl.NumberFormat('en', options).format(value)
  }
}

/**
 * Format dates with locale-specific formatting
 * @param date - Date to format
 * @param locale - Locale code (e.g., 'en', 'es', 'ar')
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date string
 */
export function formatDate(
  date: Date,
  locale: string,
  options?: Intl.DateTimeFormatOptions
): string {
  try {
    return new Intl.DateTimeFormat(locale, options).format(date)
  } catch (error) {
    // Fallback to English if locale is not supported
    return new Intl.DateTimeFormat('en', options).format(date)
  }
}

/**
 * Format relative time (e.g., "2 days ago", "in 3 hours")
 * @param value - Number of units
 * @param unit - Time unit
 * @param locale - Locale code
 * @returns Formatted relative time string
 */
export function formatRelativeTime(
  value: number,
  unit: Intl.RelativeTimeFormatUnit,
  locale: string
): string {
  try {
    const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
    return rtf.format(value, unit)
  } catch (error) {
    // Fallback to English if locale is not supported
    const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
    return rtf.format(value, unit)
  }
}

/**
 * Format currency with locale-specific formatting
 * @param amount - Amount to format
 * @param currency - Currency code (e.g., 'USD', 'EUR')
 * @param locale - Locale code
 * @returns Formatted currency string
 */
export function formatCurrency(
  amount: number,
  currency: string,
  locale: string
): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency
    }).format(amount)
  } catch (error) {
    // Fallback to English if locale is not supported
    return new Intl.NumberFormat('en', {
      style: 'currency',
      currency: currency
    }).format(amount)
  }
}

/**
 * Format percentages with locale-specific formatting
 * @param value - Number to format as percentage (0.5 = 50%)
 * @param locale - Locale code
 * @param options - Additional NumberFormat options
 * @returns Formatted percentage string
 */
export function formatPercentage(
  value: number,
  locale: string,
  options?: Intl.NumberFormatOptions
): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: 'percent',
      ...options
    }).format(value)
  } catch (error) {
    // Fallback to English if locale is not supported
    return new Intl.NumberFormat('en', {
      style: 'percent',
      ...options
    }).format(value)
  }
}

/**
 * Format lists with locale-specific formatting
 * @param items - Array of items to format
 * @param locale - Locale code
 * @param options - Intl.ListFormat options
 * @returns Formatted list string
 */
export function formatList(
  items: string[],
  locale: string,
  options?: Intl.ListFormatOptions
): string {
  try {
    return new Intl.ListFormat(locale, options).format(items)
  } catch (error) {
    // Fallback to English if locale is not supported
    return new Intl.ListFormat('en', options).format(items)
  }
}

/**
 * Format time duration in a human-readable way
 * @param seconds - Duration in seconds
 * @param locale - Locale code
 * @returns Formatted duration string
 */
export function formatDuration(seconds: number, locale: string): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60

  try {
    const rtf = new Intl.RelativeTimeFormat(locale, { style: 'narrow' })
    
    if (hours > 0) {
      return formatNumber(hours, locale) + 'h ' + formatNumber(minutes, locale) + 'm'
    } else if (minutes > 0) {
      return formatNumber(minutes, locale) + 'm ' + formatNumber(remainingSeconds, locale) + 's'
    } else {
      return formatNumber(remainingSeconds, locale) + 's'
    }
  } catch (error) {
    // Simple fallback
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    } else {
      return `${remainingSeconds}s`
    }
  }
}

/**
 * Specific formatting functions as mentioned in instructions
 */

/**
 * Format dates with medium date style and short time style as per instructions
 * @param date - Date to format
 * @param uiLang - UI language from LocaleProvider
 * @returns Formatted date string
 */
export function formatDateMediumShort(date: Date, uiLang: string): string {
  return new Intl.DateTimeFormat(uiLang, { 
    dateStyle: 'medium', 
    timeStyle: 'short' 
  }).format(date)
}

/**
 * Format numbers/scores as per instructions
 * @param n - Number to format
 * @param uiLang - UI language from LocaleProvider
 * @returns Formatted number string
 */
export function formatNumberScore(n: number, uiLang: string): string {
  return new Intl.NumberFormat(uiLang).format(n)
}

/**
 * Hook to get formatting functions for the current locale
 * @param locale - Current locale from useLocale
 * @returns Object with formatting functions bound to current locale
 */
export function createIntlFormatters(locale: string) {
  return {
    formatNumber: (value: number, options?: Intl.NumberFormatOptions) => 
      formatNumber(value, locale, options),
    
    formatDate: (date: Date, options?: Intl.DateTimeFormatOptions) => 
      formatDate(date, locale, options),
    
    formatRelativeTime: (value: number, unit: Intl.RelativeTimeFormatUnit) => 
      formatRelativeTime(value, unit, locale),
    
    formatCurrency: (amount: number, currency: string) => 
      formatCurrency(amount, currency, locale),
    
    formatPercentage: (value: number, options?: Intl.NumberFormatOptions) => 
      formatPercentage(value, locale, options),
    
    formatList: (items: string[], options?: Intl.ListFormatOptions) => 
      formatList(items, locale, options),
    
    formatDuration: (seconds: number) => 
      formatDuration(seconds, locale),

    // Add the specific formatters from instructions
    formatDateMediumShort: (date: Date) => 
      formatDateMediumShort(date, locale),
    
    formatNumberScore: (n: number) => 
      formatNumberScore(n, locale)
  }
}

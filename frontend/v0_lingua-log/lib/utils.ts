import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string, locale: string = 'en') {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date)
}

export function getLanguageEmoji(language?: string): string {
  if (!language) return "📝"; // Default emoji
  const lowerLang = language.toLowerCase();
  if (lowerLang.includes("english")) return "🇬🇧";
  if (lowerLang.includes("spanish")) return "🇪🇸";
  if (lowerLang.includes("french")) return "🇫🇷";
  if (lowerLang.includes("german")) return "🇩🇪";
  if (lowerLang.includes("japanese")) return "🇯🇵";
  if (lowerLang.includes("italian")) return "🇮🇹";
  if (lowerLang.includes("korean")) return "🇰🇷";
  // Add more languages and their emojis as needed
  return "📝"; // Default for other languages
}

export function getDisplayTitle(title?: string, originalText?: string): string {
  if (title && title.trim() !== "") {
    return title;
  }
  if (originalText) {
    // Create a title from the first few words of the original text
    const words = originalText.trim().split(/\s+/);
    return words.slice(0, 5).join(" ") + (words.length > 5 ? "..." : "");
  }
  return "Untitled Entry"; // This should be i18n but utils is used without context
}

export function getExcerpt(text?: string, maxLength: number = 100): string {
  if (!text) return "";
  if (text.length <= maxLength) {
    return text;
  }
  return text.substring(0, maxLength).trim() + "...";
}

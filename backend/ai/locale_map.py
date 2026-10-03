"""Map LinguaLog ISO language codes to Lara full locale tags."""

from typing import Optional

# Lara expects locales like es-ES, en-US, ja-JP
ISO_TO_LARA_LOCALE: dict[str, str] = {
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "pt": "pt-PT",
    "ru": "ru-RU",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "zh": "zh-CN",
    "ar": "ar-SA",
    "he": "he-IL",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "tr": "tr-TR",
    "sv": "sv-SE",
    "da": "da-DK",
    "nb": "nb-NO",
    "fi": "fi-FI",
    "hi": "hi-IN",
}


def to_lara_locale(code: Optional[str], default: str = "en-US") -> str:
    if not code:
        return default
    normalized = code.strip()
    if "-" in normalized:
        return normalized
    base = normalized.lower()[:2]
    return ISO_TO_LARA_LOCALE.get(base, default)

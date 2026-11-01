"""Closed error-tag vocabularies used by journal feedback and its statistics."""

from typing import Literal


ErrorType = Literal[
    "agreement",
    "gender_agreement",
    "number_agreement",
    "case",
    "ser_estar",
    "gustar",
    "verb_conjugation",
    "verb_aspect",
    "tense_choice",
    "article",
    "preposition",
    "por_para",
    "postposition",
    "word_order",
    "accent_spelling",
    "capitalization",
    "spelling",
    "particle",
    "classifier",
    "aspect_marker",
    "vocabulary_choice",
    "other",
]

ERROR_TYPE_VALUES = frozenset(ErrorType.__args__)

_COMMON_ROMANCE = (
    "gender_agreement", "number_agreement", "verb_conjugation", "tense_choice",
    "article", "preposition", "word_order", "accent_spelling", "vocabulary_choice", "other",
)

ERROR_TYPES_BY_FAMILY: dict[str, tuple[ErrorType, ...]] = {
    "spanish": (
        "gender_agreement", "number_agreement", "ser_estar", "gustar", "verb_conjugation",
        "tense_choice", "article", "preposition", "por_para", "word_order",
        "accent_spelling", "vocabulary_choice", "other",
    ),
    "romance": _COMMON_ROMANCE,
    "germanic": (
        "gender_agreement", "number_agreement", "verb_conjugation", "tense_choice", "article",
        "preposition", "word_order", "capitalization", "spelling", "vocabulary_choice", "other",
    ),
    "slavic": (
        "gender_agreement", "number_agreement", "case", "verb_aspect", "verb_conjugation",
        "tense_choice", "preposition", "word_order", "spelling", "vocabulary_choice", "other",
    ),
    "east_asian": (
        "particle", "classifier", "aspect_marker", "verb_conjugation", "tense_choice",
        "word_order", "spelling", "vocabulary_choice", "other",
    ),
    "southeast_asian": (
        "particle", "classifier", "aspect_marker", "word_order", "spelling", "vocabulary_choice",
        "other",
    ),
    "semitic": (
        "agreement", "gender_agreement", "number_agreement", "verb_conjugation", "tense_choice",
        "article", "preposition", "word_order", "spelling", "vocabulary_choice", "other",
    ),
    "indo_aryan": (
        "gender_agreement", "number_agreement", "case", "verb_conjugation", "tense_choice",
        "postposition", "word_order", "spelling", "vocabulary_choice", "other",
    ),
    "general": (
        "agreement", "verb_conjugation", "tense_choice", "article", "preposition", "word_order",
        "spelling", "vocabulary_choice", "other",
    ),
}

LANGUAGE_FAMILY_BY_CODE = {
    "es": "spanish",
    "fr": "romance", "it": "romance", "pt": "romance",
    "en": "germanic", "de": "germanic", "nl": "germanic", "sv": "germanic",
    "da": "germanic", "no": "germanic", "nb": "germanic",
    "ru": "slavic", "pl": "slavic",
    "ja": "east_asian", "ko": "east_asian", "zh": "east_asian",
    "th": "southeast_asian", "vi": "southeast_asian",
    "ar": "semitic", "he": "semitic",
    "hi": "indo_aryan", "fi": "general", "tr": "general",
}


def error_types_for_language(language: str) -> tuple[ErrorType, ...]:
    """Return the target-language family's permitted tags, accepting regional codes."""
    code = language.strip().lower().replace("_", "-").split("-", 1)[0]
    family = LANGUAGE_FAMILY_BY_CODE.get(code, "general")
    return ERROR_TYPES_BY_FAMILY[family]

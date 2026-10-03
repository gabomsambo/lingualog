"""
LearningPolicy: the only place a immersion level becomes behaviour.

``resolve_policy(user_id, l2, overrides)`` returns one frozen, versioned object.
Journal feedback, and any later feature that needs to know what a level means,
reads that object. Nothing else maps a level number onto languages or flags.

Precedence
----------
Highest source wins. Documented here and in the README.

Immersion level (and the flags that follow it: ``meaning``, ``rewrite_gloss``,
``vocab_def``, ``quiz``, translation policy, idiom-gloss language):

1. Per-entry ``immersion_level`` override (the new-entry slider, once moved).
2. ``user_language_profiles`` row for this target language.
3. Legacy ``user_settings.immersion_level`` (one number for every language).
4. Default ``1`` (Guided).

Explanation language (notes, ``intended_meaning``):

1. Per-entry ``explanation_mode`` when it is set and is not ``level``.
2. Per-entry ``immersion_level`` — moving the slider means "use this level",
   including the note language that level defines. This beats a saved mode.
3. Saved ``user_settings.explanation_mode`` when it is an explicit choice
   (any value other than ``level`` or empty). ``bilingual`` stored on the
   account is explicit: the control stays, and it overrides the level.
4. Otherwise the immersion level decides.

Proficiency (A1–C2) is never derived from the immersion level. It comes from
the language profile, then an optional override, then ``A2``.

A per-entry explanation mode changes note language only. It does not change
meaning, rewrite glosses, vocabulary definitions, or quiz shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

POLICY_VERSION = 1

PROFICIENCY_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
DEFAULT_PROFICIENCY = "A2"

# explanation flag -> legacy explanation_mode, so existing callers keep working.
FLAG_TO_EXPLANATION_MODE = {
    "l1": "native_only",
    "l1_with_l2_terms": "smart",
    "l2_then_l1": "bilingual",
    "l2": "target_only",
}

EXPLANATION_MODE_TO_FLAG = {mode: flag for flag, mode in FLAG_TO_EXPLANATION_MODE.items()}

# Sentinel stored when the learner wants the level to decide note language.
EXPLANATION_MODE_FOLLOW_LEVEL = "level"

# One row per immersion level. This is the only level-to-behaviour map.
LEVELS = {
    0: {
        "name": "Native-first",
        "explanation": "l1",
        "meaning": "open",
        "rewrite_gloss": "l1_open",
        "vocab_def": "l1",
        "quiz": "recognition_l1",
        "translation_policy": "L2_to_L1",
        "explanation_lang": "native",
    },
    1: {
        "name": "Guided",
        "explanation": "l1_with_l2_terms",
        "meaning": "tap",
        "rewrite_gloss": "l1_tap",
        "vocab_def": "l1_plus_l2",
        "quiz": "recognition_and_recall",
        "translation_policy": "on_demand",
        "explanation_lang": "native",
    },
    2: {
        "name": "Balanced",
        "explanation": "l2_then_l1",
        "meaning": "tap_hidden",
        "rewrite_gloss": "l2_tooltips",
        "vocab_def": "l2_plus_l1",
        "quiz": "cloze_l1_hint",
        "translation_policy": "on_demand",
        "explanation_lang": "bilingual",
    },
    3: {
        "name": "Immersive",
        "explanation": "l2",
        "meaning": "rescue_only",
        "rewrite_gloss": "l2_tooltips",
        "vocab_def": "l2",
        "quiz": "l2_only",
        "translation_policy": "omit",
        "explanation_lang": "target",
    },
}

# Kept for callers that still read the old (explanation_lang, translation_policy) pairs.
IMMERSION_MAP = {
    level: (spec["explanation_lang"], spec["translation_policy"])
    for level, spec in LEVELS.items()
}

LANG_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "th": "Thai",
    "vi": "Vietnamese",
    "nl": "Dutch",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "pl": "Polish",
    "he": "Hebrew",
}

DEFAULT_SETTINGS = {
    "interface_lang": "en",
    "native_lang": "en",
    "default_target_lang": "es",
    "explanation_mode": "bilingual",
    "immersion_level": 1,
    "strictness": "medium",
    "formality": "neutral",
}

MINIMAL_CORRECTION_RULE = (
    "Minimal correction: change only what is wrong. "
    "Never change correct usage, even if another phrasing sounds more idiomatic. "
    "Keep the learner's grammatical gender; do not switch masculine and feminine."
)


class _Unset:
    """Distinguishes 'caller passed None' from 'caller did not pass a value'."""


UNSET = _Unset()


@dataclass(frozen=True)
class LearningPolicy:
    """Frozen snapshot of how this learner wants to be taught this language."""

    v: int
    l1: str
    l2: str
    ui_language: str
    immersion_level: int
    proficiency: str
    strictness: str
    formality: str
    explanation: str
    meaning: str
    rewrite_gloss: str
    vocab_def: str
    quiz: str
    explanation_mode: str
    translation_policy: str
    explanation_source: str
    immersion_source: str

    def to_dict(self) -> Dict[str, Any]:
        """JSON-ready snapshot stored on the journal entry (``v`` is the schema version)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningPolicy":
        """Rebuild a policy from a stored snapshot. Unknown keys are ignored."""
        fields = {name: data[name] for name in cls.__dataclass_fields__ if name in data}
        if "v" not in fields:
            fields["v"] = POLICY_VERSION
        return cls(**fields)


def _language_name(code: str) -> str:
    base = (code or "").split("-")[0].lower()
    return LANG_NAMES.get(base, code)


def _clamp_immersion(level: Any) -> int:
    try:
        number = int(level)
    except (TypeError, ValueError):
        return 1
    if number in LEVELS:
        return number
    return 1


def _normalize_proficiency(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    token = value.strip().upper()
    if token in PROFICIENCY_LEVELS:
        return token
    return None


def _level_spec(immersion_level: int) -> Dict[str, str]:
    return LEVELS[_clamp_immersion(immersion_level)]


def feedback_language_rules(policy: LearningPolicy) -> str:
    """Per-level note-language rules. The explanation flag is the switch."""
    l1 = _language_name(policy.l1)
    l2 = _language_name(policy.l2)
    graded = (
        f"Write {l2} at the learner's proficiency ({policy.proficiency}), "
        "not from the immersion level: short sentences and common words at A1-A2, "
        "a fuller range at B1-B2, near-native range at C1-C2."
    )
    rules = {
        "l1": (
            f"Write every note, explanation and `intended_meaning` in {l1} only. "
            f"Quote {l2} words only as examples. Fill `note_l1`; leave `note_l2` empty."
        ),
        "l1_with_l2_terms": (
            f"Write notes in {l1} (`note_l1`), but name each grammar point with its "
            f"{l2} term in parentheses so the learner meets the vocabulary of grammar. "
            f"Leave `note_l2` empty. `intended_meaning` in {l1}."
        ),
        "l2_then_l1": (
            f"Write each note first in {l2} (`note_l2`; {graded}) and then a one-line "
            f"{l1} gloss (`note_l1`). The explanation: {l2} first, then one short {l1} sentence. "
            f"`intended_meaning` in {l1}."
        ),
        "l2": (
            f"Write everything in {l2} only — notes (`note_l2`), explanation, and "
            f"`intended_meaning` (a simple {l2} paraphrase of what the learner meant). "
            f"{graded} Never use {l1}; leave `note_l1` empty."
        ),
    }
    return rules[policy.explanation]


def feedback_prompt_rules(policy: Any) -> str:
    """
    Full tutor instructions for one resolved policy.

    Gemini infers what the learner meant. A translation is not supplied and
    must not be assumed. Lara output is intentionally absent: feeding it into
    the correction made minimal edits worse.
    """
    l1 = _language_name(policy.l1)
    l2 = _language_name(policy.l2)
    immersion = _clamp_immersion(policy.immersion_level)
    warning_language = l2 if immersion >= 3 else l1
    question_language = l2 if immersion >= 2 else l1
    if policy.rewrite_gloss in ("l1_open", "l1_tap"):
        idiom_language = l1
    else:
        idiom_language = l2

    strictness = {
        "gentle": "Be encouraging and focus on positive reinforcement. Only point out major errors.",
        "medium": "Provide balanced feedback with both corrections and encouragement.",
        "strict": "Be thorough in corrections and point out all errors, including minor ones.",
        "pedantic": "Provide extremely detailed corrections including style and advanced grammar rules.",
    }.get(policy.strictness, "Provide balanced feedback with both corrections and encouragement.")
    formality = {
        "casual": "Use a friendly, conversational tone.",
        "neutral": "Use a professional but approachable tone.",
        "formal": "Use a formal, academic tone.",
        "academic": "Use scholarly language appropriate for academic writing.",
    }.get(policy.formality, "Use a professional but approachable tone.")

    return " ".join(
        [
            feedback_language_rules(policy),
            MINIMAL_CORRECTION_RULE,
            (
                "Work out the learner's intended meaning yourself from their words. "
                "No translation of the entry is provided; do not expect one and do not "
                "copy wording from an outside translation."
            ),
            (
                "When you are unsure what the learner meant, add a question to `ambiguities` "
                f"in {question_language} instead of rewriting the sentence into a different meaning."
            ),
            (
                "On each grammar point set `meaning_changing`. When the words as written mean "
                f"something else to a native speaker, set `literal_reading` in {warning_language} "
                "(as written, a native reads…)."
            ),
            (
                f"`rewrite_idioms` lists phrases from the rewrite with a gloss in {idiom_language}."
            ),
            (
                "Also fill `note` with the learner-facing explanation: `note_l1`, or `note_l2`, "
                "or `note_l2` followed by the one-line `note_l1` gloss. Existing clients read `note`."
            ),
            f"Proficiency is {policy.proficiency} and is separate from immersion level {immersion}.",
            strictness,
            formality,
        ]
    )


def _explicit_saved_explanation(settings: Optional[Dict[str, Any]]) -> Optional[str]:
    """A stored mode counts only when the account actually has the key set."""
    if not settings or "explanation_mode" not in settings:
        return None
    mode = settings.get("explanation_mode")
    if not mode or mode == EXPLANATION_MODE_FOLLOW_LEVEL:
        return None
    if mode not in EXPLANATION_MODE_TO_FLAG:
        return None
    return mode


def _fetch_settings(user_id: str) -> Optional[Dict[str, Any]]:
    from database import create_supabase_client

    supabase = create_supabase_client()
    response = supabase.table("user_settings").select("*").eq("user_id", user_id).limit(1).execute()
    if response.data:
        return response.data[0]
    return None


def _fetch_language_profile(user_id: str, l2: str) -> Optional[Dict[str, Any]]:
    from database import fetch_language_profile

    return fetch_language_profile(user_id, l2)


def resolve_policy(
    user_id: Optional[str],
    l2: Optional[str],
    overrides: Optional[Dict[str, Any]] = None,
    settings: Any = UNSET,
    language_profile: Any = UNSET,
) -> LearningPolicy:
    """
    Resolve the learning policy for one user and one target language.

    ``settings`` and ``language_profile`` are optional injections for tests and
    for callers that already loaded the rows. Pass ``None`` to mean "no row".
    Omit them to load from the database when ``user_id`` is set.
    """
    overrides = overrides or {}

    if isinstance(settings, _Unset):
        settings = None
        if user_id:
            try:
                settings = _fetch_settings(user_id)
            except Exception as exc:
                logger.warning("Could not load user settings for %s: %s", user_id, exc)
                settings = None

    resolved_l2 = (
        overrides.get("target_language")
        or overrides.get("language")
        or l2
        or (settings or {}).get("default_target_lang")
        or DEFAULT_SETTINGS["default_target_lang"]
    )

    if isinstance(language_profile, _Unset):
        language_profile = None
        if user_id and resolved_l2:
            try:
                language_profile = _fetch_language_profile(user_id, resolved_l2)
            except Exception as exc:
                logger.warning(
                    "Could not load language profile for %s/%s: %s",
                    user_id,
                    resolved_l2,
                    exc,
                )
                language_profile = None

    if overrides.get("immersion_level") is not None:
        immersion_level = _clamp_immersion(overrides["immersion_level"])
        immersion_source = "request"
    elif language_profile and language_profile.get("immersion_level") is not None:
        immersion_level = _clamp_immersion(language_profile["immersion_level"])
        immersion_source = "language_profile"
    elif settings and settings.get("immersion_level") is not None:
        immersion_level = _clamp_immersion(settings["immersion_level"])
        immersion_source = "user_settings"
    else:
        immersion_level = DEFAULT_SETTINGS["immersion_level"]
        immersion_source = "default"

    level = _level_spec(immersion_level)

    request_mode = overrides.get("explanation_mode")
    saved_mode = _explicit_saved_explanation(settings)
    if request_mode and request_mode != EXPLANATION_MODE_FOLLOW_LEVEL and request_mode in EXPLANATION_MODE_TO_FLAG:
        explanation = EXPLANATION_MODE_TO_FLAG[request_mode]
        explanation_mode = request_mode
        explanation_source = "request_explanation_mode"
    elif "immersion_level" in overrides and overrides.get("immersion_level") is not None:
        explanation = level["explanation"]
        explanation_mode = FLAG_TO_EXPLANATION_MODE[explanation]
        explanation_source = "request_immersion_level"
    elif saved_mode:
        explanation = EXPLANATION_MODE_TO_FLAG[saved_mode]
        explanation_mode = saved_mode
        explanation_source = "saved_explanation_mode"
    else:
        explanation = level["explanation"]
        explanation_mode = FLAG_TO_EXPLANATION_MODE[explanation]
        explanation_source = "immersion_level"

    proficiency = (
        _normalize_proficiency(overrides.get("proficiency"))
        or _normalize_proficiency((language_profile or {}).get("proficiency"))
        or _normalize_proficiency((settings or {}).get("proficiency"))
        or DEFAULT_PROFICIENCY
    )

    l1 = (
        overrides.get("native_lang")
        or (settings or {}).get("native_lang")
        or DEFAULT_SETTINGS["native_lang"]
    )
    ui_language = (
        overrides.get("ui_language")
        or (settings or {}).get("interface_lang")
        or DEFAULT_SETTINGS["interface_lang"]
    )
    strictness = (
        overrides.get("strictness")
        or (settings or {}).get("strictness")
        or DEFAULT_SETTINGS["strictness"]
    )
    formality = (
        overrides.get("formality")
        or (settings or {}).get("formality")
        or DEFAULT_SETTINGS["formality"]
    )

    policy = LearningPolicy(
        v=POLICY_VERSION,
        l1=l1,
        l2=resolved_l2,
        ui_language=ui_language,
        immersion_level=immersion_level,
        proficiency=proficiency,
        strictness=strictness,
        formality=formality,
        explanation=explanation,
        meaning=level["meaning"],
        rewrite_gloss=level["rewrite_gloss"],
        vocab_def=level["vocab_def"],
        quiz=level["quiz"],
        explanation_mode=explanation_mode,
        translation_policy=level["translation_policy"],
        explanation_source=explanation_source,
        immersion_source=immersion_source,
    )
    logger.info(
        "Resolved learning policy v=%s L1=%s L2=%s immersion=%s (%s) "
        "explanation=%s (%s) proficiency=%s",
        policy.v,
        policy.l1,
        policy.l2,
        policy.immersion_level,
        policy.immersion_source,
        policy.explanation,
        policy.explanation_source,
        policy.proficiency,
    )
    return policy

"""What a review card shows. Pure functions, deterministic, no model calls.

The front is the learner's own sentence. Recognition highlights the word in it. Production
cards blank the word in the *corrected* version of that sentence, so the cloze never teaches
a mistake. With several encounters the sentence rotates with each review.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

from app.services.entry_translation_service import split_sentences
from review_scheduler import PRODUCTION, RECOGNITION

# Languages written without spaces between words, where a word has no \w boundary around it.
UNSPACED_LANGUAGES = frozenset({"ja", "zh", "th"})

# quiz flag (learning_policy.LEVELS) -> how a production card is asked.
PRODUCTION_FORMATS = {
    "recognition_l1": "meaning_to_word",
    "recognition_and_recall": "typed_recall",
    "cloze_l1_hint": "cloze",
    "l2_only": "cloze",
}
# Policies whose learner may see the native gloss; the middle level keeps it behind a tap.
GLOSS_SHOWN = frozenset({"recognition_l1", "recognition_and_recall"})
GLOSS_ON_TAP = frozenset({"cloze_l1_hint"})
_MIN_OVERLAP = 0.3


@dataclass(frozen=True)
class Candidate:
    """A sentence the learner met the word in, and the forms the word took there."""

    sentence: str
    surfaces: tuple[str, ...]
    entry_id: Optional[str] = None
    kind: str = "lookup"


@dataclass(frozen=True)
class Cloze:
    before: str
    answer: str
    after: str


def _base(language: str) -> str:
    return (language or "").split("-")[0].lower()


def _pattern(form: str, language: str) -> re.Pattern[str]:
    escaped = re.escape(form.strip())
    if _base(language) in UNSPACED_LANGUAGES:
        return re.compile(escaped, re.IGNORECASE)
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def find_form(sentence: str, forms: Iterable[str], language: str) -> Optional[tuple[int, int]]:
    """Span of the first of ``forms`` found as a whole word, preferring the longest form."""
    for form in sorted({f for f in forms if f and f.strip()}, key=len, reverse=True):
        match = _pattern(form, language).search(sentence)
        if match:
            return match.start(), match.end()
    return None


def split_around(sentence: str, forms: Iterable[str], language: str) -> Optional[Cloze]:
    """The sentence cut around the word, keeping the word exactly as written."""
    span = find_form(sentence, forms, language)
    if not span:
        return None
    return Cloze(sentence[: span[0]], sentence[span[0]:span[1]], sentence[span[1]:])


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _overlap(a: str, b: str) -> float:
    left, right = _tokens(a), _tokens(b)
    return len(left & right) / max(1, len(left | right))


def corrected_sentence(
    candidate: Candidate,
    forms: Sequence[str],
    language: str,
    entry: Optional[Mapping[str, Any]],
) -> Optional[str]:
    """The corrected sentence that holds the word, or None when none can be found.

    A fix or the rewrite is already corrected. Otherwise the source entry's validated
    sentence mapping names the corrected sentences; without one, the corrected sentence that
    contains the word and overlaps most with what the learner wrote stands in.
    """
    if candidate.kind in ("entry_fix", "entry_rewrite"):
        return candidate.sentence
    if not entry or not entry.get("corrected"):
        return None
    corrected = split_sentences(entry["corrected"])
    original = split_sentences(entry.get("original_text") or "")
    shortlist = corrected
    mapping = entry.get("sentence_mapping") or []
    if entry.get("sentence_mapping_status") == "valid" and mapping:
        for index, source in enumerate(original):
            if candidate.sentence.strip() == source or candidate.sentence.strip() in source:
                row = next((m for m in mapping if m.get("source_sentence") == index), None)
                targets = [corrected[i] for i in (row or {}).get("corrected_sentences", []) if i < len(corrected)]
                if targets:
                    shortlist = targets
                break
    holding = [s for s in shortlist if find_form(s, forms, language)]
    if not holding:
        return None
    return max(holding, key=lambda s: _overlap(s, candidate.sentence))


def normalize_answer(text: str) -> str:
    """Case, accent and spacing insensitive form used to compare a typed answer."""
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped)


def accepted_answers(*forms: Optional[str]) -> list[str]:
    seen: list[str] = []
    for form in forms:
        value = normalize_answer(form or "")
        if value and value not in seen:
            seen.append(value)
    return seen


def pick(options: Sequence[Any], reps: int) -> Optional[Any]:
    """Rotate through options as the card is reviewed, so one context is not memorised."""
    return options[reps % len(options)] if options else None


def sentence_candidates(
    word: Mapping[str, Any], encounters: Sequence[Mapping[str, Any]]
) -> list[Candidate]:
    """The learner's own sentences for this word, oldest first, each sentence once.

    The same sentence is often both the saved example and a lookup, so the forms the word
    took in every copy are kept together.
    """
    card = word.get("card") or {}
    order: list[str] = []
    found: dict[str, dict[str, Any]] = {}

    def add(sentence: Optional[str], surface: Optional[str], entry_id: Any, kind: str) -> None:
        text = (sentence or "").strip()
        if not text:
            return
        if text not in found:
            order.append(text)
            found[text] = {"surfaces": [], "entry_id": str(entry_id) if entry_id else None, "kind": kind}
        if surface and surface.strip() and surface.strip() not in found[text]["surfaces"]:
            found[text]["surfaces"].append(surface.strip())

    add(word.get("example_sentence"), card.get("surface"), word.get("entry_id"), "lookup")
    for encounter in sorted(encounters, key=lambda row: str(row.get("created_at"))):
        # A use with a mistake in it is feedback, not a sentence to learn from.
        if encounter.get("kind") == "used_error":
            continue
        # A word met in a sentence that is just the word itself gives no context.
        if encounter.get("sentence") and encounter["sentence"].strip() != encounter.get("surface", "").strip():
            entry_id = encounter.get("source_id") if encounter.get("source_type") == "entry" else None
            add(encounter["sentence"], encounter.get("surface"), entry_id, encounter.get("kind") or "lookup")
            if entry_id and not found[encounter["sentence"].strip()]["entry_id"]:
                found[encounter["sentence"].strip()]["entry_id"] = str(entry_id)
    return [Candidate(text, tuple(found[text]["surfaces"]), found[text]["entry_id"], found[text]["kind"])
            for text in order]


def word_forms(word: Mapping[str, Any], candidate: Optional[Candidate] = None) -> list[str]:
    card = word.get("card") or {}
    return [f for f in (*(candidate.surfaces if candidate else ()), card.get("surface"),
                        word.get("lemma"), word.get("term")) if f]


def review_format(card_type: str, quiz: str) -> str:
    """The ask for a card: recognition is always sentence to meaning; production follows ``quiz``."""
    if card_type == RECOGNITION:
        return "recognition"
    return PRODUCTION_FORMATS.get(quiz, "meaning_to_word")


def _cloze_options(
    word: Mapping[str, Any],
    candidates: Sequence[Candidate],
    entries: Mapping[str, Mapping[str, Any]],
    language: str,
) -> list[tuple[Cloze, str]]:
    """Every sentence the word can be blanked in, with where the sentence came from."""
    options: list[tuple[Cloze, str]] = []
    for candidate in candidates:
        forms = word_forms(word, candidate)
        fixed = corrected_sentence(candidate, forms, language, entries.get(candidate.entry_id or ""))
        source = "corrected"
        if fixed is None and candidate.entry_id is None:
            # Not the learner's own entry text, so there is no mistake to avoid teaching.
            fixed, source = candidate.sentence, "encounter"
        if fixed and (cut := split_around(fixed, forms, language)):
            options.append((cut, source))
    if not options:
        for example in (word.get("card") or {}).get("examples") or []:
            if cut := split_around(example, word_forms(word), language):
                options.append((cut, "card_example"))
    return options


def _front_hint(asked: str, quiz: str, meaning: str, gloss: str) -> str:
    """What the learner sees beside the question. Level 2 keeps its gloss behind a tap."""
    if asked == "recognition":
        return ""
    if quiz == "l2_only":
        return meaning
    if quiz in GLOSS_ON_TAP:
        return ""
    return gloss or meaning


def build_review_card(
    row: Mapping[str, Any],
    word: Mapping[str, Any],
    encounters: Sequence[Mapping[str, Any]],
    entries: Mapping[str, Mapping[str, Any]],
    quiz: str,
    status: str,
    at_risk: bool,
) -> dict[str, Any]:
    """Everything the client needs to show one card. Pure, so it never calls a model."""
    language = row["language"]
    card = word.get("card") or {}
    reps = int(row.get("reps") or 0)
    candidates = sentence_candidates(word, encounters)
    asked = review_format(row["card_type"], quiz)
    lemma = word.get("lemma") or word.get("term") or ""

    front = {"before": "", "target": "", "after": ""}
    source = "word"
    if asked in ("cloze", "typed_recall"):
        choice = pick(_cloze_options(word, candidates, entries, language), reps)
        if choice:
            cut, source = choice
            front = {"before": cut.before, "target": cut.answer, "after": cut.after}
        else:
            asked = "meaning_to_word"
    elif candidates:
        chosen = pick(candidates, reps)
        cut = split_around(chosen.sentence, word_forms(word, chosen), language)
        source = "encounter"
        front = (
            {"before": cut.before, "target": cut.answer, "after": cut.after}
            if cut else {"before": chosen.sentence, "target": "", "after": ""}
        )
    if asked == "recognition" and not candidates:
        front = {"before": "", "target": lemma, "after": ""}

    meaning = card.get("sense_in_context") or word.get("sense") or ""
    native = card.get("gloss_l1") or ""
    answer = front["target"] if asked in ("cloze", "typed_recall") else lemma
    return {
        "card_id": row["id"],
        "word_id": row["word_id"],
        "card_type": row["card_type"],
        "format": asked,
        "language": language,
        "lemma": lemma,
        "reps": reps,
        "is_new": reps == 0 and row["card_type"] == RECOGNITION,
        "front": front,
        "sentence_source": source,
        "meaning": meaning,
        "gloss": native if quiz in GLOSS_SHOWN else "",
        "tap_gloss": native if quiz in GLOSS_ON_TAP else "",
        "hint": _front_hint(asked, quiz, meaning, native),
        "answer": answer,
        "typed": asked == "typed_recall",
        "accepted": accepted_answers(answer, lemma, word.get("term")),
        "status": status,
        "at_risk": at_risk,
    }

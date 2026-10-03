"""Entry meaning translations via Lara (Gemini fallback)."""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ai.gemini_translate import translate_sentences_gemini
from ai.lara import LaraUnavailableError, translate_texts
from ai.locale_map import to_lara_locale
from database import create_supabase_client, fetch_single_entry

logger = logging.getLogger(__name__)

JOURNAL_ENTRIES_TABLE = "journal_entries"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def split_sentences(text: str) -> List[str]:
    stripped = text.strip()
    if not stripped:
        return []
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(stripped) if p.strip()]
    return parts if parts else [stripped]


def join_sentences(sentences: List[str]) -> str:
    return "\n\n".join(sentences)


def _cache_key(part: str, target_lang: str) -> str:
    return f"{part}:{target_lang}"


def _get_cached(cache: Dict[str, Any], part: str, target_lang: str) -> Optional[Dict[str, Any]]:
    entry = cache.get(_cache_key(part, target_lang))
    if isinstance(entry, dict) and entry.get("status") == "ok":
        return entry
    return None


def _build_note_html(note_text: str, quoted_terms: List[str]) -> str:
    html = note_text
    for term in sorted(set(quoted_terms), key=len, reverse=True):
        if not term:
            continue
        html = html.replace(term, f'<span translate="no">{term}</span>')
    return f"<p>{html}</p>"


def _grammar_suggestions(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    ai = entry.get("ai_feedback") or {}
    raw = ai.get("grammar_suggestions") or entry.get("grammar_suggestions") or []
    return raw if isinstance(raw, list) else []


def _resolve_source_text(entry: Dict[str, Any], part: str) -> Tuple[str, List[str], Optional[str]]:
    """Return (source_text, quoted_l2_terms, content_type)."""
    if part == "original":
        text = entry.get("content") or entry.get("original_text") or ""
        return text, [], None
    if part == "rewrite":
        ai = entry.get("ai_feedback") or {}
        text = ai.get("rewrite") or entry.get("rewrite") or ""
        return text, [], None
    if part.startswith("note:"):
        note_id = part.split(":", 1)[1]
        suggestions = _grammar_suggestions(entry)
        for index, sugg in enumerate(suggestions):
            sid = str(sugg.get("id") if sugg.get("id") is not None else index)
            if sid == note_id:
                note = sugg.get("note") or ""
                original = sugg.get("original") or ""
                terms = [original] if original else []
                return _build_note_html(note, terms), terms, "html"
        raise ValueError(f"Grammar note not found: {note_id}")
    raise ValueError(f"Unknown translation part: {part}")


async def _run_translation(
    sentences: List[str],
    *,
    source_lang: str,
    target_lang: str,
    content_type: Optional[str] = None,
    html_source: Optional[str] = None,
) -> Tuple[List[str], str, str]:
    """Returns (translated_sentences, provider, status)."""
    try:
        if content_type == "html" and html_source:
            translated = await translate_texts(
                html_source,
                source_lang=source_lang,
                target_lang=target_lang,
                content_type="html",
            )
            return translated, "lara", "ok"
        translated = await translate_texts(
            sentences,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        return translated, "lara", "ok"
    except (LaraUnavailableError, asyncio.TimeoutError, Exception) as lara_err:
        logger.info("Lara translation unavailable, trying Gemini fallback: %s", lara_err)

    try:
        translated = await translate_sentences_gemini(
            sentences,
            to_lara_locale(source_lang),
            to_lara_locale(target_lang),
        )
        return translated, "gemini", "ok"
    except Exception as gemini_err:
        logger.error("Gemini translation fallback failed: %s", gemini_err)
        return [], "none", "unavailable"


async def translate_entry_part(
    entry_id: str,
    user_id: str,
    part: str,
    target_lang: str,
) -> Dict[str, Any]:
    entry = fetch_single_entry(entry_id, user_id)
    if not entry:
        raise PermissionError("Entry not found")

    source_lang = entry.get("language") or entry.get("target_language") or "es"
    cache: Dict[str, Any] = entry.get("meaning_translations_cache") or {}
    if not isinstance(cache, dict):
        cache = {}

    cached = _get_cached(cache, part, target_lang)
    if cached:
        return {
            "part": part,
            "target_lang": target_lang,
            "source_lang": source_lang,
            "sentences": cached.get("sentences", []),
            "text": cached.get("text", ""),
            "provider": cached.get("provider"),
            "status": cached.get("status", "ok"),
            "provider_label": cached.get("provider_label"),
            "cached": True,
        }

    source_text, _terms, content_type = _resolve_source_text(entry, part)

    if content_type == "html":
        sentences = [source_text]
        html_source = source_text
    else:
        sentences = split_sentences(source_text)
        html_source = None

    if not sentences:
        payload = {
            "sentences": [],
            "text": "",
            "provider": "none",
            "status": "unavailable",
            "provider_label": None,
        }
    else:
        translated, provider, status = await _run_translation(
            sentences,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            html_source=html_source,
        )
        provider_label = None
        if provider == "gemini":
            provider_label = "Translated by Gemini (Flash-Lite)"
        elif provider == "lara":
            provider_label = "Translated by Lara"

        payload = {
            "sentences": translated,
            "text": join_sentences(translated) if translated else "",
            "provider": provider,
            "status": status,
            "provider_label": provider_label,
        }

    cache[_cache_key(part, target_lang)] = payload
    supabase = create_supabase_client()
    supabase.table(JOURNAL_ENTRIES_TABLE).update(
        {"meaning_translations_cache": cache}
    ).eq("id", entry_id).eq("user_id", user_id).execute()

    return {
        "part": part,
        "target_lang": target_lang,
        "source_lang": source_lang,
        "cached": False,
        **payload,
    }

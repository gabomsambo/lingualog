"""Lara Translate adapter — all SDK calls go through translate_texts()."""

import asyncio
import logging
import os
from typing import Iterable, List, Optional, Union

from lara_sdk import AccessKey, TextBlock, Translator

from ai.locale_map import to_lara_locale

logger = logging.getLogger(__name__)

LARA_DEFAULT_TIMEOUT_MS = int(os.getenv("LARA_TRANSLATE_TIMEOUT_MS", "30000"))

# Enforced on every Lara API call (private journals; block account translation memories).
LARA_PRIVACY_KWARGS = {
    "no_trace": True,
    "adapt_to": [],
}


class LaraUnavailableError(Exception):
    """Lara credentials missing or the API call failed."""


def _build_translator() -> Translator:
    access_id = os.getenv("LARA_TRANSLATE_ID")
    secret = os.getenv("LARA_TRANSLATE_SECRET")
    if not access_id or not secret:
        raise LaraUnavailableError("LARA_TRANSLATE_ID or LARA_TRANSLATE_SECRET not set")
    return Translator(AccessKey(access_id, secret))


def _translate_sync(
    text: Union[str, Iterable[str], Iterable[TextBlock]],
    *,
    source: Optional[str],
    target: str,
    content_type: Optional[str] = None,
    timeout_ms: Optional[int] = None,
) -> List[str]:
    translator = _build_translator()
    kwargs = {
        **LARA_PRIVACY_KWARGS,
        "target": target,
        "style": "faithful",
        "timeout_ms": timeout_ms or LARA_DEFAULT_TIMEOUT_MS,
    }
    if source:
        kwargs["source"] = source
    if content_type:
        kwargs["content_type"] = content_type

    result = translator.translate(text, **kwargs)
    translation = result.translation
    if isinstance(translation, list):
        parts: List[str] = []
        for item in translation:
            if isinstance(item, TextBlock):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return parts
    return [str(translation)]


async def translate_texts(
    texts: Union[str, List[str]],
    *,
    source_lang: str,
    target_lang: str,
    content_type: Optional[str] = None,
    timeout_s: float = 35.0,
) -> List[str]:
    """
    Translate one or more related strings (sentence-aligned) via Lara.

    Raises LaraUnavailableError when credentials are missing.
    Raises asyncio.TimeoutError or Lara SDK errors on failure.
    """
    source_locale = to_lara_locale(source_lang)
    target_locale = to_lara_locale(target_lang)
    payload: Union[str, List[str]] = texts if isinstance(texts, str) else list(texts)

    return await asyncio.wait_for(
        asyncio.to_thread(
            _translate_sync,
            payload,
            source=source_locale,
            target=target_locale,
            content_type=content_type,
            timeout_ms=LARA_DEFAULT_TIMEOUT_MS,
        ),
        timeout=timeout_s,
    )


def lara_configured() -> bool:
    return bool(os.getenv("LARA_TRANSLATE_ID") and os.getenv("LARA_TRANSLATE_SECRET"))

"""Gemini Flash-Lite fallback when Lara is unavailable."""

import asyncio
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# gemini-2.5-flash-lite 404s for new API keys; the "-latest" alias tracks the served Flash-Lite.
GEMINI_FLASH_LITE_MODEL = os.getenv("GEMINI_TRANSLATE_MODEL", "gemini-flash-lite-latest")


def _translate_sync(sentences: List[str], source_locale: str, target_locale: str) -> List[str]:
    import google.generativeai as genai
    from config import GEMINI_API_KEY

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_FLASH_LITE_MODEL)

    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences))
    prompt = (
        f"Translate each numbered sentence from {source_locale} to {target_locale}. "
        "Preserve the learner's intended meaning (including false friends and mistakes). "
        "Return ONLY the translations, one per line, same numbering, no extra commentary.\n\n"
        f"{numbered}"
    )
    response = model.generate_content(prompt)
    text = ""
    if response.candidates and response.candidates[0].content.parts:
        text = response.candidates[0].content.parts[0].text or ""

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: List[str] = []
    for line in lines:
        if len(line) > 2 and line[0].isdigit() and "." in line[:4]:
            _, rest = line.split(".", 1)
            out.append(rest.strip())
        else:
            out.append(line)
    if len(sentences) == 1 and out:
        return [" ".join(out)]
    if len(out) != len(sentences):
        raise ValueError(
            f"Gemini returned {len(out)} lines for {len(sentences)} sentences"
        )
    return out


async def translate_sentences_gemini(
    sentences: List[str],
    source_locale: str,
    target_locale: str,
    timeout_s: float = 30.0,
) -> List[str]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_translate_sync, sentences, source_locale, target_locale),
            timeout=timeout_s,
        )
    except Exception as exc:
        logger.warning("Gemini translation fallback failed: %s", exc)
        raise

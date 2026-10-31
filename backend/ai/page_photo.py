"""Flash-Lite vision for a photographed book page: the text, and the words worth marking."""

from __future__ import annotations

import os
from typing import List

from pydantic import BaseModel, Field

from ai.gemini import generate_structured
from learning_policy import LANG_NAMES

GEMINI_MODEL_PAGE_PHOTO = os.getenv("GEMINI_MODEL_PAGE_PHOTO", "gemini-3.5-flash-lite")


class PageWord(BaseModel):
    """One word on the page the learner probably does not know yet."""

    surface: str = Field(description="The word exactly as printed on the page")
    lemma: str = Field(description="Dictionary form of the word, or the full fixed phrase")


class PageTranscription(BaseModel):
    """The structured vision result for one page."""

    readable: bool = Field(description="False when the photo shows no legible printed text")
    transcription: str = Field(
        description="The page text exactly as printed, in reading order, one paragraph per line"
    )
    candidates: List[PageWord] = Field(
        description=(
            "Words and fixed phrases a learner at the stated proficiency probably does not know. "
            "Never proper nouns. Empty when nothing qualifies."
        )
    )


def _language_name(code: str) -> str:
    return LANG_NAMES.get((code or "").split("-")[0].lower(), code)


def build_page_photo_prompts(language: str, proficiency: str) -> tuple[str, str]:
    """The prompt contract for one page photo."""
    system_prompt = (
        "You read one photographed page of a printed book for a language learner. Transcribe the "
        "text exactly as printed, without correcting, translating or adding anything; ignore "
        "page numbers, running heads and anything outside the page. Then list the words and "
        f"fixed phrases a learner at {proficiency} level probably does not know. Use the exact "
        "printed form as surface and the dictionary form as lemma. Skip proper nouns, numbers "
        "and words that look like cognates of everyday English. If the photo has no legible "
        "text, set readable to false and leave the other fields empty."
    )
    user_prompt = f"The book is written in {_language_name(language)}. Read this page."
    return system_prompt, user_prompt


async def read_page_photo(
    image: bytes, mime_type: str, language: str, proficiency: str
) -> PageTranscription:
    """One structured Flash-Lite vision call. The image is only held in memory for it."""
    system_prompt, user_prompt = build_page_photo_prompts(language, proficiency)
    return await generate_structured(
        system_prompt,
        user_prompt,
        PageTranscription,
        timeout=45.0,
        model=GEMINI_MODEL_PAGE_PHOTO,
        use_thinking=False,
        images=[(image, mime_type)],
    )


__all__ = [
    "GEMINI_MODEL_PAGE_PHOTO",
    "PageTranscription",
    "PageWord",
    "build_page_photo_prompts",
    "read_page_photo",
]

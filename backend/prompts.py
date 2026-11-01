"""Curated writing prompts for languages that have a reviewed prompt pack."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


CONTENT_DIR = Path(__file__).parent / "content" / "prompts"
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
PACK_LEVELS = ("A1", "A2", "B1")


@lru_cache(maxsize=8)
def _load_pack(l2: str) -> List[Dict[str, Any]]:
    """Read a static prompt pack. Unsupported languages intentionally have no prompts."""
    language = l2.split("-")[0].lower()
    path = CONTENT_DIR / f"{language}.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("prompts", [])


def content_level(level: str) -> str:
    """Use the closest curated level, capping advanced learners at the B1 pack."""
    normalized = level.strip().upper()
    if normalized not in CEFR_LEVELS:
        raise ValueError(f"level must be one of {', '.join(CEFR_LEVELS)}")
    rank = CEFR_LEVELS.index(normalized)
    return PACK_LEVELS[min(rank, len(PACK_LEVELS) - 1)]


def list_prompts(
    l2: str,
    level: str,
    topic: Optional[str] = None,
    exclude: Iterable[str] = (),
    *,
    meaning: str = "rescue_only",
    l1: str = "en",
) -> Dict[str, Any]:
    """Filter a prompt pack and include only an English gloss allowed by policy."""
    selected_level = content_level(level)
    excluded = {item.strip() for item in exclude if item.strip()}
    normalized_topic = (topic or "").strip().lower()
    pack = _load_pack(l2)
    records = [
        item for item in pack
        if item.get("level") == selected_level
        and item.get("id") not in excluded
        and (not normalized_topic or normalized_topic in item.get("topics", []))
    ]
    may_show_meaning = meaning != "rescue_only" and l1.split("-")[0].lower() == "en"
    prompts = []
    for item in records:
        prompt = dict(item)
        prompt["gloss"] = item.get("gloss_en") if may_show_meaning else None
        prompt.pop("gloss_en", None)
        prompts.append(prompt)
    topics = sorted({tag for item in pack if item.get("level") == selected_level for tag in item.get("topics", [])})
    return {
        "l2": l2.split("-")[0].lower(),
        "level": selected_level,
        "meaning": meaning,
        "gloss_available": may_show_meaning,
        "topics": topics,
        "prompts": prompts,
    }


def get_prompt(l2: str, prompt_id: str) -> Optional[Dict[str, Any]]:
    """Return a raw authored prompt for validating an entry's prompt id."""
    return next((item for item in _load_pack(l2) if item.get("id") == prompt_id), None)

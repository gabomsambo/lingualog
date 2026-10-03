"""How many tokens a correction changed. Japanese is counted by character."""

import difflib
import re
from typing import List


def tokens(text: str, l2: str) -> List[str]:
    if l2 == "ja":
        return list(text)
    return re.findall(r"\w+|[^\w\s]", text)


def words_changed(original: str, corrected: str, l2: str) -> int:
    """Token edits between the learner's text and the correction. Equal spans do not count."""
    before, after = tokens(original, l2), tokens(corrected, l2)
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    return sum(
        max(i2 - i1, j2 - j1)
        for op, i1, i2, j1, j2 in matcher.get_opcodes()
        if op != "equal"
    )

"""
Score corrected text against the planted-error corpus.

Manual only. Pytest and CI do not run this module.

    cd backend
    python -m evals.score_ref
    python -m evals.score_ref path/to/results.json

A results file is a JSON list of ``{"key", "cond", "rep", "out": {"corrected", "ambiguities"?}}``.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from evals.corpus import CORPUS
from evals.edits import words_changed


def score_corrected(key: str, corrected: str) -> Dict[str, Any]:
    """Return hits, misses, and broken traps for one corrected entry."""
    entry = CORPUS[key]
    hits = [name for name, options in entry["errors"].items() if any(option in corrected for option in options)]
    misses = [name for name in entry["errors"] if name not in hits]
    traps_broken = [
        name for name, options in entry["traps"].items() if not any(option in corrected for option in options)
    ]
    return {
        "key": key,
        "hits": hits,
        "misses": misses,
        "hit_count": len(hits),
        "error_count": len(entry["errors"]),
        "traps_broken": traps_broken,
        "trap_count": len(entry["traps"]),
        "words_changed": words_changed(entry["text"], corrected, entry["l2"]),
    }


def score_results(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Aggregate a list of result rows the way the immersion probe was scored."""
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        scored = score_corrected(row["key"], row["out"]["corrected"])
        scored["ambiguities"] = len(row["out"].get("ambiguities") or [])
        buckets[row.get("cond", "unlabelled")].append(scored)

    summary = {}
    for condition, items in buckets.items():
        summary[condition] = {
            "errors_fixed": sum(item["hit_count"] for item in items),
            "errors_total": sum(item["error_count"] for item in items),
            "traps_broken": sum(len(item["traps_broken"]) for item in items),
            "traps_total": sum(item["trap_count"] for item in items),
            "mean_words_changed": round(
                sum(item["words_changed"] for item in items) / len(items), 2
            ),
            "runs": len(items),
        }
    return summary


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Probe corpus (manual eval, not CI):")
        for key, entry in CORPUS.items():
            print(f"  {key} {entry['l2']}: {len(entry['errors'])} errors, {len(entry['traps'])} traps")
        print("Pass a results JSON file to score it.")
        return 0

    rows = json.loads(Path(argv[1]).read_text())
    summary = score_results(rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

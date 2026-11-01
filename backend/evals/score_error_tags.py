"""Run the Spanish error-tag corpus through the production Gemini feedback call."""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
CORPUS_PATH = Path(__file__).with_name("error_tags_es.json")
MAX_LIVE_CALLS = 80


def _load_local_gemini_key() -> None:
    """Load only the API key from the project dotenv file without printing it."""
    if os.getenv("GEMINI_API_KEY"):
        return
    dotenv = REPO_DIR / ".env"
    if not dotenv.is_file():
        return
    needed = {"GEMINI_API_KEY", "GEMINI_MODEL_FEEDBACK"}
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        name = key.strip()
        if separator and name in needed and value.strip():
            os.environ.setdefault(name, value.strip().strip("\"'"))


def _classification_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = Counter(row["expected"] for row in rows)
    predicted = Counter(row["predicted"] for row in rows if row["predicted"] is not None)
    true_positive = Counter(
        row["expected"] for row in rows if row["predicted"] == row["expected"]
    )
    labels = sorted(set(expected) | set(predicted))
    per_tag = {}
    for label in labels:
        tp = true_positive[label]
        fp = predicted[label] - tp
        fn = expected[label] - tp
        per_tag[label] = {
            "support": expected[label],
            "precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
            "recall": round(tp / (tp + fn), 4) if tp + fn else 0.0,
        }
    correct = sum(row["predicted"] == row["expected"] for row in rows)
    return {
        "samples": len(rows),
        "accuracy": round(correct / len(rows), 4) if rows else 0.0,
        "correct": correct,
        "per_tag": per_tag,
    }


async def _run_live(corpus: list[dict[str, str]]) -> tuple[list[dict[str, Any]], int, str]:
    _load_local_gemini_key()
    sys.path.insert(0, str(BACKEND_DIR))
    from google import genai

    from ai.gemini import GeminiError, generate_structured
    from ai.schemas import GeminiJournalFeedback
    from lang_policy import resolve_effective
    from prompt_builder import build_messages, build_user_message

    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is required for live scoring")
    model = os.getenv("GEMINI_MODEL_FEEDBACK", "gemini-3.8-flash")
    original_client_factory = genai.Client
    counter = {"calls": 0}

    def counted_client(*args: Any, **kwargs: Any) -> Any:
        client = original_client_factory(*args, **kwargs)

        async def counted_generate(*call_args: Any, **call_kwargs: Any) -> Any:
            if counter["calls"] >= MAX_LIVE_CALLS:
                raise RuntimeError(f"live Gemini call cap reached ({MAX_LIVE_CALLS})")
            counter["calls"] += 1
            return await client.aio.models.generate_content(*call_args, **call_kwargs)

        return SimpleNamespace(
            aio=SimpleNamespace(models=SimpleNamespace(generate_content=counted_generate))
        )

    genai.Client = counted_client
    rows = []
    profile = {
        "interface_lang": "en",
        "native_lang": "en",
        "default_target_lang": "es",
        "explanation_mode": "bilingual",
        "immersion_level": 1,
        "strictness": "medium",
        "formality": "neutral",
    }
    try:
        for sample in corpus:
            effective = resolve_effective(
                profile,
                {"target_language": "es", "proficiency": sample["level"]},
            )
            system_prompt, _ = build_messages(sample["text"], effective)
            user_prompt = build_user_message(sample["text"], effective)
            try:
                feedback = await generate_structured(
                    system_prompt,
                    user_prompt,
                    GeminiJournalFeedback,
                    timeout=45.0,
                    model=model,
                    use_thinking=False,
                )
                predicted = (
                    feedback.grammar_suggestions[0].error_type
                    if feedback.grammar_suggestions
                    else None
                )
                failure = None
            except GeminiError as exc:
                predicted = None
                failure = exc.code
            rows.append({
                "id": sample["id"],
                "level": sample["level"],
                "expected": sample["expected"],
                "predicted": predicted,
                "failure": failure,
            })
    finally:
        genai.Client = original_client_factory
    return rows, counter["calls"], model


def _render_report(report: dict[str, Any]) -> str:
    lines = [
        f"Live calls: {report['live_calls']} / {MAX_LIVE_CALLS}",
        f"Model: {report['model']}",
        f"Overall accuracy: {report['correct']}/{report['samples']} ({report['accuracy']:.1%})",
        "",
        "| Tag | Support | Precision | Recall |",
        "| --- | ---: | ---: | ---: |",
    ]
    for tag, metrics in report["per_tag"].items():
        lines.append(
            f"| `{tag}` | {metrics['support']} | {metrics['precision']:.1%} | {metrics['recall']:.1%} |"
        )
    return "\n".join(lines)


async def _main(args: argparse.Namespace) -> int:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if not corpus or len(corpus) * 2 > MAX_LIVE_CALLS:
        raise RuntimeError("Corpus must be non-empty and leave room for one Gemini retry per sample")
    rows, live_calls, model = await _run_live(corpus)
    metrics = _classification_metrics(rows)
    report = {**metrics, "live_calls": live_calls, "model": model, "results": rows}
    print(_render_report(report))
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Raw results: {args.output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional path for raw results; keep generated output outside the repository")
    return asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

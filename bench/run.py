"""Run text-only predictions, save resumable checkpoints, then score the replies."""

import argparse
import csv
import hashlib
import json
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from agent.budget import paid_run_guard
from core.building import content_hash
from core.profiles import current_profile

from .agent import PROMPT_VERSION, configure_budget, predict, validate_mode

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "agent_output" / "bench"
ROUTE_KINDS = {"route", "route_step_free", "route_with_closure", "tour"}


@dataclass(frozen=True)
class RunConfig:
    directory: Path
    name: str
    csv: Path | None = None
    workers: int = 4
    mode: str = "llm"
    kinds: tuple[str, ...] = ()
    limit: int | None = None
    warmup: bool = False
    max_cost: float | None = None
    paraphrases: Path | None = None
    per_kind: int | None = None


def revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def source_hash() -> str:
    digest = hashlib.sha256()
    for directory in ("bench", "agent", "core", "server", "starter_agent"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    for path in sorted((ROOT / "agent" / "skills").glob("*.md")):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def execution_context(mode: str) -> dict:
    """Use the same model settings and prompt versions as inference."""
    validate_mode(mode)
    if mode == "template":
        return {"mode": mode, "model": None, "agent_options": None,
                "prompt_version": PROMPT_VERSION, "prompt_versions": {"template": PROMPT_VERSION}}
    from agent.config import configured_options
    from agent.prompts import PROMPT_VERSION as AGENT_PROMPT_VERSION
    from .llm_fallback import PROMPT_VERSION as SUBMISSION_PROMPT_VERSION

    options = asdict(configured_options())
    versions = {"agent": AGENT_PROMPT_VERSION, "submission": SUBMISSION_PROMPT_VERSION}
    return {"mode": mode, "model": options["model"], "agent_options": options,
            "prompt_version": "+".join(versions.values()), "prompt_versions": versions}


def load_questions(config: RunConfig) -> list[tuple[Path, dict]]:
    if config.paraphrases is not None:
        return select_questions(load_paraphrases(config), config)
    filename = "questions_basic.jsonl" if config.warmup else "questions.jsonl"
    questions = []
    for path in sorted(config.directory.glob(f"*/{filename}")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            question = json.loads(line)
            if not config.kinds or question["kind"] in config.kinds:
                questions.append((path.parent, question))
    return select_questions(questions, config)


def select_questions(questions: list[tuple[Path, dict]], config: RunConfig) -> list[tuple[Path, dict]]:
    if config.per_kind is not None:
        counts = defaultdict(int)
        selected = []
        for path, question in questions:
            kind = question["kind"]
            if counts[kind] < config.per_kind:
                selected.append((path, question))
                counts[kind] += 1
        questions = selected
    return questions[:config.limit] if config.limit is not None else questions


def load_paraphrases(config: RunConfig) -> list[tuple[Path, dict]]:
    """Join source gold in the evaluator; inference receives only the new text."""
    sources = {}
    for filename in ("questions.jsonl", "questions_basic.jsonl"):
        for path in sorted(config.directory.glob(f"*/{filename}")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    source = json.loads(line)
                    if source["id"] in sources:
                        raise ValueError(f"Duplicate source question: {source['id']}")
                    sources[source["id"]] = (path.parent, source, filename == "questions_basic.jsonl")
    questions, seen = [], set()
    for line in config.paraphrases.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") in seen or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("Paraphrases need unique nonempty string IDs.")
        seen.add(row["id"])
        if row.get("source_id") not in sources:
            raise ValueError(f"Unknown paraphrase source: {row.get('source_id')}")
        path, source, warmup = sources[row["source_id"]]
        if row.get("kind") != source["kind"] or row.get("building_id") != path.name:
            raise ValueError(f"Paraphrase {row['id']} changes the source kind or building.")
        if not isinstance(row.get("question"), str) or not row["question"].strip():
            raise ValueError(f"Paraphrase {row['id']} has no text.")
        question = {"id": row["id"], "question": row["question"], "kind": source["kind"],
                    "source_id": source["id"], "warmup": warmup}
        if "answer" in source:
            question["answer"] = source["answer"]
        if not config.kinds or question["kind"] in config.kinds:
            questions.append((path, question))
    return questions


def checkpoint_key(question: dict, building_hash: str, context: dict) -> str:
    fields = {
        **context, "question_id": question["id"],
        "question_sha1": hashlib.sha1(question["question"].encode()).hexdigest(),
        "building_hash": building_hash,
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def load_checkpoint(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    rows = {}
    for index, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                # Repair an interrupted final write before appending more records.
                path.write_text("\n".join(lines[:index]) + ("\n" if index else ""), encoding="utf-8")
                break
            raise
        rows[row["key"]] = row
    if content and not content.endswith("\n") and len(rows) == len(lines):
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n")
    return rows


def infer(task: tuple[Path, str, str]) -> dict:
    directory, text, mode = task
    start = time.perf_counter()
    prediction = predict(directory, text, mode)
    return {**asdict(prediction), "ms": (time.perf_counter() - start) * 1000}


def predictions(config: RunConfig, questions: list[tuple[Path, dict]], context: dict) -> list[dict]:
    directory = OUTPUT / config.name
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint = directory / "checkpoint.jsonl"
    previous = load_checkpoint(checkpoint)
    remaining = None
    if config.max_cost is not None:
        remaining = config.max_cost - sum(row.get("cost", 0.0) for row in previous.values())
    configure_budget(remaining if remaining is not None and remaining > 0 else None)
    hashes = {path: content_hash(json.loads((path / "building.json").read_text(encoding="utf-8"))) for path in {path for path, _ in questions}}
    keys = [checkpoint_key(question, hashes[path], context) for path, question in questions]
    records = {}
    with ThreadPoolExecutor(max_workers=config.workers) as pool, checkpoint.open("a", encoding="utf-8") as handle:
        pending = {}
        for (path, question), key in zip(questions, keys):
            if key in previous:
                records[key] = previous[key]
            elif key not in pending.values():
                future = pool.submit(infer, (path, question["question"], config.mode))
                pending[future] = key
        for future in as_completed(pending):
            key = pending[future]
            row = {"key": key, **future.result()}
            records[key] = row
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
    print(f"Predictions: {len(pending)} computed, {len(keys) - len(pending)} resumed")
    return [records[key] for key in keys]


def score_warmup(question: dict, prediction: dict) -> bool:
    expected, kind, result = question["answer"], question["kind"], prediction["result"]
    if prediction["error"] or not prediction["reply"].startswith("Answer:"):
        return False
    if kind == "locate":
        return result.get("asset_id") == expected["asset_id"]
    if kind == "count":
        return result.get("value") == expected["count"]
    if kind in ROUTE_KINDS:
        computed = result if kind == "tour" else result["route"]
        if expected.get("reachable") is False:
            return computed.get("reachable") is False
        if computed.get("reachable") is False:
            return False
        optimal = expected["optimal_length_m"]
        return abs(computed["length_m"] - optimal) <= max(0.01 * optimal, 0.01)
    return False


def score_predictions(questions: list[tuple[Path, dict]], rows: list[dict], config: RunConfig) -> list[dict]:
    # Scorer import and gold access occur only after the prediction batch completes.
    from benchmark.score import score_reply

    scored = []
    for (_, question), row in zip(questions, rows):
        correct = None
        if "answer" in question:
            correct = score_warmup(question, row) if question.get("warmup", config.warmup) else score_reply(question["answer"], row["reply"])
        scored.append({**row, "id": question["id"], "expected_kind": question["kind"], "correct": correct})
    return scored


def make_report(rows: list[dict], context: dict) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[row["expected_kind"]].append(row)
    per_kind = {}
    for kind, members in sorted(groups.items()):
        per_kind[kind] = {
            "correct": sum(row["correct"] is True for row in members), "total": len(members),
            "errors": sum(row["error"] is not None for row in members),
            "unscored": sum(row["correct"] is None for row in members),
            "mean_ms": round(sum(row["ms"] for row in members) / len(members), 3),
            "tokens": sum(sum(row["tokens"].values()) for row in members),
            "cost": sum(row["cost"] for row in members),
            "mean_tool_calls": sum(row.get("tool_calls", 0) for row in members) / len(members),
        }
    by_method, by_model = defaultdict(list), defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(row)
        by_model[row["model"] or "none"].append(row)
    return {
        **context, "date": datetime.now(timezone.utc).isoformat(), "per_kind": per_kind,
        "correct": sum(row["correct"] is True for row in rows), "total": len(rows),
        "by_method": {key: group_metrics(members) for key, members in sorted(by_method.items())},
        "by_model": {key: group_metrics(members) for key, members in sorted(by_model.items())},
        "failures": [{"id": row["id"], "kind": row["expected_kind"], "error": row["error"], "reply": row["reply"]} for row in rows if row["correct"] is False],
    }


def group_metrics(rows: list[dict]) -> dict:
    return {"correct": sum(row["correct"] is True for row in rows), "total": len(rows),
            "mean_ms": sum(row["ms"] for row in rows) / len(rows),
            "mean_tool_calls": sum(row.get("tool_calls", 0) for row in rows) / len(rows),
            "tokens": {key: sum(row["tokens"].get(key, 0) for row in rows) for key in {key for row in rows for key in row["tokens"]}},
            "cost": sum(row["cost"] for row in rows)}


def run(config: RunConfig) -> dict:
    execution = execution_context(config.mode)
    if config.workers < 1 or config.limit is not None and config.limit < 0:
        raise ValueError("Workers must be positive and limit must be nonnegative.")
    if config.per_kind is not None and config.per_kind < 1:
        raise ValueError("Per-kind selection must be positive.")
    if Path(config.name).name != config.name or config.name in {"", ".", ".."}:
        raise ValueError("Run name must be one directory name.")
    questions = load_questions(config)
    if not questions:
        raise ValueError("No questions selected.")
    context = {"commit": revision(), "source_hash": source_hash(), "profile": current_profile(),
               **execution, "budget_limit": config.max_cost}
    configure_budget(config.max_cost)
    start = time.perf_counter()
    with paid_run_guard(OUTPUT / config.name / "paid-run.lock", config.max_cost):
        rows = score_predictions(questions, predictions(config, questions, context), config)
    report = make_report(rows, context)
    data = [(question["id"], question["question"], content_hash(json.loads((path / "building.json").read_text(encoding="utf-8")))) for path, question in questions]
    report["data_hash"] = hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()
    report["wall_seconds"] = time.perf_counter() - start
    directory = OUTPUT / config.name
    (directory / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (directory / "results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    for kind, result in report["per_kind"].items():
        print(f"{kind:26} {result['correct']:4}/{result['total']:<4} errors={result['errors']} mean_ms={result['mean_ms']:.3f} tokens={result['tokens']} cost=${result['cost']:.4f}")
    print(f"all {report['correct']}/{report['total']} · {report['wall_seconds']:.2f} s")
    if config.csv is not None:
        config.csv.parent.mkdir(parents=True, exist_ok=True)
        with config.csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["question_id", "answer"])
            writer.writerows((row["id"], row["reply"]) for row in rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--mode", choices=["template", "llm"], default="llm")
    parser.add_argument("--kinds", nargs="+", default=())
    parser.add_argument("--limit", type=int)
    parser.add_argument("--per-kind", type=int, help="Select the first N source questions of each kind")
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--paraphrases", type=Path, help="JSONL with source_id links to benchmark or warm-up questions")
    parser.add_argument("--max-cost", type=float, help="USD limit; write the allocation in STATUS before a paid run")
    arguments = parser.parse_args()
    try:
        run(RunConfig(**vars(arguments)))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()

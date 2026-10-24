"""Read provisional Sunday inputs and write isolated, checkpointed answer records."""

import argparse
import csv
import json
import math
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from agent.budget import paid_run_guard
from core.routing import route
from core.tour import plan_tour

from .agent import PROMPT_VERSION, Prediction, configure_budget, load_base, predict
from .llm_fallback import PROMPT_VERSION as FALLBACK_PROMPT_VERSION
from .run import checkpoint_key, load_checkpoint, revision, source_hash
from .serialize import serialize


@dataclass(frozen=True)
class Task:
    building: Path
    text: str
    constraints: dict | None = None
    max_cost: float | None = None


def load_input(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        content = path.read_text(encoding="utf-8-sig")
        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in content.splitlines() if line.strip()]
        else:
            rows = raw.get("questions", [raw]) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("Expected a question list or a questions object.")
    questions = []
    seen = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Question {index} must be an object.")
        question_id = row.get("id", row.get("question_id"))
        text = row.get("text", row.get("question"))
        if not isinstance(question_id, str) or not question_id or question_id in seen:
            raise ValueError(f"Question {index}: missing or duplicate string ID.")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Question {question_id}: missing question text.")
        constraints = row.get("constraints")
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError(f"Question {question_id}: constraints must be an object.")
        # Keep only inference-safe fields. Ignore any supplied answers or inputs.
        questions.append({"id": question_id, "question": text, "kind": row.get("kind"),
                          "constraints": constraints, "building_id": row.get("building_id")})
        seen.add(question_id)
    if not questions:
        raise ValueError("No questions supplied.")
    return questions


def make_questions(building: Path, output: Path) -> None:
    rows = []
    for filename in ("questions.jsonl", "questions_basic.jsonl"):
        path = building / filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                question = json.loads(line)
                rows.append({"id": question["id"], "text": question["question"], "kind": question["kind"]})
    if not rows:
        raise ValueError("No rehearsal questions found.")
    write_json(output, {"questions": rows})
    print(f"Converted {len(rows)} questions without answers or inputs")


def constrained_prediction(task: Task) -> Prediction:
    prediction = predict(task.building, task.text)
    if not task.constraints or prediction.error:
        return prediction
    if prediction.kind not in {"route", "route_step_free", "route_with_closure", "tour"}:
        # Interpretation can already have incurred a charge. Retain its usage
        # and cost when rejecting unsupported constraint semantics so a resumed
        # paid batch cannot mistakenly reclaim that allocation.
        return replace(prediction, reply="I cannot apply route constraints to this spatial question.", result={},
                       error="Explicit constraints require a route or tour question.")
    building, inputs = load_base(task.building), prediction.inputs
    parsed = {"step_free": prediction.kind == "route_step_free" or inputs.get("step_free", False),
              "closed": inputs.get("closed", []), "min_door_width_m": 0.0}
    constraints = {**parsed, **task.constraints}
    if prediction.kind == "tour":
        stops = inputs["stops"]
        result = plan_tour(building, stops[0], [{"target": stop} for stop in stops[1:]], constraints, keep_order=True)
        result = {**result, "reachable": not result.get("unreachable_stops")}
    else:
        result = {"route": route(building, inputs["start"], inputs["destination"], constraints)}
    prediction.result = result
    prediction.reply = serialize(building, prediction.kind, result)
    prediction.constraint_overrides = {key: {"parsed": parsed.get(key), "supplied": value} for key, value in task.constraints.items() if parsed.get(key) != value}
    return prediction


def child_infer(connection, task: Task) -> None:
    try:
        configure_budget(task.max_cost)
        result = asdict(constrained_prediction(task))
    except Exception as error:
        result = asdict(Prediction(reply=f"I could not compute this answer: {error}", error=f"{type(error).__name__}: {error}",
                                  method="error", cost=task.max_cost or 0.0))
    try:
        connection.send(result)
    finally:
        connection.close()


def isolated_infer(task: Task, timeout: float) -> dict:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=child_infer, args=(sender, task))
    process.start()
    sender.close()
    try:
        # Read before join: a large route may exceed the pipe buffer.
        if receiver.poll(timeout):
            try:
                return receiver.recv()
            except EOFError:
                return asdict(Prediction(reply="This question could not be computed.", error="Inference worker exited without a result.",
                                        method="error", cost=task.max_cost or 0.0))
        return asdict(Prediction(reply="This question exceeded the time limit.", error=f"Timeout after {timeout:g} seconds",
                                method="error", cost=task.max_cost or 0.0))
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join()


def route_record(route_result: dict) -> dict:
    reachable = route_result.get("reachable", True)
    return {"reachable": reachable, "space_path": route_result.get("space_path", []) if reachable else [],
            "node_path": route_result.get("node_path", []) if reachable else [],
            "element_path": route_result.get("element_path", []) if reachable else [],
            "length_m": route_result.get("length_m") if reachable else None}


def answer_record(question: dict, prediction: dict) -> dict:
    result = prediction["result"]
    kind = prediction["kind"] or question["kind"]
    computed_route = route_record(result["route"]) if "route" in result else None
    if kind == "tour" and result:
        computed_route = {**route_record(result), "legs": [route_record(leg) for leg in result.get("legs", [])]}
    return {"id": question["id"], "kind": kind, "answer_text": prediction["reply"],
            "value": result.get("value", result.get("area_m2")), "item_id": result.get("asset_id"),
            "space_id": result.get("space_id"), "route": computed_route, "error": prediction["error"],
            "constraints": question["constraints"], "constraints_applied": bool(question["constraints"]) and prediction["error"] is None,
            "constraint_overrides": prediction.get("constraint_overrides", {}),
            "method": prediction["method"], "model": prediction["model"],
            "tokens": prediction["tokens"], "cost": prediction["cost"]}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class Options:
    building: Path
    questions: Path
    output: Path
    csv: Path | None = None
    workers: int = 4
    timeout: float = 60
    max_cost: float | None = None


def run(options: Options) -> dict:
    if options.workers < 1 or not math.isfinite(options.timeout) or options.timeout <= 0:
        raise ValueError("Workers and timeout must be positive.")
    if options.max_cost is not None:
        from agent.budget import Budget
        Budget(options.max_cost)
    building = load_base(options.building)
    questions = load_input(options.questions)
    metadata = {"profile": building.profile, "commit": revision(), "building_id": building.id,
                "content_hash": building.content_hash, "source_hash": source_hash(),
                "prompt_version": PROMPT_VERSION + "+" + FALLBACK_PROMPT_VERSION, "model": ["claude-haiku-5-5", "claude-sonnet-5-5"] if options.max_cost else None,
                "max_cost": options.max_cost, "timeout": options.timeout}
    checkpoint = options.output.with_name(options.output.name + ".checkpoint.jsonl")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    previous = load_checkpoint(checkpoint)
    keys = [checkpoint_key(question, building.content_hash, {**metadata, "constraints": question["constraints"]}) for question in questions]
    records = {key: previous[key] for key in keys if key in previous}
    pending_count = len(keys) - len(records)
    allocation = max(0, options.max_cost - sum(row.get("cost", 0) for row in previous.values())) / max(1, pending_count) if options.max_cost else None
    with (paid_run_guard(options.output.with_name(options.output.name + ".paid-run.lock"), options.max_cost),
          ThreadPoolExecutor(max_workers=options.workers) as pool, checkpoint.open("a", encoding="utf-8") as handle):
        futures = {}
        for question, key in zip(questions, keys):
            if key in records:
                continue
            if question["building_id"] and question["building_id"] != building.id:
                records[key] = asdict(Prediction(reply="The question names a different building.", error="Building ID does not match the supplied building.", method="error"))
                handle.write(json.dumps({"key": key, **records[key]}, ensure_ascii=False) + "\n")
                handle.flush()
                continue
            task = Task(options.building, question["question"], question["constraints"], allocation or None)
            futures[pool.submit(isolated_infer, task, options.timeout)] = key
        for future in as_completed(futures):
            key = futures[future]
            try:
                records[key] = future.result()
            except Exception as error:
                records[key] = asdict(Prediction(reply="This question could not be computed.", error=f"Worker failure: {type(error).__name__}: {error}",
                                               method="error", cost=allocation or 0.0))
            handle.write(json.dumps({"key": key, **records[key]}, ensure_ascii=False) + "\n")
            handle.flush()
    answers = [answer_record(question, records[key]) for question, key in zip(questions, keys)]
    output = {**metadata, "answers": answers}
    write_json(options.output, output)
    if options.csv is not None:
        options.csv.parent.mkdir(parents=True, exist_ok=True)
        with options.csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["question_id", "answer"])
            writer.writerows((answer["id"], answer["answer_text"]) for answer in answers)
    answered = sum(answer["answer_text"].startswith("Answer:") for answer in answers)
    print(f"answered={answered} unanswered={len(answers) - answered} errors={sum(answer['error'] is not None for answer in answers)}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("building", type=Path, nargs="?")
    parser.add_argument("questions", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--max-cost", type=float)
    parser.add_argument("--make-questions", type=Path, nargs=2, metavar=("BUILDING", "OUTPUT"))
    arguments = parser.parse_args()
    try:
        if arguments.make_questions:
            make_questions(*arguments.make_questions)
        elif all((arguments.building, arguments.questions, arguments.output)):
            del arguments.make_questions
            run(Options(**vars(arguments)))
        else:
            parser.error("Supply building, questions and output, or --make-questions BUILDING OUTPUT.")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()

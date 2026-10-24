# L01: Benchmark M1 and the test submission (target G2, 23:30 CEST)

## 1. Outcome and user value

`bench.agent:answer(building_directory, question_text)` answers every published question kind from the question text alone, with a correct `Answer:` line, without needing an API key. The validated 145-row test CSV is committed early, so the 55-point submission is safe for the rest of the weekend.

## 2. Starting state

- Kit evaluator and scorer exist (`benchmark/evaluate.py` supports `--agent module:function` and `--submission-csv`). Kit oracle 369/369 (warm-up tools).
- Reference copy of the sibling template parser: `research/sibling-repo-2026-10-24/core/questions.py` (nine benchmark templates; raises on unknown wording or ambiguous labels; never guesses). Measured with the ported solvers in a scratch copy: dev 138/138 from text, train 510/517 (7 ambiguous labels), all 145 test questions parse.
- `core.spatial.solve` / `core.resolve` / `core.load_building` arrive from Hagen's codex around 22:40 CEST (H01 step 2). Until then build everything else; for the warm-up kinds you can test against the kit `BuildingMap` directly.
- Read: CONTRACTS §4 (inputs table), §12, §13; kit README §4 and §6.

## 3. Scope and ownership

Create and own: `bench/__init__.py`, `bench/templates.py` (port + warm-up templates), `bench/serialize.py`, `bench/agent.py`, `bench/run.py`, `bench/validate_submission.py`, `tests/bench/`, `submissions/test_answers.csv`, `BENCHMARK.md` (draft). Do not touch `benchmark/` (official), `core/`.

## 4. Implementation obligations

1. **`bench/templates.py`:** port `parse_question(core, text) -> (kind, inputs)` from the reference copy unchanged in behaviour for the nine kinds (floor phrase parsing "ground floor / floor N / basement N", full-label entity resolution "Name (Floor)", the `" and "` pair splitting for `straight_line_3d` and `what_if_door`, room types by underscore/space normalisation, asset types by `[\s-]+ → _`). Use `core.resolve` for the final fallback instead of the starter `resolve_space`. Add the six warm-up templates from `data/*/*/questions_basic.jsonl` wordings (inspect a sample per kind in train and dev; examples: "Where is the lectern?", "How many toilet items are on the floor 2?", "How do I get from A (Floor) to B (Floor)?", "Is there a step-free route from A to B?", "Lift 1 is closed for maintenance. How do I get from A to B?", "Starting at A, visit B, then C in this order. What is the route?"). For `locate`, verify on train+dev that the type or name in the question identifies exactly one asset; if not, return ambiguity (never pick by hidden IDs).
2. **`bench/serialize.py`:** one function per kind implementing CONTRACTS §13 from the typed `solve` result. A short first sentence is allowed ("The largest office on floor 1 is Office 1.14."). Numeric lines contain exactly one number. Unit test against `benchmark.score.score_reply` with synthetic answers, including a room whose ref contains digits.
3. **`bench/agent.py`:** `answer(building_directory: Path, question_text: str) -> str` = load (cached) → template parse → solve → serialize. On `MapError`/`CoreError` from parsing: call the LLM fallback hook (L03; until then return `"I could not determine a unique answer: <reason>. Please name the exact room."` **without** an `Answer:` line). Catch solver errors per question; never crash the whole run.
4. **Inference isolation test** (`tests/bench/test_isolation.py`): while `answer()` runs on a dev question, patch `builtins.open`/`Path.read_text`/`Path.open` to fail on any path whose name starts with `questions`; the call must still succeed. Also assert that importing `bench.agent` does not import `benchmark.score` (only `bench.run` may use the scorer, after predictions are complete).
5. **`bench/run.py`:** `uv run python -m bench.run <split_dir> --name <run> [--csv path] [--workers 4] [--mode hybrid|template|llm] [--kinds ...] [--limit n] [--warmup]`. Per-question checkpoint lines in `agent_output/bench/<run>/checkpoint.jsonl` keyed by `(question id, sha1 of text, building content_hash, git commit, profile, model, prompt_version)`; resume skips matching keys only. Per-kind report (correct/total, errors, mean ms, tokens, cost) printed and written as JSON. Scoring uses `benchmark.score.score_reply` for benchmark kinds and the kit warm-up rules for `--warmup` (locate asset ID, count number, route length within 1 %, unreachable).
6. **`bench/validate_submission.py`:** CSV vs template: exactly the template IDs once each, header `question_id,answer`, UTF-8, ≤ 5 MB, each answer contains an `Answer:` line; exit non-zero with a list of problems.
7. **Submission:** generate `submissions/test_answers.csv` with the official evaluator (independent of your runner) and validate it. Commit it with the SHA and command in `BENCHMARK.md`. Remove nothing from `.gitignore`; `submissions/` is a new tracked folder.

## 5. Interfaces and fixtures

- Consumes CONTRACTS §4 `solve` inputs exactly as in the table; if a field name differs in Hagen's push, raise a change request instead of adapting silently.
- Produces `bench.agent:answer` (CONTRACTS §12) for the evaluator and for Hagen's `core.evaluate --check text`.

## 6. Execution order

1. (20 min) `serialize.py` + `validate_submission.py` + tests (no core needed).
2. (20 min) `templates.py` port; warm-up templates against `starter_agent.building_map.BuildingMap`; tests on a few dev buildings.
3. (10 min) `agent.py` + isolation test; wire to `core` as soon as Hagen pushes (fetch his branch: `git fetch origin && git merge origin/hagen/core` is allowed for an unmerged dependency; note it in STATUS).
4. (15 min) `run.py` with checkpoints; dev run; train run.
5. (10 min) official evaluator dev and test; CSV; validation; `BENCHMARK.md` draft; push; ask the captain to merge at G2.

## 7. Acceptance

- `uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer --name dev-official` → 138/138 (paste the table).
- `uv run python -m bench.run data/train --name train-template --mode template` → 510/517 or better, every miss classified (ambiguous label vs bug).
- `uv run python -m bench.run data/dev --warmup --name dev-warmup` → 369/369 or every miss explained.
- `uv run python -m bench.validate_submission submissions/test_answers.csv data/test/submission_template.csv` → ok.
- `uv run pytest -q tests/bench` green. No `ANTHROPIC_API_KEY` set during these runs (state it in STATUS).
- Review: Hagen's codex runs the dev command on his checkout.

## 8. Collaboration and Git

Branch `lenard/bench`. Push after steps 1, 3, 5. Merge window G2 23:30 CEST (after Hagen's core is merged at G1).

## 9. Completion report

SHA; tables (dev official, train template, warm-up); CSV path and validator output; known misses with IDs and reasons; isolation test result; next: L02 (chat agent, needed at G3).

## 10. Blocked-work behaviour

Core late: finish steps 1, 2, 4 against the reference copy through a temporary adapter module `bench/_sibling_adapter.py` that imports the reference solvers with the A5 patch (see Hagen's H01 §4.2); delete it when `core` lands. Never commit a CSV produced by the kit-1.0 sibling code or the old `../repo/submissions/team_answers.csv`.

# L03: LLM fallback for new wording and the Sunday adapter (target 01:30 CEST; robustness runs may continue in the stretch window)

## 1. Outcome and user value

The Sunday building may come with new wording ("same distribution", but not the same sentences). When the template parser does not recognise a question, a bounded Claude agent turns the text into validated typed inputs, the same solver computes, and the serializer answers. The Sunday command produces the organizers' answer file with one documented command and no manual steps.

## 2. Starting state

- L01 merged: hybrid `answer()` with a fallback hook; runner with checkpoints. L02 (chat) is live; the A/B test (end of L02) interrupts this milestone around 01:30 CEST.
- API facts verified on 24 Oct 2026 with the bundled Claude API reference: model IDs `claude-haiku-5-5` ($0.10/$0.50 per MTok, effort default medium), `claude-sonnet-5-5` ($2/$10; cache read $0.20); `temperature`, `top_p`, `top_k` return HTTP 400 on every model since 21 Oct 2026; forced `tool_choice` (`any`/`tool`) returns 400 on Sonnet 5.5; `thinking: {"type": "disabled"}` returns 400 on Sonnet 5.5; set effort with `output_config={"effort": "low"}`; `strict: true` on tool definitions with `additionalProperties: false`; Python tool runner: `@beta_tool` + `client.beta.messages.tool_runner(...)`; Haiku 5.5 has no server-side refusal fallback. The starter `starter_agent/agent.py` shows a working tool-runner loop and usage tracking.
- Sunday format is unknown (PDF: `questions.json` → `answers.json` with item/room ID, route as node IDs, length; README: CSV; route announcement: ordered list of spaces). CONTRACTS §12 defines a provisional schema.
- Read: MASTER_PLAN §4.2; CONTRACTS §12–§14.

## 3. Scope and ownership

Own `bench/llm_fallback.py`, `bench/run_benchmark.py`, `bench/paraphrases/dev_paraphrases.jsonl`, `tests/bench/`, `BENCHMARK.md`. Uses `core` only through `solve`, `resolve`, `load_building`.

## 4. Implementation obligations

1. **Fallback agent** (`bench/llm_fallback.py`): tools (all `strict: true`):
   - `building_facts()` → floors (id, level, name), room types present, asset types present, connector names, entrance spaces (compact, no polygons);
   - `resolve(text, kind)` → CONTRACTS §4 result;
   - `solve(kind, inputs)` → typed result or a validation error message (lets the model repair once);
   - `submit_answer(kind, inputs)` → re-runs `solve`, stores the result, ends the loop.
   System prompt: the kind catalogue with one-line definitions and the exact input fields (from CONTRACTS §4), rules from README §4 (e.g. errand allows stairs; wide delivery is step-free with lifts allowed; counts exclude corridors/stairs/lifts where the question says so), "never compute numbers yourself, never answer without `submit_answer`, ask nothing (benchmark mode)". Cache the system prompt and tools (`cache_control` on the last stable block; verify `cache_read_input_tokens > 0` on the second call). Bounds: 8 iterations, 60 s, `max_tokens` 4000. Model order: `claude-haiku-5-5` effort `low`; if no valid `submit_answer`, one retry with `claude-sonnet-5-5` effort `low` (+ `fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). Handle `stop_reason == "refusal"` and API errors per question. The serializer, not the model, writes the `Answer:` line.
2. **Paraphrase set** (`bench/paraphrases/dev_paraphrases.jsonl`): at least 4 paraphrases per benchmark kind and 2 per warm-up kind, each with `source_id` pointing to a dev question; meaning preserved exactly (same rooms, floors, constraints, same final instruction format). Write them yourself (you are an LLM coding agent; this is test data). The scorer uses the source question's answer.
3. **Measurements** (budget first, e.g. `--max-cost 5`): (a) `--mode hybrid` on paraphrases (how often the template path still catches them; fallback accuracy on the rest); (b) `--mode llm` on 2 original dev questions per kind (pure LLM path). Report per-kind accuracy, mean tool calls, latency, tokens, cost per question, by model. Decide Haiku vs Sonnet as fallback default by the numbers; record in `BENCHMARK.md`.
4. **Sunday adapter** (`bench/run_benchmark.py <building_dir> <questions> <answers.json> [--csv out.csv] [--workers 4]`): tolerant input (JSON list, `{"questions": [...]}`, JSONL, or the kit CSV; fields `id` and `text|question`, optional `kind` and `constraints`); output per CONTRACTS §12 including `route` with `space_path`, `node_path`, `element_path`, `length_m` for route/tour kinds; `item_id`/`space_id` for locate and room answers; also CSV. Per-question timeout and checkpoint; a crash in one question never loses the others; final summary line with counts of answered, unanswered (no `Answer:` line) and errors. Respect question-supplied `constraints` by merging them into the parsed inputs (explicit constraints win; record when they differ).
5. **Rehearsal input:** a converter `bench/run_benchmark.py --make-questions <split_building_dir> <out.json>` that writes a questions file from a kit building's `questions.jsonl` and `questions_basic.jsonl` **without answers or inputs**, so the Sunday path can be rehearsed on dev buildings.
6. **`BENCHMARK.md`** (draft now, final in L04): single commands for test CSV and Sunday; what needs a key (only the fallback); models and prompt version; measured tables with commit and date; limits (ambiguous labels, provisional schema).

## 5. Interfaces and fixtures

CONTRACTS §12 output schema is yours; if the organizers publish theirs, only this adapter changes (update CONTRACTS §12 and its changelog).

## 6. Execution order

Fallback agent with two tools (`resolve`, `submit_answer`) end-to-end on 3 paraphrases (30 min) → full tool set + bounds + caching (20 min) → Sunday adapter + converter + rehearsal on `data/dev/proc-factory-dev-003` (25 min) → paraphrase set (15 min) → measurement runs (15 min, budgeted) → `BENCHMARK.md` draft.

## 7. Acceptance

- `uv run python -m bench.run_benchmark data/dev/proc-factory-dev-003 /tmp/q.json /tmp/a.json --csv /tmp/a.csv` on a converted file: every question answered or explicitly unanswered; route entries carry `space_path`/`element_path` that match the kit warm-up answers (spot-check 5).
- Paraphrase results table in STATUS and `BENCHMARK.md` with model, cost and latency; no claim beyond the measured numbers.
- Fallback never emits an `Answer:` line that was not produced by `solve` + serializer (unit test with a stubbed client).
- `uv run pytest -q tests/bench` green without network (stub the client in tests).

## 8. Collaboration and Git

Branch `lenard/bench`; merge window G5 (02:15 CEST) or the stretch window. Tell Manuel's codex if the fallback needs new environment variables.

## 9. Completion report

SHA; measured tables; chosen fallback model and why; Sunday adapter command and rehearsal output; costs spent; open risks.

## 10. Blocked-work behaviour

No API key or credits: ship the adapter and the stubbed tests, mark the fallback "not measured", and keep the template path as the documented Sunday command. Never estimate accuracy you did not measure.

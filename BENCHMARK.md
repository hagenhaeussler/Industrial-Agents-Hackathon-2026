# Reproduce the building answers

The deterministic agent answers the published English templates from question text and `building.json`. It needs no API key. The solver uses the unchanged kit 1.1.0 route model, profile `kit_1_1_0`.

## Completion audit, 24 Oct 2026

Rechecked the integrated `16d64cc` base with the fallback compatibility and Sunday accounting fixes described here. Offline runs explicitly used `PYTHON_DOTENV_DISABLED=1` and empty `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY` and `OPENAI_API_KEY`; no provider calls or charges were incurred by this audit.

- `python -m benchmark.evaluate data/dev --agent bench.agent:answer --name completion-audit-dev`: **138/138**, all nine kinds correct.
- `python -m benchmark.evaluate data/test --agent bench.agent:answer --name completion-audit-test --submission-csv /private/tmp/tyb-completion-test-answers.csv`: **145 rows**, validator passes, byte-identical to `submissions/test_answers.csv` with the SHA-256 below. Hidden test accuracy remains unknown.
- `python -m bench.run_benchmark --make-questions data/dev/proc-factory-dev-003 /private/tmp/tyb-completion-sunday-questions.json`, then `python -m bench.run_benchmark data/dev/proc-factory-dev-003 /private/tmp/tyb-completion-sunday-questions.json /private/tmp/tyb-completion-sunday-answers.json --csv /private/tmp/tyb-completion-sunday-answers.csv`: **15 answered / 0 unanswered / 0 errors**. Independent post-inference comparison found all **seven route/tour legs** have exact space/element paths and lengths within 0.01 m of the warm-up reference.
- `pytest -q tests/bench tests/agent`: **150 passed in 2.75 s**. The fallback now sends a small strict envelope (`kind`, `inputs_json`) for `solve` and `submit_answer`; it decodes an object and runs unchanged core validation before any submission. The full typed field catalogue remains in the system prompt. This replaces duplicated 15-way unions which passed public field/union counts but failed the live provider's internal grammar size limit before token generation. Tool schemas total 2,054 JSON bytes with zero optional fields and zero unions. The existing SDK grammar adaptation still handles unsupported field bounds in other tools. A real-SDK mocked transport inspects the actual request JSON; invalid JSON, non-object values, kind/field mismatches and shared repair limits are covered. Rejected unsupported Sunday constraints retain any model usage/cost so checkpoints do not refund spent budget.

The fallback, adapter, submission and authored 48-question paraphrase set are present. Live fallback accuracy/cache measurements and the three-model human voice A/B comparison remain unmeasured. Organizer schema, unseen Sunday building/questions and the final freeze/release run require the actual event inputs. Existing live app/provider smoke evidence is separate in [`docs/live-provider-setup.md`](docs/live-provider-setup.md); the historical measurements below describe their own dated revisions.

## Test submission

From the repository root:

```sh
uv sync
env -u ANTHROPIC_API_KEY uv run python -m benchmark.evaluate data/test --agent bench.agent:answer --name test-official --submission-csv submissions/test_answers.csv
uv run python -m bench.validate_submission submissions/test_answers.csv data/test/submission_template.csv
```

The official evaluator produced the committed CSV, not the custom runner. The CSV has 145 answers and is 6,337 bytes. Its SHA-256 is `d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f`. Public test answers are hidden. Generation and format validation do not establish test accuracy.

## Measured results

Measured 24 Oct 2026 on source commit `54904dd8d8247a2bccfd4a31bc50abcea15e3dad`, including Hagen's core checkpoint `cdd4f67`, contract C3. Python 3.14.7. No `ANTHROPIC_API_KEY` was set. No model calls, tokens or charges.

| Kind | Dev, official evaluator | Train, template runner |
|---|---:|---:|
| errand | 19/19 | 73/74 |
| floor_area_total | 31/31 | 150/150 |
| largest_room | 20/20 | 76/76 |
| room_stacked | 9/9 | 15/17 |
| shared_walls_count | 24/24 | 117/119 |
| step_free_reachable_count | 1/1 | 1/1 |
| straight_line_3d | 13/13 | 15/17 |
| what_if_door | 2/2 | 2/2 |
| wide_delivery_count | 19/19 | 61/61 |
| Total | 138/138 | 510/517 |

Commands used:

```sh
env -u ANTHROPIC_API_KEY uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer --name dev-official
env -u ANTHROPIC_API_KEY uv run python -m bench.run data/train --name train-template --mode template
env -u ANTHROPIC_API_KEY uv run python -m bench.run data/dev --warmup --name dev-warmup --mode template
```

The train run took 9.16 s. The dev warm-up run took 22.79 s. These are local batch times with four workers, not live app latency claims.

| Warm-up kind | Correct/total |
|---|---:|
| count | 40/40 |
| locate | 100/100 |
| route | 120/120 |
| route_step_free | 40/40 |
| route_with_closure | 28/29 |
| tour | 40/40 |
| Total | 368/369 |

## Known ambiguities

No answer is committed for an ambiguous question. We do not choose a hidden entity ID.

| Question IDs | Reason |
|---|---|
| `osm-way37850565-H02`, `-H03`, `-H04` | Several rooms share the name Büro on the same floor. |
| `osm-way52060470-H06` | Two rooms share Genusswerk (Floor 1). |
| `osm-way58216509-H04`, `-H05`, `-H06` | Duplicate full room labels on floor 2. |
| `osm-way27917482-Q09` (dev warm-up) | Three rooms share Generic room 03.08.033 (Floor 3). |

## Isolation and checkpoints

`bench.agent` does not import the scorer or open question files. Its public entry point accepts only a building directory and question text. The isolation test blocks `open`, `Path.open` and `Path.read_text` for question files while the real loader, parser, solver and serializer run.

The custom runner completes predictions before it imports the scorer or accesses reference answers. It saves each completed prediction under `agent_output/bench/<name>/checkpoint.jsonl`. Resume requires the same question ID, text SHA-1, building content hash, Git commit, source hash, profile, mode, model and prompt version. Changed expected answers are scored again without rerunning unchanged inference. The source hash also protects runs made with local code edits.

Each run writes `report.json` and `results.jsonl`. Reports include per-kind accuracy, errors, mean time, tokens, cost, source revision and data hash. Unknown test answers remain unscored.

## Earlier gate checks

`env -u ANTHROPIC_API_KEY scripts/check.sh` passed locally: 240 Python tests (including prepared L02 agent tests), kit oracle 369/369, core text dev 138/138, 39 Bun tests, TypeScript/Vite production build and the device-gate bundle. Environment: uv 0.11.27, Python 3.14.7. A fresh Linux rehearsal is still due at G6.

The Sunday input format remains provisional. L04 must rerun the submission on the captain's release commit and verify the final file. A fresh Linux rehearsal, organizer schema, release tag and unseen building are not available in this checkpoint.


## Sunday adapter

This command uses only the template path when no budget is configured. A key alone cannot enable model calls.

```sh
env -u ANTHROPIC_API_KEY uv run python -m bench.run_benchmark BUILDING_DIR QUESTIONS_FILE submissions/sunday_answers.json --csv submissions/sunday_answers.csv
```

Rehearsal commands actually run on 24 Oct 2026, after integrating C5 main `a8be9ec` at local merge `50b16ea`:

```sh
env -u ANTHROPIC_API_KEY uv run python -m bench.run_benchmark --make-questions data/dev/proc-factory-dev-003 /tmp/tyb-sunday-q.json
env -u ANTHROPIC_API_KEY uv run python -m bench.run_benchmark data/dev/proc-factory-dev-003 /tmp/tyb-sunday-q.json /tmp/tyb-sunday-c5-a.json --csv /tmp/tyb-sunday-c5-a.csv
```

Result: 15 answered, 0 unanswered, 0 errors. Independently compared all seven route/tour legs with warm-up gold: exact `space_path` and `element_path`, lengths within 0.01 m. Converter output has only ID, text and kind. The adapter discards supplied gold `answer` and `inputs` fields.

Inputs can be a JSON list, a questions object, JSONL (including one record), or the kit CSV. Outputs follow provisional CONTRACTS §12. Routes carry node, space and element paths, plus length. Tours include legs. Unreachable routes have empty paths and null length. Each question runs in a separate process with a hard timeout, 60 seconds by default; one failed question does not stop the batch. Output JSON is written atomically. Completed questions are checkpointed beside the output file.

Explicit route/tour constraints override parsed constraints and are recorded under `constraint_overrides`. Unknown fields or invalid values are rejected by core. **Limit:** explicit constraints on other spatial kinds return an unanswered error. Their meaning is not defined by the current solver interface; no constraint is silently ignored. The organizers' final schema may need a change here.

## New wording and fallback

The authored set has 48 paraphrases across all 15 kinds: four per benchmark kind and two per warm-up kind. Each source link preserves the building, rooms, floors and constraints. Only the evaluator joins the source answer. Inference receives the new question text and the building.

```sh
env -u ANTHROPIC_API_KEY uv run python -m bench.run data/dev --name dev-paraphrases-template-c5 --mode template --paraphrases bench/paraphrases/dev_paraphrases.jsonl
```

Measured on 24 Oct 2026, after merge `50b16ea`, with this checkpoint's source code. Full source hash is stored in the report. Four workers. Batch time 1.61 s. No model calls, tokens or cost. All 48 replies were explicitly unanswered because the template parser did not recognize the wording. This result measures the template boundary. It does not measure fallback accuracy.

| Kind | Template correct/total | Mean time, ms |
|---|---:|---:|
| count | 0/2 | 71.76 |
| errand | 0/4 | 70.70 |
| floor_area_total | 0/4 | 191.85 |
| largest_room | 0/4 | 191.04 |
| locate | 0/2 | 46.12 |
| room_stacked | 0/4 | 37.35 |
| route | 0/2 | 94.74 |
| route_step_free | 0/2 | 57.96 |
| route_with_closure | 0/2 | 39.93 |
| shared_walls_count | 0/4 | 90.84 |
| step_free_reachable_count | 0/4 | 56.83 |
| straight_line_3d | 0/4 | 113.57 |
| tour | 0/2 | 72.88 |
| what_if_door | 0/4 | 207.63 |
| wide_delivery_count | 0/4 | 35.58 |

The fallback is implemented and tested offline. It starts with `claude-haiku-5-5`, then permits one `claude-sonnet-5-5` attempt. Both use low effort and automatic tool choice. Tools are `building_facts`, `resolve`, `solve` and `submit_answer`. Only a validated `submit_answer` calls the solver and serializer to store the final answer. Model prose cannot create an answer. There are at most eight model responses, 4,000 output tokens per request, deadline checks at 60 seconds and a 7.5-second request timeout. The Sunday process supplies the hard wall-clock timeout; the plain in-process fallback has deadline checks between calls.

System and tool cache markers are configured. Cache hits have not been measured. Current prompt version: `benchmark-fallback-v2` (small JSON-string envelope with typed local validation), templates `templates-v1`, chat `chat-v1`. Historical results above used fallback v1. Haiku is the planned first attempt, not a measured winner.

| Required live measurement | Status |
|---|---|
| Hybrid paraphrases | Not run; budget pending |
| Pure model path, two original questions per kind | Not run; budget pending |
| Haiku versus Sonnet accuracy, latency, tokens and cost | Not measured |
| Cache read on the second request | Not measured |
| Voice model comparison with a human | Not run; provider setup and human pending |

For a future authorized run, `bench.run` supports `--mode hybrid` or `--mode llm`, `--max-cost DOLLARS`, `--paraphrases PATH` and `--per-kind 2`. Run original benchmark and `--warmup` selections separately. The available dev set has only one step-free reachability source question. Reports break down kind, method and final model, with usage and cost retained across escalation. No paid run is approved or included here.

A paid batch needs both `ANTHROPIC_API_KEY` and an explicit positive `--max-cost`, with its allocation written in STATUS before execution. Workers share a conservative budget; Sunday process workers receive fixed shares. Completed checkpoint cost is deducted before new work. Failed API calls without usage retain their reservation. Timed-out or crashed Sunday workers retain their full allocation as an upper bound, not a measured charge. SDK retries are disabled.

An active paid-run marker prevents concurrent runs with the same name/output. If the parent process stops before checkpointing, the marker remains and blocks paid resume. Reconcile spend and obtain a new written allocation before choosing a new run name/output. Do not remove a marker to repeat uncertain charges. Successfully completed batches release the marker and can resume from their recorded checkpoints.

## Historical C5 verification and release gates

Final check after C5 integration: `env -u ANTHROPIC_API_KEY scripts/check.sh` passed with 340 Python tests in 30.10 s, kit oracle 369/369, core text dev 138/138, 39 Bun tests, TypeScript/Vite build and device-gate bundle. The focused agent/bench suite passed 125 tests. The real Anthropic SDK tool loop was tested with mocked HTTP transport, without network access. Local logs: `/tmp/tyb-check-final.log` and `/tmp/tyb-agent-bench-final.log`. No kit, core, server or dependency files were edited by this builder.

C5 resolves the exact-name registry collision found during chat testing. The original regression now passes without changing its expectation. Chat integration tests use an offline model client and the real registry; live language understanding remains unmeasured. Voice prompts are available in `agent/voice_prompts/`; human-owned dashboard configuration is unchanged.

L04 remains gated on the captain's fresh Linux clone, release tag, organizer format and unseen building. These local checks are not the Sunday release run. No deployment is claimed.

## Integrated live fallback verification (24 October 2026)

Human authorization: $5 total smoke budget in the integration chat. This run allocated at most $1 ($0.40 paraphrases, $0.30 originals, $0.30 warm-up), shared with previous provider tests and the next deployment. Keys stayed in ignored server-side environment files.

An initial live attempt failed before generation: Anthropic rejected the 9,439-byte overlapping strict input unions as a compiled grammar that was too large. All 77 checkpoints had zero generated tokens and zero tool calls; provider400 or budget-blocked outcomes were retained, not reported as an accuracy result. A direct sanitized diagnostic confirmed the cause. The revised strict envelope `{kind, inputs_json}` is 2,054 bytes, has no unions, and decodes only an object before the unchanged core validation and serializer. A single diagnostic returned200.

The v2 batches ran with two workers each on base main `16d64cc` plus the source hash below. They receive question text and building data; evaluator gold is joined only after predictions.

| Selection | Correct / total | Batch seconds | App-metered USD |
|---|---:|---:|---:|
| Hybrid authored paraphrases (all15kinds) | 48/48 | 143.48 | 0.083319 |
| Pure LLM originals (two per benchmark kind where available) | 17/17 | 49.44 | 0.024177 |
| Pure LLM warm-up (two per kind) | 12/12 | 36.93 | 0.041307 |

Combined **77/77**, no unanswered cases. App-metered total **$0.14880213**; the separate schema diagnostic cost $0.000162525. Observed cache reads: **681,072 input tokens**. Source hash: `2ed294557604e873774541cbf5a57662d7c7c00653b5e5495b8ebc0af4a8aa74`. Prompt: `templates-v1+benchmark-fallback-v2`. Reports and per-kind/model/token/cost tables: ignored `agent_output/bench/swarm-*-live-v2-20261024/`; compact summary: `agent_output/reports/core/swarm-live-benchmark-summary.json`.

Haiku is attempted first with one Sonnet escalation. Grouping by the final model is not a matched A/B comparison and does not establish a model winner. Typical completed question times are several seconds; this does not certify the three-second spoken-route target or a real voice conversation. The unseen Sunday building, organizer output format and human voice/device gates remain open. Earlier “not run” tables above are historical checkpoints; this section supersedes their fallback/cache measurement status.

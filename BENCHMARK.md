# Reproduce the building answers

The deterministic agent answers the published English templates from question text and `building.json`. It needs no API key. The solver uses the unchanged kit 1.1.0 route model, profile `kit_1_1_0`.

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

## Remaining release work

`env -u ANTHROPIC_API_KEY scripts/check.sh` passed locally: 240 Python tests (including prepared L02 agent tests), kit oracle 369/369, core text dev 138/138, 39 Bun tests, TypeScript/Vite production build and the device-gate bundle. Environment: uv 0.11.27, Python 3.14.7. A fresh Linux rehearsal is still due at G6.

The Sunday input format is provisional until the organizers confirm it. L03 supplies the separate Sunday adapter and bounded language fallback. L04 must rerun the submission on the captain's release commit and verify the final file. No paid run budget is approved. Language model and voice accuracy are not measured.

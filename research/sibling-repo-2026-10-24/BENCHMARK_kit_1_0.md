# Deterministic spatial benchmark

All nine published benchmark kinds run locally using building.json, NetworkX and
Shapely. No LLM, GPU, network, API key or model weights are needed for inference.
The existing conversational starter also exposes these operations as spatial_query.

## Run

Run from this repository, using the existing environment or `uv sync` first:

```bash
# All train/dev tool calculations; nonzero exit if any structured-input case fails.
uv run python -m core.evaluate data/train data/dev --check structured

# Strict text-only validation of dev, including parsing and the official scorer.
uv run python -m core.evaluate data/dev --check text

# Synthetic edge cases, agent-tool wiring and all 655 train/dev regressions.
uv run python -m unittest discover -s tests -v
```

With an already installed environment, replace `uv run python` with `.venv/bin/python`.
Detailed predictions and summaries are written to `reports/spatial/`. The prediction
path receives only building data and question text. Published `inputs` are used
separately for tool-only validation; reference answers are used only by the scorer.
Reports do not copy the reference answers.

For compatibility with the unmodified official runner:

```bash
uv run python -m benchmark.evaluate data/dev --agent core.questions:answer --name spatial-dev
uv run python -m benchmark.evaluate data/train --agent core.questions:answer --name spatial-train

# Test submission (executed after train/dev development was complete).
uv run python -m benchmark.evaluate data/test --agent core.questions:answer --name spatial-test-official --submission-csv submissions/team_answers.csv
```

The official runner saves replies and prints scores. Its exit code does not enforce
a passing score; use core.evaluate for a strict check. The text adapter supports
the published English templates, not arbitrary conversation. Unsupported phrasing
and ambiguous labels produce a clarification without an Answer line. The live LLM
can instead resolve IDs interactively and invoke the structured spatial_query tool.

## Results, 24 October 2026

| Kind | Train, structured | Dev, structured | Train, text | Dev, text |
|---|---:|---:|---:|---:|
| largest_room | 76/76 | 20/20 | 76/76 | 20/20 |
| floor_area_total | 150/150 | 31/31 | 150/150 | 31/31 |
| errand | 74/74 | 19/19 | 73/74 | 19/19 |
| wide_delivery_count | 61/61 | 19/19 | 61/61 | 19/19 |
| step_free_reachable_count | 1/1 | 1/1 | 1/1 | 1/1 |
| room_stacked | 17/17 | 9/9 | 15/17 | 9/9 |
| shared_walls_count | 119/119 | 24/24 | 117/119 | 24/24 |
| straight_line_3d | 17/17 | 13/13 | 15/17 | 13/13 |
| what_if_door | 2/2 | 2/2 | 2/2 | 2/2 |
| **Total** | **517/517** | **138/138** | **510/517 (98.65%)** | **138/138** |

200 train buildings and 40 dev buildings. All cases are scored with the supplied
benchmark.score.score_reply implementation. The official runner independently
produced the same text-only scores. These are deterministic tool/template results,
not measured success rates of the conversational LLM or unseen buildings.

Seven train cases have ambiguous labels on the same floor:

- osm-way37850565-H02, H03, H04
- osm-way52060470-H06
- osm-way58216509-H04, H05, H06

For example, the two questions H02/H03 in osm-way37850565 have identical text
(`Büro (Ground floor)`) but different start-space IDs and expected destination rooms.
The text-only adapter refuses to choose by hidden input IDs, question IDs, answer
keys or cached outputs. With the published start IDs both calculations pass.
Consequently, strict text-mode evaluation of train intentionally exits nonzero.

## Local calibration rather than weight training

The core implements algorithms and has no trainable weights. Local development
used train examples to check the rules and dev to verify them; both sets were
inspected during debugging, so dev is not an untouched holdout. No test-set tuning,
new neural model, downloaded checkpoint or fine-tuning is involved. Reported 100%
tool accuracy must not be interpreted as generalisation evidence for an LLM.

The regression suite includes 100 seeded variations of scale, translation and door
widths to check geometry and routing invariants, as well as targeted cases for
parallel connectors, closures, fractional wall gaps, split polygon rings,
order-independent what-if doors, ambiguous labels, names containing "and", arbitrary
IDs, state preservation and live agent-tool integration.

## Tool API

```python
from pathlib import Path
from core.spatial import SpatialCore, Constraints

core = SpatialCore.load(Path("data/dev/proc-factory-dev-003"))
result = core.solve("floor_area_total", {
    "floor_id": "proc-factory-dev-003-F0",
    "room_type": "office",
})
print(core.format_answer(result))

# Independent routing primitive with combined constraints:
# core.constrained_route(start_id, destination_id,
#     Constraints(step_free=True, min_width=1.1, closed=frozenset({lift_id})))
```

`core/spatial.py` contains the reusable tools; `core/questions.py` interprets the
published text templates; `core/evaluate.py` performs scoring. Persistent edits
still use the starter map API; spatial queries apply current closures plus their
own temporary constraints. Hypothetical doors do not modify the building.

## Conventions and limits

- Preserve the official MultiGraph, representative-point anchors, consecutive
  connector stops, stairs/lift costs and zero-cost outside node. These costs and
  straight-line room traversals are benchmark conventions, not a safety-validated
  physical navigation model.
- Areas, largest rooms, stacking and wall-neighbour queries include room and hall
  spaces. Reachability/delivery counts include only type=room.
- An arrival at the supplied start space is assumed to have occurred. Entrance
  clearance before that arrival is not separately validated. Outdoor shortcuts
  remain exactly as in the published model.
- Shared-wall counts measure first-boundary length inside the second boundary's
  Euclidean 0.35-m buffer. This includes tolerance near corners; it is not a CAD
  wall-segment classifier. The minimum length is 1 m.
- What-if doors use the longest straight run of merged nearby boundary segments,
  centred between the two wall faces. Arguments are canonicalised for symmetry.
  Distances improve only when the reduction is strictly greater than 1 m. A room
  newly connected to an exit counts as improved; rooms unreachable in both states
  do not count.
- Invalid polygons fail explicitly rather than being silently repaired and
  changing area/topology. Room polylines follow the kit schema without holes.
- Equal maxima use a stable ID tie-break. The kit promises clear winners; equal
  geometric candidates in new data require an explicit product policy.
- The tool wrapper was tested locally without paid conversational-agent calls.

Independent Sonnet 5.5 review and dispositions are recorded in
`reports/spatial/SONNET_REVIEW.md`.

## Test submission, 24 October 2026

After the train/dev implementation and review were complete, the unchanged core
was run on the public test split at the user's request. No implementation changes
or parameter tuning were made using test questions or outputs.

- Submission: [submissions/team_answers.csv](submissions/team_answers.csv).
- 145 rows, all 145 IDs from submission_template.csv present exactly once.
- Every reply has a nonempty Answer line; no unresolved questions or runtime errors.
- UTF-8, columns `question_id,answer`, 6,342 bytes.
- SHA-256: `483d782790d4db8133a4bc1b14bc46d0a7053691522d8d69b890978687a7d118`.
- Validation: [reports/spatial/test-submission-validation.json](reports/spatial/test-submission-validation.json).
- Full run log: agent_output/benchmark/spatial-test-official.jsonl.
- No test reference answers are supplied, so the test score is unknown. A complete
  Answer line is a format/coverage check, not a correctness measurement.

The kit README documents the unchanged starter at **under 5% on benchmark
questions** because its tools lack the necessary geometry/constraint operations.
Our measured text-only dev result is 138/138 (100%). This is substantially above
that documented baseline, but no new paid starter run on the identical sample was
performed. The test submission needs scoring by the organisers for a test-set
comparison. The CSV is prepared locally; it has not been uploaded or submitted.

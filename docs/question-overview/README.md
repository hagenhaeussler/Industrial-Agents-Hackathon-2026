# Building question overview

`building-question-overview.xlsx` catalogs **2,930 questions across 280 buildings** at source commit `f41616590b69f3ea0c1cbfb41d6c35edd9ce53df`, prepared on 24 October 2026. It groups all 15 source question kinds into six conceptual clusters and maps the deterministic skills and proposed tools needed to answer similar questions for an unseen building.

The source contains 800 benchmark questions and 2,130 warm-up questions. The 2,785 train/dev reference answers are preserved. The 145 public test answers are withheld; this overview does not generate or fill them.

## Workbook contents

| Sheet | Use |
|---|---|
| Overview | Corpus totals, cluster frequencies and implementation order. Counts link to the detailed catalog. |
| Question types | All 15 exact kinds, expected outputs, scoring rules, algorithms, required fields, concrete examples and likely variations. |
| Questions | Every numbered question, full original prompt, readable answer, full answer JSON, source inputs, numerical tolerances, constraints, skills, proposed tools and source location. |
| Agent tools | Fifteen proposed tool contracts, current starter support and gaps, deterministic implementation and failure handling. |
| Buildings | Coverage by building, split, source, question kind, floor count and answer availability. |
| Live scenarios | Additional interaction and routing requirements from the saved announcement and team plan, distinguished from dedicated JSONL kinds. |
| Scoring and sources | Definitions, separate scoring profiles, methodology, evidence status, snapshot links and attribution. |

Filter `Questions` by cluster, kind, split, building or answer status. `No.` is unique within this overview. `Question ID` is the stable source identifier. `Reference reply (benchmark)` demonstrates the source scorer's expected final answer line for known benchmark answers. Full route and tour structures remain in `Answer JSON`.

## LLM-readable companion

`questions-clustered.jsonl` has one record per question in the same order and with the same `no` as the workbook. Every record contains the original source object, typed reference-answer availability, cluster, expected output, scoring contract, deterministic method, required building fields, proposed tool IDs and immutable source provenance. Test reference answers and source inputs remain `null`.

The taxonomy and tool contracts are analysis, not official benchmark labels or evidence that the tools have already been implemented. Foundation tools for loading, overview, resolution and serialization apply across all kinds; per-question tool lists emphasize the task-specific operations. Tool coverage counts overlap and must not be summed.

## Scoring and generalization

The supplied kit's `benchmark/score.py` grades the final `Answer:` line, while the warm-up evaluator checks agent state and route length. The later saved route announcement describes a different geometry/cost model and grading of ordered space paths. The workbook documents both; it does not silently treat them as interchangeable. The saved announcement lacks an independently verified external author/message link, and some Sunday route and serialization details remain unresolved.

For numeric benchmark answers, put exactly one number after `Answer:`. In particular, do not append `m²` to a numeric-only answer line because the scorer parses the `2` as an additional number. The area-bearing `largest_room` contract is different and accepts a room label plus area.

At inference time, derive intent and parameters from the question text and facts from the new building. The benchmark adapter receives a building directory and question text. The train/dev `inputs` and reference answers in this overview are analysis and validation labels, not tools for the live agent. Evaluate deterministic core behavior against known labels, then evaluate the full text-to-answer flow on dev. Corpus frequencies do not guarantee the frequency of future questions.

## Provenance and redistribution

The overview reads all 520 `data/*/*/questions*.jsonl` files once, without also counting the duplicated test CSV. Original question IDs and source file/line links are retained. SHA-256 of the question corpus, using processing order train/dev/test, sorted building IDs, `questions.jsonl` then `questions_basic.jsonl`, and `path + NUL + original file bytes + NUL`:

`943637d9218ae347c3d54cd2241346cdf390bca8631105143ecd6e24926cfb13`

Source definitions and implementation references are linked to the source commit in the workbook and JSONL. The local analysis was checked for complete coverage, unique IDs, exact source-answer preservation, cluster/count reconciliation and valid source-scorer formatting for all 655 known benchmark reference replies. Workbook formulas were recalculated and the sheets rendered for visual inspection. No live agent run, API-credit evaluation or native Excel execution is implied.

Preserve the repository's [ATTRIBUTION.md](../../ATTRIBUTION.md). Swiss Dwellings and ResPlan data are CC BY 4.0; procedural data is CC0-1.0. The OpenStreetMap-derived portion remains under ODbL-1.0, © OpenStreetMap contributors. The companion retains each building's source, license and attribution; the workbook includes them in its input tables.

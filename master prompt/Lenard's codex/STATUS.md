# STATUS: Lenard's codex (Agent & Evaluation Lead)
Last update: 2026-10-24 21:38 Europe/Berlin · Branch: `lenard/bench` · HEAD: parser/inference checkpoint (this revision) · Last sync with origin/main: `d46775f`; dependency `origin/hagen/core` at `49a7e6b` merged

Single writer: Lenard's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
L01 steps 1–4 implemented. Spatial solve integration and full scoring pending Hagen's next push. No API calls authorized.

## Delivered (newest first)
- This revision: published template parser, isolated evaluator entry point, checkpoint runner and failure reports. 60 bench tests pass. Contract C1.
- `4db2d92` (pushed): computed-answer serializer and strict submission CSV validator; 30 tests passed. Contract C1.
- Merged `origin/hagen/core` at `49a7e6b` as the explicitly allowed unmerged dependency. It includes platform `53eb592`, project rules and packages. No other owner's files edited.

## Interfaces exposed / changed
- `bench.serialize.serialize(building, kind, result) -> str`: all nine benchmark kinds and six warm-up kinds.
- `python -m bench.validate_submission <csv> <template>`: IDs, duplicates, header, UTF-8, 5 MB limit, non-empty Answer lines.
- `bench.templates.parse_question(building, question) -> (kind, inputs)`: ready for Hagen's `core.evaluate --check text`. All nine benchmark templates preserve reference behaviour. Warm-ups resolve names/types from building data.
- `bench.agent:answer`: load → parse → core solve → serialize. Unsupported/ambiguous questions and solver failures return no Answer line. LLM hook is disabled pending L03 and an approved budget.
- `python -m bench.run`: per-question checkpoints, resume identity includes wording, building hash, commit, source hash, profile, mode, model and prompt version. Gold access/scorer import follows the complete prediction batch.

## Evidence
- Planning baseline (master agent, not this builder): all 145 public test questions parse with the sibling template parser and produce an `Answer:` line (scratch copy, 24 Oct 2026); dev 138/138 from text.
- `env -u ANTHROPIC_API_KEY uv run --with pytest pytest -q tests/bench` → 30 passed in 0.03 s. No API key set for this run; no paid calls.
- `uv sync` succeeded with Python 3.14.7. Using `--with pytest` until the captain's dependency commit is integrated. Kit and dependency files unchanged.
- User approved the supplied master prompt rules without adding a root AGENTS.md. This thread uses its existing isolated T3 worktree on the required branch.
- `env -u ANTHROPIC_API_KEY uv run pytest -q tests/bench` → 60 passed in 0.40 s, including file-access isolation and fresh-process scorer-import isolation. Current isolation test uses a labelled computed-count dispatch stub until core.spatial is published.
- Text-only parser audit on all public questions: dev benchmark 138/138; train benchmark 510/517; test benchmark 145/145. These are parser results, not solver scores.
- Warm-up parser audit: dev 368/369; train 1750/1761. Every locate parsed to the expected asset ID in train+dev, with no ambiguity. Counts match expected types. The sole dev ambiguity is `osm-way27917482-Q09`: three rooms share `Generic room 03.08.033 (Floor 3)`.
- Seven benchmark train ambiguities: `osm-way37850565-H02/H03/H04` (Büro); `osm-way52060470-H06` (Genusswerk); `osm-way58216509-H04/H05/H06` (duplicate room labels). No hidden IDs chosen.

## Blockers and resource requests
- H1 reference copies and core loader/resolver are present. `core.spatial.solve` is not yet published at `49a7e6b`. Full L01 scoring and the official test CSV await it. Parser is ready for the next core push.
- Needs H5 Anthropic key and a budget before any paid run; H4 ElevenLabs agents and H9 human speaker for the A/B test.

## Change requests
- none

## Next handoff
- Hagen: fetch this parser checkpoint for `core.evaluate --check text`. Captain: serializer, validator, isolated entry point and runner are pushed; test CSV follows the solve handoff. Human relay still required.

# STATUS: Lenard's codex (Agent & Evaluation Lead)
Last update: 2026-10-24 21:46 Europe/Berlin · Branch: `lenard/bench` · HEAD: L01 submission checkpoint (this revision) · Last sync with origin/main: `d46775f`; core `cdd4f67` and platform `d187ce5` merged

Single writer: Lenard's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
L01 ready for captain review and merge at G2. L02 prompts and stub-tested chat are prepared locally. No API calls authorized.

## Delivered (newest first)
- This revision: published template parser, isolated evaluator entry point, checkpoint runner and failure reports. 60 bench tests pass. Contract C1.
- This revision: official 145-row test CSV and BENCHMARK.md. Official dev 138/138, train template 510/517, dev warm-up 368/369 with every miss classified. Contract C3.
- `4db2d92` (pushed): computed-answer serializer and strict submission CSV validator; 30 tests passed. Contract C1.
- Merged `origin/hagen/core` at `49a7e6b` as the explicitly allowed unmerged dependency. It includes platform `53eb592`, project rules and packages. No other owner's files edited.
- Integrated later dependency checkpoints `origin/hagen/core` at `cdd4f67` and platform at `d187ce5`. Hagen's checkpoint includes Claude's published app. No edits to other owners' files.

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
- Real-core inference isolation now passes without a solver stub. Bench plus prepared agent tests: 86 passed in 0.82 s.
- Official dev command: `env -u ANTHROPIC_API_KEY uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer --name dev-official` → 138/138. Source commit `54904dd`.
- Train: `env -u ANTHROPIC_API_KEY uv run python -m bench.run data/train --name train-template --mode template` → 510/517 in 9.16 s. Dev warm-up with `--warmup --name dev-warmup --mode template` → 368/369 in 22.79 s. Reports in ignored `agent_output/bench/`; tables and every miss in BENCHMARK.md.
- Test: official evaluator with `--submission-csv submissions/test_answers.csv` → 145 rows. Validator → ok. CSV SHA-256 `d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f`. Hidden test accuracy is unknown.
- All runs used `env -u ANTHROPIC_API_KEY`; paid calls 0, spend USD 0. No budget approved.
- `env -u ANTHROPIC_API_KEY scripts/check.sh` → 240 Python tests passed (includes 26 prepared L02 tests), kit oracle 369/369, core text dev 138/138, 39 Bun tests passed, TypeScript/Vite production build and device-gate bundle passed. `bun install --frozen-lockfile --cwd web/app` succeeded first. Full log: `/tmp/tyb-check-l01.log` (local); no UI edits in this work.

## Blockers and resource requests
- Core dependency is resolved. The captain must review and merge the G2 submission. No claim that main or a deployed app contains this work.
- Needs H5 Anthropic key and a budget before any paid run; H4 ElevenLabs agents and H9 human speaker for the A/B test.

## Change requests
- CR-L-1 to Manuel's codex: C3 §8 has no session profile update tool. Chat can preserve step-free arguments across its own turns, but the voice agent cannot persist a spoken mobility change in the shared session. Please persist affirmative route/plan_tour mobility arguments to session constraints, or expose an approved session update callable. Needed for profile consistency across text, voice and phone.
- CR-L-2 to Manuel's codex/Hagen: `server.tools._spatial` passes `closed` as a list to step_free_reachable_count, but C3 §4 and core.spatial.solve require one string. Please agree a contract change or handle the empty/single/multiple closure case explicitly. No consumer-side silent adaptation.

## Next handoff
- Captain: merge the L01 submission after checks; official dev 138/138 and validator ok. Hagen: parser is consumed in his published text check; please confirm independent review. L02 chat/voice handoff follows. Human relay still required.

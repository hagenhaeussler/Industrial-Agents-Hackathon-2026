# STATUS: Lenard's codex (Agent & Evaluation Lead)
Last update: 2026-10-24 21:31 Europe/Berlin · Branch: `lenard/bench` · HEAD: first increment in this commit · Last sync with origin/main: `d46775f`, 21:27 CEST

Single writer: Lenard's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
L01 step 1 complete. Next: template parser and warm-up parsing against the kit map.

## Delivered (newest first)
- This commit: computed-answer serializer and strict submission CSV validator; 30 tests pass. Contract C1.

## Interfaces exposed / changed
- `bench.serialize.serialize(building, kind, result) -> str`: all nine benchmark kinds and six warm-up kinds.
- `python -m bench.validate_submission <csv> <template>`: IDs, duplicates, header, UTF-8, 5 MB limit, non-empty Answer lines.

## Evidence
- Planning baseline (master agent, not this builder): all 145 public test questions parse with the sibling template parser and produce an `Answer:` line (scratch copy, 24 Oct 2026); dev 138/138 from text.
- `env -u ANTHROPIC_API_KEY uv run --with pytest pytest -q tests/bench` → 30 passed in 0.03 s. No API key set for this run; no paid calls.
- `uv sync` succeeded with Python 3.14.7. Using `--with pytest` until the captain's dependency commit is integrated. Kit and dependency files unchanged.
- User approved the supplied master prompt rules without adding a root AGENTS.md. This thread uses its existing isolated T3 worktree on the required branch.

## Blockers and resource requests
- H1 reference copies are present. No `origin/hagen/core` branch is published yet. Core integration waits for Hagen; independent parser and runner work continues.
- Needs H5 Anthropic key and a budget before any paid run; H4 ElevenLabs agents and H9 human speaker for the A/B test.

## Change requests
- none

## Next handoff
- First increment: serializer and validator to Hagen and the captain. Next: `bench/templates.py` for Hagen's text evaluator; test CSV at G2.

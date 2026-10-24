# STATUS: Lenard's codex (Agent & Evaluation Lead)
Last update: – (not started) · Branch: `lenard/bench` · HEAD: – · Last sync with origin/main: –

Single writer: Lenard's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
L01 step 1 (not started)

## Delivered (newest first)
- none yet

## Interfaces exposed / changed
- none yet (planned: `bench.agent:answer`, `bench.run`, `bench.run_benchmark`, `agent.chat.ChatAgent`; CONTRACTS §12–§13)

## Evidence
- Planning baseline (master agent, not this builder): all 145 public test questions parse with the sibling template parser and produce an `Answer:` line (scratch copy, 24 Oct 2026); dev 138/138 from text.

## Blockers and resource requests
- Needs H1 reference copies at G0; `core` from Hagen's codex around 22:40 CEST.
- Needs H5 Anthropic key and a budget before any paid run; H4 ElevenLabs agents and H9 human speaker for the A/B test.

## Change requests
- none

## Next handoff
- `bench/templates.py` to Hagen's codex for `core.evaluate --check text`; test CSV to the captain at G2.

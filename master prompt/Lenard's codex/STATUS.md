# STATUS: Lenard's codex (Agent & Evaluation Lead)
Last update: 2026-10-24 22:11 Europe/Berlin · Branch: `lenard/bench` · HEAD: L03 offline checkpoint (this revision) · Last sync with origin/main: `a8be9ec` (C5), merged at `50b16ea`

Single writer: Lenard's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
L01 is on main at G2 (`0e89243`). C5 resolves all three owner-side integration requests; unchanged exact-name regression is green. L02 chat/prompts and L03 fallback/Sunday adapter are ready for code review with explicit offline limits. Live model and voice measurements remain blocked on budget/setup. L04 waits for the Sunday release inputs. No API calls authorized.

## Delivered (newest first)
- This revision: L03 bounded fallback, Sunday process adapter/converter, 48 paraphrases, mixed source scoring, per-kind selection and spend guards. Rehearsal 15 answered / 0 unanswered / 0 errors; seven route/tour legs match gold. No paid measurements. Contract C5, provisional Sunday schema.
- Integrated C5 main `a8be9ec` at `50b16ea`. CR-L-3 exact-name regression now passes unchanged. Final full check passes: 340 Python tests, oracle 369/369, core text dev 138/138, 39 Bun tests, TS/Vite build, device-gate bundle.
- `cd03324` (pushed): L02 `ChatAgent`, six prompt recipes, navigator/admin prompts and shared budget guard. 31 agent tests pass; the exact-name real-registry test still fails (CR-L-3). This is a recoverable checkpoint, not a green G3 merge request. Contract C4.
- G2 main `0e89243` includes the L01 submission and platform C4 mobility/closure fixes. Integrated here; no other owner's files edited.
- `4d93bdb` (pushed): published template parser, isolated evaluator entry point, checkpoint runner and failure reports. 60 bench tests pass. Contract C1.
- `e1c2dfd` (pushed): official 145-row test CSV and BENCHMARK.md. Official dev 138/138, train template 510/517, dev warm-up 368/369 with every miss classified. Contract C3.
- `4db2d92` (pushed): computed-answer serializer and strict submission CSV validator; 30 tests passed. Contract C1.
- Merged `origin/hagen/core` at `49a7e6b` as the explicitly allowed unmerged dependency. It includes platform `53eb592`, project rules and packages. No other owner's files edited.
- Integrated later dependency checkpoints `origin/hagen/core` at `cdd4f67` and platform at `d187ce5`. Hagen's checkpoint includes Claude's published app. No edits to other owners' files.

## Interfaces exposed / changed
- Sunday: `python -m bench.run_benchmark BUILDING QUESTIONS ANSWERS [--csv CSV] [--workers 4] [--timeout 60]`. JSON list/object, one/many JSONL records, kit CSV; gold fields discarded. Converter: `--make-questions BUILDING OUTPUT`. Process timeout, per-question checkpoint, atomic JSON, paths and lengths in provisional §12 schema.
- Benchmark runner: `--paraphrases PATH` maps source references only in the evaluator; inference sees text/building only. `--per-kind 2` selects original live measurement samples. `--max-cost DOLLARS` enables the guarded fallback only with a key and written allocation. Reports include kind/method/model metrics and cache token usage.
- Fallback: Haiku then one Sonnet attempt, auto strict tools, eight responses total, solver/serializer-only submission, one input repair, deadline checks and 7.5 s request timeout. Sunday adds the hard process timeout. Version `benchmark-fallback-v1`; cache effectiveness not measured.
- Paid batch interrupted before a checkpoint: retained marker blocks a repeated paid run. Reconcile spend and write a new allocation before using a new run name/output. Sunday worker timeout/crash retains its full share as an upper-bound cost. See BENCHMARK.md.
- `agent.chat.ChatAgent(registry, session_provider).reply(session_id, message)`: strict registry tools, current session per turn, per-session history/lock, bounded Sonnet tool runner, preview/confirm guard and returned display payloads. Shared session mobility replaces old chat preferences after an explicit UI profile change.
- Text chat requires both `ANTHROPIC_API_KEY` and positive `TYB_CHAT_BUDGET_USD`, plus a written allocation here before enabling them. Key alone cannot start requests. SDK retries disabled; process restart resets the budget and needs a new allocation. See `agent/README.md`.
- H4: paste-ready English voice prompts and first messages in `agent/voice_prompts/`, each under 2,500 characters. Six recipes each fit 25 lines; version `chat-v1`. Human configuration document unchanged.
- `bench.serialize.serialize(building, kind, result) -> str`: all nine benchmark kinds and six warm-up kinds.
- `python -m bench.validate_submission <csv> <template>`: IDs, duplicates, header, UTF-8, 5 MB limit, non-empty Answer lines.
- `bench.templates.parse_question(building, question) -> (kind, inputs)`: ready for Hagen's `core.evaluate --check text`. All nine benchmark templates preserve reference behaviour. Warm-ups resolve names/types from building data.
- `bench.agent:answer`: load → parse → core solve → serialize. Unsupported/ambiguous questions and solver failures return no Answer line. Fallback is implemented but stays disabled without an approved run budget and key.
- `python -m bench.run`: per-question checkpoints, resume identity includes wording, building hash, commit, source hash, profile, mode, model and prompt version. Gold access/scorer import follows the complete prediction batch.

## Evidence
- Final `env -u ANTHROPIC_API_KEY uv run pytest -q tests/bench tests/agent` → 125 passed in 1.74 s (local log `/tmp/tyb-agent-bench-final.log`). Covers model-prose rejection, one escalation/eight-response bounds, budget refusal before requests, refusal/API errors, repair/deadline guards, gold-free source mapping, timeout and constraints. The real SDK tool loop also passes with mocked HTTP transport; no network requests.
- `env -u ANTHROPIC_API_KEY scripts/check.sh` final after C5 → exit 0: 340 Python tests in 30.10 s, oracle 369/369, core text dev 138/138, 39 Bun tests, TypeScript/Vite build and device-gate bundle. `/tmp/tyb-check-final.log`. Earlier pre-C5 check had 311 passes and one CR-L-3 failure; that cause is now fixed by its owner.
- Sunday converter on `data/dev/proc-factory-dev-003` → 15 inference-safe questions. Adapter to `/tmp/tyb-sunday-c5-a.json` and `.csv` → 15 answered / 0 unanswered / 0 errors. Independently compared all 7 route/tour legs: exact space and element paths; lengths within 0.01 m. Commands in BENCHMARK.md.
- `env -u ANTHROPIC_API_KEY uv run python -m bench.run data/dev --name dev-paraphrases-template-c5 --mode template --paraphrases bench/paraphrases/dev_paraphrases.jsonl` → 0/48, all explicitly unanswered for unsupported wording, 1.61 s batch. No model accuracy inferred. Per-kind timing table in BENCHMARK.md; source identity in ignored `agent_output/bench/dev-paraphrases-template-c5/report.json`.
- Hybrid paraphrases, pure LLM two-per-kind, cache read test and model comparison: not run, no budget. Haiku-first order remains provisional. Dev has only one step-free reachability source; do not claim two distinct examples there. Paid calls 0, spend USD 0.
- Historical L02 checkpoint `cd03324`, before C5: `env -u ANTHROPIC_API_KEY uv run pytest -q tests/agent -k 'not case0'` → 31 passed, 1 deselected. The then-full agent suite had 31 passed, 1 failed. C5 fixes that same test without a changed expectation.
- Five HTTP conversations used an injected offline interpretation client and the real registry. This tests tool integration, not live language understanding. `env -u ANTHROPIC_API_KEY uv run pytest -q -s tests/agent/test_chat.py -k endpoint` → 5 passed after C5. Latest transcripts: `/tmp/tyb-chat-c5-transcripts.log`.

| User turn | Observed reply/result | Result |
|---|---|---|
| Where is CNC mill H-A1-A? | CNC mill H-A1-A is in Production zone H-A1 on Ground floor | Pass after C5 |
| the CNC mill | One question with three mills, all on Ground floor | Pass |
| Find the quantum teleporter | No item or place matches that name | Pass |
| I need the 3D printer H-A3-A and the UPS unit 1.24 | 2 stops, about 96 metres | Pass |
| Close the office lift → yes | Preview, then one saved event; duplicate tool commit suppressed | Pass |

- Demo wording uses items present in the dev factory. Filament, torque wrench and steel drum are absent there; coffee machines are present. No invented fixture substitutions. Preview speech has duplicate periods from owner-side composition, a cosmetic follow-up.
- Voice A/B table: Sonnet 5.5 / hosted model / Gemini Flash: all not run, latency not measured, cost USD 0. Retain specified Sonnet 5.5 provisionally; no evidence-based model switch. H4/H9 human and provider setup remain required.
- Planning baseline (master agent, not this builder): all 145 public test questions parse with the sibling template parser and produce an `Answer:` line (scratch copy, 24 Oct 2026); dev 138/138 from text.
- `env -u ANTHROPIC_API_KEY uv run --with pytest pytest -q tests/bench` → 30 passed in 0.03 s. No API key set for this run; no paid calls.
- `uv sync` succeeded with Python 3.14.7. The early command used `--with pytest`; later checks use the integrated dependency file. Kit and dependency files unchanged.
- User approved the supplied master prompt rules without adding a root AGENTS.md. This thread uses its existing isolated T3 worktree on the required branch.
- `env -u ANTHROPIC_API_KEY uv run pytest -q tests/bench` → 60 passed in 0.40 s, including file-access isolation and fresh-process scorer-import isolation. At that early checkpoint, isolation used a labelled computed-count stub. The later real-core isolation check is recorded below.
- Text-only parser audit on all public questions: dev benchmark 138/138; train benchmark 510/517; test benchmark 145/145. These are parser results, not solver scores.
- Warm-up parser audit: dev 368/369; train 1750/1761. Every locate parsed to the expected asset ID in train+dev, with no ambiguity. Counts match expected types. The sole dev ambiguity is `osm-way27917482-Q09`: three rooms share `Generic room 03.08.033 (Floor 3)`.
- Seven benchmark train ambiguities: `osm-way37850565-H02/H03/H04` (Büro); `osm-way52060470-H06` (Genusswerk); `osm-way58216509-H04/H05/H06` (duplicate room labels). No hidden IDs chosen.
- Real-core inference isolation now passes without a solver stub. Bench plus prepared agent tests: 86 passed in 0.82 s.
- Official dev command: `env -u ANTHROPIC_API_KEY uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer --name dev-official` → 138/138. Source commit `54904dd`.
- Train: `env -u ANTHROPIC_API_KEY uv run python -m bench.run data/train --name train-template --mode template` → 510/517 in 9.16 s. Dev warm-up with `--warmup --name dev-warmup --mode template` → 368/369 in 22.79 s. Reports in ignored `agent_output/bench/`; tables and every miss in BENCHMARK.md.
- Test: official evaluator with `--submission-csv submissions/test_answers.csv` → 145 rows. Validator → ok. Validator and byte-identical hash rechecked at L03. CSV SHA-256 `d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f`. Hidden test accuracy is unknown.
- All runs used `env -u ANTHROPIC_API_KEY`; paid calls 0, spend USD 0. No budget approved.
- `env -u ANTHROPIC_API_KEY scripts/check.sh` → 240 Python tests passed (includes 26 prepared L02 tests), kit oracle 369/369, core text dev 138/138, 39 Bun tests passed, TypeScript/Vite production build and device-gate bundle passed. `bun install --frozen-lockfile --cwd web/app` succeeded first. Full log: `/tmp/tyb-check-l01.log` (local); no UI edits in this work.

## Blockers and resource requests
- G2 is on main; CR-L-1/2/3 are resolved in C5. Captain review/merge of chat and Sunday code is pending. Live text/voice quality is not measured. No deployment claimed.
- L04 needs organizer schema/questions, unseen building, captain release tag and fresh Linux rehearsal. Local dev rehearsal is ready; no Sunday submission is invented.
- Explicit Sunday constraints on non-route spatial kinds return an unanswered error until semantics are agreed (CR-L-4).
- Needs H5 Anthropic key and a budget before any paid run; H4 ElevenLabs agents and H9 human speaker for the A/B test.

## Change requests
- CR-L-4, open, to captain/Hagen (C5 §12 provisional constraints): confirm whether supplied constraints apply only to route/tour kinds, or define spatial-kind semantics and a core interface. Current adapter returns an explicit error for spatial-kind constraints, rather than silently ignoring them. Route/tour overrides work and are recorded. Needed before organizer-schema adaptation if those inputs appear.
- CR-L-3 resolved by platform `4d48930`, C5, integrated via main `a8be9ec`. Unchanged regression passes. Original request to Manuel's codex (C3 §8 find): real-registry chat test `Where is CNC mill H-A1-A?` fails. `_find` merges exact asset candidates and fuzzy space candidates by score alone. Core returns exact asset at 1.0 and `Production zone H-A1` fuzzy token-set match at 1.0, so the tool reports ambiguity. Please preserve match-stage precedence across entity kinds (exact ID/ref/name before normalized/fuzzy) and add this cross-kind regression. Effect: unnecessary question despite an exact item name. The original L02 success-path failure is resolved; no platform file edited.
- CR-L-1 resolved by platform `b922b1d`, C4, integrated via main `0e89243`. Original request to Manuel's codex: C3 §8 has no session profile update tool. Chat can preserve step-free arguments across its own turns, but the voice agent cannot persist a spoken mobility change in the shared session. Please persist affirmative route/plan_tour mobility arguments to session constraints, or expose an approved session update callable. Needed for profile consistency across text, voice and phone.
- CR-L-2 resolved by platform `b922b1d`, C4, integrated via main `0e89243`. Original request to Manuel's codex/Hagen: `server.tools._spatial` passes `closed` as a list to step_free_reachable_count, but C3 §4 and core.spatial.solve require one string. Please agree a contract change or handle the empty/single/multiple closure case explicitly. No consumer-side silent adaptation.

## Next handoff
- Human relay to Manuel's codex: fetch this L03 checkpoint and `cd03324`. All owner-side regressions are green after C5; review/merge chat and Sunday adapter code through the captain. Configure `TYB_CHAT_BUDGET_USD` only after a written allocation. H4 can use prompt files. H4/H9 setup and a written budget are required for live chat/A-B measurements.
- Hagen: review fallback kind/input schemas and provisional constraint scope (CR-L-4). Sunday rehearsal command is ready in BENCHMARK.md.
- L04: rerun on captain's fresh Linux clone and release tag, validate/regenerate official CSV, then use actual organizer inputs when released. No main merge or deployment performed by this builder.

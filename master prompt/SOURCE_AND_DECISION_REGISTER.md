# Source and decision register

Audit performed 24 Oct 2026, 20:15–21:00 CEST, on `main` at `a5656fe` (up to date with `origin/main` per the humans), working tree with intentional uncommitted edits in `2026-10-24-plan-review-zwei-ux.md` and `docs/elevenlabs-agent-config.md`. Nothing in the repository was modified except this new `master prompt/` directory. Authority is resolved by subject: current human instructions define outcomes; organizer documents define the competition contract; executable code and observed checks define implementation state; plans and research supply candidates.

## 1. Checks actually run during this audit

All free, local, no API calls. Scratch files lived in the session scratchpad, outside the repository.

| # | Command / method | Result |
|---|---|---|
| A1 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m starter_agent.evaluate data/dev --oracle` (20:25 CEST) | **369/369** (count 40, locate 100, route 120, route_step_free 40, route_with_closure 29, tour 40), 13.7 s wall |
| A2 | Corpus inventory script over `data/*/questions*.jsonl` | train 517 + 1,761, dev 138 + 369, test 145 → **2,930 questions, 280 buildings**. Benchmark kinds: 9; warm-up kinds: 6. Test has no `step_free_reachable_count` (largest_room 21, floor_area_total 33, errand 20, shared_walls_count 26, room_stacked 9, straight_line_3d 15, what_if_door 3, wide_delivery_count 18). `inputs` field names are uniform per kind (table in CONTRACTS §4). |
| A3 | Sibling `../repo/core` (kit 1.0.0 routing) scored against **kit 1.1.0** dev answers from question text | geometry kinds 97/97, wide_delivery 19/19, step_free 1/1, **errand 3/19, what_if_door 0/2** |
| A4 | Same sibling core imported against the 1.1.0 `starter_agent/building_map.py` | `KeyError: 'via'` in `constrained_graph` for errand, wide_delivery, step_free, what_if (41 dev questions) |
| A5 | Scratch port (two changes: `data.get("via")`; what-if door via `add_door(position=…)` on a deep copy and multi-source Dijkstra from entrance door nodes instead of the removed `outside` node) | **dev text 138/138, gold-inputs 138/138; train text 510/517, gold-inputs 517/517**. The 7 train misses are ambiguous labels (identical "Name (Floor)" for different rooms), refused rather than guessed. Dev run 10.4 s. |
| A6 | Same port on the 145 public test questions | all 145 parsed to the expected kind and produced an `Answer:` line, 1.5 s; correctness unknown (no labels) |
| A7 | Reconstructed `space_path`/`element_path` from the kit graph for all reachable dev `route*` warm-ups (incl. closures) | `space_path` 161/161 equal; `element_path` 161/161 equal when each stair/lift **edge** is listed (a two-flight stair appears twice) |
| A8 | `benchmark.score.score_reply` probes | `Answer: 12.5 m²` and `Answer: 12.5 m2` both parse as one number; `Answer: Room 0.21, 12.5 m²` yields two numbers (wrong for numeric kinds) |
| A9 | Tool availability on this machine | `uv 0.11.8`, `node v25.8.2`, `gh`, `codex` present; **`bun` and the Railway CLI not installed**; so `web/mobile` build and tests were **not** run |
| A10 | Claude API reference (bundled skill, cached 6 Oct 2026) | IDs `claude-haiku-5-5` ($0.10/$0.50), `claude-sonnet-5-5` ($2/$10, cache read $0.20), `claude-opus-5-5` ($4/$20); `temperature`/`top_p`/`top_k` return 400 on every model since 21 Oct 2026; forced `tool_choice` returns 400 on Sonnet 5.5 and Opus 5.5; `thinking: disabled` returns 400 on Sonnet 5.5 and Opus 5.5; effort via `output_config.effort`; `strict: true` on tools; `fallbacks: "default"` + beta `server-side-fallback-2026-07-01` on Sonnet 5.5 (Claude API only); Haiku 5.5 has no server-side fallback |
| A11 | ElevenLabs React docs (WebFetch) | `@elevenlabs/react` re-exports `@elevenlabs/client`; hooks inside `ConversationProvider`; WebRTC via server `GET /v1/convai/conversation/token?agent_id=` → `startSession({ conversationToken })`; signed URL is the WebSocket path; client tools keyed by name; tool must be set to block ("wait for response") or the agent assumes success; `sendContextualUpdate` does not trigger a reply |

Not verified (stated as such in the plan): Railway limits (taken from the humans' verification), iOS/Android device behaviour, ElevenLabs account entitlements and credit balance, Anthropic credit balance, Claude Design availability, Sunday schema and release time.

## 2. Source register

| Source | Commit/date | Subject | Authority | Evidence | Implication for the plan |
|---|---|---|---|---|---|
| Human instructions in the launch message | 24 Oct ~20:15 | Railway, Python core/TS frontend, devices, voice, three aha moments, image import timebox, Git constraints | **current human requirement** | – | fixed inputs; not re-litigated |
| `HagenFinalPrompt.md` | `c2822f9` | mission, package structure, standards | human instruction | – | structure of this package |
| `Hagen UX explanation transcript.md` | `07a46bd`, recording 18:44 | Manfred journey: desk model + parts list → select → QR → multi-part optimal route → phone map → lift fails → reroute → found; new building via floorplan upload; movement as small optional flourish | central product source; cleaned, non-verbatim, speaker attribution inferred | medium | [UX_REQUIREMENTS.md](UX_REQUIREMENTS.md) traceability; "building model" not "3D mandate"; "optimal"/"perfect" are desired outcomes |
| `2026-10-24-plan-review-zwei-ux.md` (uncommitted, latest) | working tree 20:19 | consolidated team proposal: decisions, contracts, packages, gates, demo, risks | strong team input | proposals; some verified checks | adopted largely; deviations in §5 |
| `docs/elevenlabs-agent-config.md` (uncommitted) | working tree 19:17 | two agents, settings, tool names, token flow | intended config (team) | token semantics confirmed (A11) | tool names frozen in CONTRACTS §8 |
| `README.md`, `CHANGELOG.md` (kit 1.1.0) | `a5656fe` | task, levels, data format, route model, scoring, submission CSV | organizer contract | strong | profile `kit_1_1_0`; CSV submission |
| `Hackathon Challenge - Talk to Your Building-1.pdf` | in repo | story, levels, Sunday benchmark (`questions.json` → `answers.json`, node IDs, length), rubric 55/25/10/10, submission items | organizer contract, partly TODO | strong but incomplete ("TODO: exact time", schema TODO) | Sunday adapter provisional (CONTRACTS §12) |
| `Industrial Agents Hackathon Kick-Off.pdf` | in repo | submit Sunday 13:00 on Hack & More: 1-min demo video, 1-min technical video, architecture notes; finals 15:00, 3 + 1 min; $150 Claude credits per person | organizer | strong | schedule and release outcome |
| `starter_agent/`, `benchmark/` | `a5656fe` | graded route model (`building_map.py`), official scorer, evaluators | executable truth | A1, A7, A8 | reuse unchanged; wrap in `core/` |
| `data/` (280 buildings, 2,930 questions) | `4756739` | corpus | organizer data | A2 | labels only in tests |
| `2026-10-24-route-scoring-specifications.md` | `e1753b2` | route announcement: door-to-door 15 cm, stairs/lift costs, forklift ≥ 3 m, production bays destination-only, "give your route as the ordered list of spaces", score = best/yours | organizer announcement, source link missing | medium | `space_path` in Sunday output; forklift semantics unresolved |
| `2026-10-24-challenge-lead-qa.md` | `b272d50` | same distribution for unseen data; local what-if edits emphasised; website enough; judges may run code with own OpenAI/Anthropic keys; videos emphasise interaction | organizer verbal, transcript | medium | benchmark must run with an Anthropic key only or no key; text chat fallback |
| `2026-10-24-weitere-aufnahmen-relevante-infos.md` | `7a3961c` | Wi-Fi not expected; language free; usefulness matters | organizer verbal | medium | no Wi-Fi; UX emphasis |
| `open questions for judge .md`, `2026-10-24-fragen-an-juroren.md` | `f416165`, `aeebaee` | open organizer questions, ranked | team | – | [HUMAN_INPUTS_AND_RESOURCES.md](HUMAN_INPUTS_AND_RESOURCES.md) Q-list |
| `docs/brainstorming/2026-10-24-transkript.md`, `2026-10-24-brainstorming-zusammenfassung.md` | `aeebaee` | early team intent: two user groups, camera ideas | team, transcript | weak | background only |
| `PLAN.md` | `2ab5974` | TypeScript-only core on Railway/Node, DB-first, Hono, `node:sqlite`, prompt rules, budget split, licence rules, reuse table | superseded on language by humans; budget/licence rules still useful | proposal | TS core rejected (human); see §5 |
| `codex reviewed plan suggestions .md` | `03b4e91` | scoring profiles, one FastAPI service, state contract, token vs signed URL, viewer door bug, submission checks | strong review | partly verified | adopted (profiles, state, checks) |
| `AGENT_BUILD_SPEC.md` | `c0f2171` | Python tool catalogue, answer formats, harness modes, phases | team spec | proposal | tool catalogue adapted into CONTRACTS §4 |
| `research/2026-10-24-repositories-und-agent-skills.md` | `30dc8b4` | reuse candidates, six skill clusters, QR/AR building blocks, marker-pose caveat | research | documentation-based | dispositions §4 |
| `research/2026-10-24-tools-libraries-data-structures-algorithms.md` | `b7df2f1` | typed requests, caches, sparse traps, A* counterexample, portal graph | research | experiments on kit 1.0 model | dispositions §4; A* caveat applies to the removed outside node |
| `research/2026-10-24-harnesses-infrastructure-unexplored-resources.md` | `a5214b5` | release manifest, voice regression, Linux CI, replay, Railway envs | research | documentation-based | dispositions §4 |
| `research/experiments/2026-10-24-methods-audit.py` + results | `b7df2f1` | A* counterexample with zero-cost outside edge, parallel-edge summing trap, CSR timing on `osm-way27917482` | experiment, kit 1.0 graph | reproducible but pre-1.1.0 | parallel-edge rule kept; zero-edge trap obsolete in 1.1.0 |
| `web/mobile/` (`AGENTS.md`, `DESIGN.md`, `README.md`, `src/`) | `b411e05` | real camera hook, route banner, minimap, Blobatar agent dock; demo routes and scripted German chat; rule: no recording/upload of camera frames | executable prototype | code read; build not run (no Bun here) | base of the SPA; English; rule respected |
| `docs/architecture/README.md` + PNG | `3b4e839` | illustration of the reviewed plan | illustration | none | label as initial draft |
| `2026-10-24-tech-stack-initial-prompt.txt`, `repo-overview-prompt.txt`, PNGs | `7a3961c`, `aeebaee` | historical intent | historical | none | not used for decisions |
| `docs/question-overview/` | **deleted in `a5656fe`** | old taxonomy (referenced by the prompt and research) | – | – | replaced by A2 inventory and CONTRACTS §4 |
| `../repo/` (local sibling checkout of the Synera kit on the author's machine, **not in the team repo**) | uncommitted, 24 Oct 13:45–19:55 | `core/spatial.py`, `core/questions.py`, `core/evaluate.py`, `core/export3d.py`, `tests/test_spatial.py`, `routing_modes/`, `BENCHMARK.md`, `submissions/team_answers.csv` (kit 1.0 answers) | executable, local only | A3–A6 | **human input H1**: commit reference copies; old `team_answers.csv` must not be submitted (errand/what-if built on 1.0 rules) |
| `../experiments/recast-comparison/` (local only) | 24 Oct 19:31 | Recast navmesh comparison against kit 1.0 costs | experiment | pre-1.1.0 | rejected (§4) |

## 3. Verified facts versus proposals

| Claim | Status |
|---|---|
| Kit oracle 369/369 on dev | verified (A1) |
| Kit 1.1.0 is the model for hidden test answers | organizer statement in `CHANGELOG.md`; not independently verifiable |
| Geometry kinds 64/64 dev, 243/243 train (plan review A.3) | superseded by A5 (all nine kinds); plan review numbers came from a different (codex) check |
| "112 warm-up routes and tours are `reachable: false`" | A2 counts 32 dev and 201 train warm-up answers with `reachable: false` in total; the changelog's 112 are the ones that changed in 1.1.0. Not recounted per change. |
| Sunday output format | **unknown**: PDF says `answers.json` with node IDs and length, README says CSV, route announcement says space list |
| Plan PNGs lack scale; SVGs are Matplotlib exports with room `<path>` polygons | plan review A.2 claim; not re-verified here; H04 starts by checking it |
| iOS Safari has no WebXR `immersive-ar`; `BarcodeDetector` off by default | research claim with MDN compat data; device test still required (M03 X0) |
| Railway: no replicas with a volume, short downtime on redeploy | human-verified in Railway docs |
| Anthropic credits: $150 per person (kickoff slide) = $600 for four | kickoff slide; earlier transcript said per team; balance unknown (H-input) |

## 4. Research dispositions

| Item (source) | Disposition | Reason / activation condition |
|---|---|---|
| Typed requests + semantic validation (tools report §2.2) | **adopt** | `solve` validates required/extra fields and types; LLM fills strict schemas |
| Six domain skill clusters (repos report §5) | **adapt** | as prompt modules in `agent/skills/`, compiled into chat and voice prompts; not native API Skills |
| Native Claude API Skills in code-execution containers | reject | isolated container, not our core; extra environment |
| Building/version/profile cache identity (tools §4.1) | **adopt** | cache key `(content_hash, version, profile, constraints)` |
| Multi-source graph queries (tools §5.2) | **adopt** | entrance distances (what-if), reachability components, errand nearest item |
| Geometry indexing (STRtree) | defer | only if a measured hotspot appears (dev run 10 s for 138 questions) |
| Preserve parallel edges; zero-cost edges | **adopt** / obsolete | MultiGraph kept; the zero-cost outside node no longer exists in 1.1.0 |
| A* with Euclidean heuristic | **reject** | Dijkstra everywhere; counterexample shows no general guarantee |
| Portal graph with selected door identity (tools §4.3, codex §8) | **adopt** | kit door nodes already are portals; `node_path`, `element_path` and polylines carry the chosen door |
| Exact vs heuristic tour (tools §1, AGENT_BUILD_SPEC) | **adopt** | Held-Karp exact ≤ 12 stops; NN + 2-opt above, labelled heuristic |
| OR-Tools | reject | not needed for ≤ 12 stops |
| Transactional edits, idempotent commit, ephemeral what-if | **adopt** | CONTRACTS §6 |
| Replay and failure tests (harness §3.6) | **adapt** | three scenarios: double commit, stale preview, reconnect after commit |
| Release manifest (harness §3.1) | **adapt** | `/health` exposes commit and profile; `BENCHMARK.md` records SHA; agent config export |
| ElevenLabs native test/versioning, τ²-bench methodology | defer | manual 10-utterance A/B and regression list instead; activate only if time remains Sunday morning |
| Linux CI / fresh install (harness §3.3) | **adopt** | G6 fresh clone in a Linux container; `scripts/check.sh` |
| Separate Railway test environment | defer | one production service; no deploy during recording; activate if a second Railway environment is free and quick |
| SciPy CSR kernel | defer | not a measured bottleneck |
| rustworkx | reject | third graph representation |
| NetworkX + Shapely | **adopt** | kit dependencies; graded model |
| extremitypathfinder | reject | kit visibility graph is the graded walk; a second path engine could disagree |
| Recast navmesh (`../experiments`, `../repo/routing_modes`) | reject | measured against kit 1.0 costs; 1.1.0 already walks door to door |
| RapidFuzz | **adopt** | last step of `resolve`, numbers must match exactly |
| Pydantic v2 | **adopt** | `core/schemas.py`, server models, OpenAPI |
| openapi-typescript | **adopt** | generated TS types |
| react-zoom-pan-pinch | **adopt** | 2D map pan/zoom |
| jsQR | **adopt** | in-app QR scanning (iOS `BarcodeDetector` off) |
| zxing-js | reject | duplicate of jsQR |
| `qrcode` (npm) for the handoff QR; python-qrcode for marker sheets | **adopt** | small, client/server side |
| three.js WebXR hit-test sample | **adopt, timeboxed** | Android AR line (M03) |
| MindAR, AR.js | reject | image-marker tracking only, licence mix, second AR pipeline |
| hloc/MegaLoc visual localization (Lenard's offline test) | **defer/out** | uploads camera frames (conflicts with the prototype rule), no floor-plan registration yet, separate service; needs a human decision to revisit |
| svgelements | **adopt for H04 spike** | parse Kit SVG paths |
| floorplan-to-vector skill | reference only | different output format |
| CubiCasa5K, FP-TXT, IndoorGML, A2A, Temporal, Managed Agents, E2B, Railway sandboxes | reject for this weekend | no current need |
| Claude Agent SDK as product harness | reject | brings file/shell tools we do not want; Tool Runner suffices |
| Custom LLM endpoint for ElevenLabs | reject | built-in LLM via ElevenLabs credits is enough; activate only if ElevenLabs LLM quota is the blocker |
| Message Batches API in the Sunday path | reject | up to 24 h completion; template path is free anyway |
| `../repo/core/export3d.py` (USD/glTF via `pxr`, `trimesh`) | reference only | heavy deps; 3D in the browser via react-three-fiber extrusion |
| ElevenLabs UI components (Orb, Conversation Bar) | adapt, optional | only if they drop into Vite quickly; else a simple status pill |
| Hypothesis property tests | defer | optional for core invariants after G1 |
| OpenTelemetry | reject | request-ID logging suffices |
| NavigaTUM / c3nav / indoor-wayfinder | ideas only | GPL or different data models; no code import |
| Lovable credits | not used | the prototype already exists in React |

## 5. Decisions

Format: decision · alternatives · reason/evidence · consequence.

| ID | Decision | Alternatives considered | Reason / evidence | Consequence |
|---|---|---|---|---|
| D-01 | Python core, server, benchmark; TypeScript only in the frontend | TS core (`PLAN.md`) | **human decision**; graded model is shapely-based (A1) | `PLAN.md` TS sections superseded |
| D-02 | Use `starter_agent/building_map.py` unchanged; `core/` wraps or subclasses it | copy and modify | graded model exactness; kit updates stay mergeable | kit file is read-only for all builders |
| D-03 | Port the sibling `../repo/core` solvers and template parser (with the A5 fixes) | write from scratch | measured 138/138 dev in a scratch port (A5) | needs H1; fallback: reimplement to the same acceptance |
| D-04 | **Benchmark = hybrid:** deterministic template parser first, Claude tool-runner fallback for unknown wording | LLM tool runner for every question (plan review §6.1) | the 145 test questions and all dev questions are templated (A6); deterministic path is exact, free and reproducible without keys; the fallback covers new wording on Sunday | LLM generalization is measured separately (L03); pitch line "the LLM interprets only when needed" |
| D-05 | Fallback model `claude-haiku-5-5` (effort low), one escalation to `claude-sonnet-5-5` | Sonnet only | cost (A10); measured decision in L03 | – |
| D-06 | Authoritative state = base JSON + event log; derived caches in process and as SQLite blobs; **no normalized replica of building.json in SQLite** | full SQLite building DB precomputed at import (plan review §5.1, `PLAN.md`) | one source of truth, no sync code, benchmark independent of the DB; dev run is already 10 s total | "precomputed DB" intent kept as a persisted derived cache |
| D-07 | Railway, one service, one process, SQLite on volume `/state` | – | **human decision** | no replicas; no deploys during recording |
| D-08 | **One SPA `web/app/`** (prototype moved there with `git mv`), routes `/desk`, `/admin`, `/go/:tour`, `/m/:marker` | separate `web/mobile`, `web/desk`, `web/shared` Bun workspace (plan review §4) | one build, one manifest, shared map/route components, simpler Docker and routing | Claude owns the move in C01; `AGENTS.md`/`DESIGN.md` move along and are generalised |
| D-09 | Bun is authoritative for the frontend; `web/app/package.json` and `bun.lock` owned by Manuel's Claude | pnpm (`PLAN.md`) | prototype already uses Bun (human decision includes Bun) | Dockerfile uses a Bun build stage |
| D-10 | `pyproject.toml`/`uv.lock` owned by **Manuel's codex**; all known deps added in M01's first commit | Hagen's codex as owner (plan review §4) | dependency changes are platform work and must match the Docker image; frees the core lead | deps: fastapi, uvicorn[standard], pydantic, rapidfuzz, qrcode, pytest, httpx, svgelements |
| D-11 | Tour order: Held-Karp exact up to 12 stops, NN + 2-opt above (labelled) | all permutations ≤ 7 (plan review §5.4) | exact for realistic picking lists at negligible cost | honest "optimal" claim |
| D-12 | `element_path` lists one entry per stair/lift edge plus every door | dedupe connectors | reproduces kit answers 161/161 (A7) | Sunday route output |
| D-13 | Route polylines from the visibility-graph shortest path of the same walk computation; length must equal the kit walk length (1e-6) | straight lines door to door; navmesh | map, camera and benchmark agree; no lines through walls in L-rooms | H02 acceptance |
| D-14 | Two ElevenLabs agents (navigator, admin), WebRTC + conversation token, client tools with wait-for-response | one agent with role switch | intended config in `docs/elevenlabs-agent-config.md`; A11 confirms semantics | two agent IDs in Railway variables |
| D-15 | Voice LLM: start Claude Sonnet 5.5 (low), decide by a ≤ 30-min A/B test | – | **human decision** | result recorded in the config doc |
| D-16 | Position: tour-start confirmation, printed position markers with a floor footprint sticker and heading, manual room choice, manual stop progress | camera-pose estimation from the QR | a decoded QR is not a camera pose (research §3.2); simple standing protocol makes the XR origin meaningful | marker sheet shows the sticker and arrow |
| D-17 | Visual localization (hloc/MegaLoc) out of scope | upgrade before the journey gate (plan review X6) | conflicts with the prototype's no-upload rule; no plan registration; service cost | human decision required to reopen (HUMAN_INPUTS Q-9) |
| D-18 | Camera guidance: device gate early (≈ 30 min, with humans), implementation only after G4 and before/after G5 as capacity allows | full camera before the journey gate (plan review rank 5) | protects the integration captain and the 2D journey; AR is creativity points, not functionality | AR may end up as a short clip only |
| D-19 | Generic constraints only (`min_door_width_m`, `no_transit_room_types`); no forklift profile or demo | forklift constraints in K1 (plan review) | no data field identifies aisles; width ≥ 3 m is not sufficient evidence; no question uses it | organizer question remains open |
| D-20 | No cross-building routing | – | team decision in the review; no link data | – |
| D-21 | No custom LLM endpoint | – | team decision; not needed | – |
| D-22 | Plan import: SVG path first (deterministic), PNG + Claude vision second, scale by two points or one known length, validator, overlay preview; measured on 3 dev floors; timebox 90 min after G5 | PNG vision only (plan review B2) | SVG may give near-exact polygons cheaply; PNG has no scale | if no measurement by 03:00 CET it is cut from the pitch |
| D-23 | 3D only after G5 | – | plan review | – |
| D-24 | No durable job workflow | Temporal, queues | single short request | – |
| D-25 | No sandbox or LLM code execution | E2B, Railway sandboxes, code execution | LLM only fills typed tool args | – |
| D-26 | Buildings materialised lazily on first request; only the hero and demo buildings warmed at start | precompute all 280 at startup | largest building has 1,623 spaces; startup time | warm in background thread |
| D-27 | Dijkstra (networkx) everywhere | A*, CSR | correctness; timings fine | – |
| D-28 | Integration captain Manuel's codex, backup Lenard's codex | – | plan review | – |
| D-29 | Git: branch + worktree per builder; builders merge `origin/main` into their branch (no rebase of pushed branches); captain merges with `--no-ff` after `scripts/check.sh`; no force-push to `main` | PR-only via GitHub UI | works with or without `gh`; preserves history | GitHub PRs are optional for review comments |
| D-30 | User-facing text in English; the prototype's German strings are translated; `index.html` `lang="en"` | keep German | human decision (demo English) | – |
| D-31 | Root `AGENTS.md` (source precedence, data rules, API rules) created by Manuel's codex in M01 | – | plan review §4 | – |
| D-32 | Text chat agent: Sonnet 5.5, effort low, shared tool registry | – | plan review §6.2 | – |
| D-33 | Hero building of the venue, hand-authored with humans, ≥ 2 routes to the target (ideally lift and stairs), real objects as assets | – | plan review X2; kit buildings are not walkable | H-inputs H6/H7 |
| D-34 | Gate times re-based to T0 = 22:00 CEST | plan review times based on 20:30 start | current clock | – |
| D-35 | Old `../repo/submissions/team_answers.csv` must not be submitted | – | built with 1.0 routing (A3) | regenerate with the 1.1.0 port |
| D-36 | Mock presence and simulated part movement only after G5, visibly labelled, never claimed as tracking | – | transcript calls movement a "Spielerei"; honesty rule | – |
| D-37 | Add one navigator tool `spatial_query` (CONTRACTS §8) to the ten tools of the config doc | answer spatial questions only in the benchmark | interaction and the bonus moment ("what is above it?") need the geometry solvers in conversation; same solver as the benchmark | required for chat; optional on the ElevenLabs navigator |

## 6. Deviations from `2026-10-24-plan-review-zwei-ux.md`

| Review item | This plan | Why |
|---|---|---|
| §5.1/§2 #3: SQLite building DB with base tables and precomputed values | D-06: event log + derived cache blobs; base JSON authoritative | avoid a second representation and sync bugs; benchmark independent of DB |
| §6.1: benchmark = LLM tool runner with Haiku first | D-04: deterministic template parser first, LLM fallback | measured 138/138 dev from text with zero tokens (A5) |
| §4: `web/mobile`, `web/desk`, `web/shared` with a Bun workspace | D-08: one SPA `web/app/` | simpler build, routing, ownership |
| §4 table: Python deps owned by Hagen's codex | D-10: Manuel's codex | platform coupling, protects core lead |
| §4 table: coordinate transform `web/shared/geo/transform.ts` owned by Manuel's codex | split: 2D transform (Claude), WebXR frames (Manuel's codex) | each owner owns the renderer that uses it |
| §5.4: tours, permutations ≤ 7 | D-11: Held-Karp ≤ 12 | exact for larger lists |
| §5.4 K1: forklift constraints in core | D-19: generic constraints only | no data semantics |
| §8 X6: visual localization as optional upgrade before 01:00 | D-17: out | privacy-rule conflict, missing registration |
| §10/§11: X0/X1 camera before the journey gate | D-18: device gate early, AR implementation after G4 | protect the 2D journey and the captain |
| §11: gate times from a 20:30 start; journey gate 01:00 | D-34: re-based to 22:00; journey gate 02:15 CEST | actual clock |
| §10 K3/M1 at ~23:30 depending on LLM agent | M1 at 23:30 via deterministic path, independent of API keys | lower risk |
| §8: "standing at the QR and looking at it = XR origin" | D-16: explicit floor footprint sticker and heading protocol | a marker on a wall is not a standing point |
| §6.4 `POST /api/buildings/{id}/plan-image` | `POST /api/buildings/{id}/plan-import` returning a draft for confirmation | nothing saved without confirmation |
| §12 rank 6 3D before rank 7 | unchanged order, but both strictly after G5 | – |
| §6.3 tool list (navigator: find, plan_tour, route, next_step) | adds `spatial_query` (D-37) | spatial questions in conversation |
| Not in the review | `../repo` sibling core discovery and H1 | biggest acceleration available |

## 7. Conflicts that remain open (bounded assumptions)

| Conflict | Working assumption | Owner | Changes if answered |
|---|---|---|---|
| Sunday output: `answers.json` (PDF) vs CSV (README) vs space list (route announcement) | produce both; JSON schema per CONTRACTS §12 | Lenard's codex | only `bench/run_benchmark.py` |
| Sunday release time and who runs it | team runs it as soon as released; also documented for a judge rerun | Lenard's codex + human | schedule |
| Rubric "Submission demo 10" (PDF) vs "3–5 min live demo without restart" (README) vs kickoff (two 1-min videos, 3 + 1 min final) | do both: videos for submission, live demo for the final | Manuel's Claude (story), Manuel's codex (upload) | – |
| Whether image-only import is graded | timeboxed attempt (human decision) | Hagen's codex | priority of H04 |
| Forklift/production-bay data mapping | not implemented as a profile | Hagen's codex | add a named profile in 20 min |
| Lead said JSON lacks room layouts | the kit JSON has polygons; JSON path is primary | – | – |
| Hagen's "optimal" | exact for ≤ 12 stops, labelled heuristic above | Hagen's codex | – |
| Credits ($150 per person vs per team) | check balances before paid runs | humans | budget caps in L03 |

## 8. Explicit assumptions

1. The humans commit this package and the H1 sibling copies before builders start, and record the base SHA in [README.md](README.md).
2. Each builder runs on a machine with `uv`, Git and network access; at least the Claude and platform machines have Bun ≥ 1.2.
3. Somebody with Railway access creates the project, volume and variables (H3) within the first hour.
4. Somebody with ElevenLabs access creates the two agents per the config doc (H4) by G3.
5. Two phones (Android Chrome with ARCore, iPhone Safari) are available for the device gate and journey gate.
6. The venue allows printing and taping position markers (H7).

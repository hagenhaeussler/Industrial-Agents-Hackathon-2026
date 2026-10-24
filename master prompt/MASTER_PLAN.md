# Master plan: Talk to Your Building (Synera Track 01)

Written 24 Oct 2026, 20:15–21:00 CEST, against `main` at `a5656fe` plus the uncommitted human edits to `2026-10-24-plan-review-zwei-ux.md` and `docs/elevenlabs-agent-config.md`. Code freeze: **Sunday 25 Oct 2026, 13:00 CET**. Daylight saving ends that night: 03:00 CEST becomes 02:00 CET, so the night has one extra hour.

Reasons, sources and rejected options are in [SOURCE_AND_DECISION_REGISTER.md](SOURCE_AND_DECISION_REGISTER.md). Interfaces are in [CONTRACTS.md](CONTRACTS.md). Builder entry points are listed in [README.md](README.md).

## 1. The one-paragraph plan

We ship one web app on one Railway service. A Python core reuses the kit's graded route model exactly and answers every benchmark question kind deterministically. A hybrid benchmark agent parses the published question templates without an LLM and falls back to a tool-calling Claude agent for wording it does not recognise. The same core powers a desktop planning view (find parts, plan an optimal collection tour, hand it to the phone by QR) and a phone view (turn-by-turn on a real 2D map, voice, live reroute when an admin closes a lift). Camera guidance and plan-image import are timeboxed extensions after the journey gate. The demo and pitch are built around three moments: **"Say what you need, not where it is"**, **"From screen to hand"**, **"The building reacts"**.

**The most important finding of this audit:** a deterministic spatial core already exists outside the team repository, in the local sibling checkout `../repo/core/` (kit 1.0.0 base, uncommitted). Against the kit 1.1.0 answers it scores, from question text alone and with no API calls, 97/97 on the five geometry kinds and 19/19 on `wide_delivery_count`, but only 3/19 on `errand` and 0/2 on `what_if_door`, and it crashes (`KeyError 'via'`) on the 1.1.0 graph. A ten-line port, tested in a scratch copy during this audit, raises it to **dev 138/138 from question text** and **train 510/517** (the 7 failures are genuinely ambiguous labels), and all 145 public test questions parse and produce an `Answer:` line in 1.5 s. Getting this code into the team repository (human input H1) moves the benchmark milestone from "23:30 if all goes well" to "about an hour after launch" and frees two builders for the product.

## 2. Selected architecture

```text
 Laptop browser (/desk, /admin)          Phone browser (/go/{tour}, /m/{marker})
          │  HTTPS + WSS                         │  HTTPS + WSS          ┌──────────────────────────┐
          └───────────────┬──────────────────────┘   WebRTC audio ─────▶│ ElevenLabs agents        │
                          │                           client tools ◀────│ navigator, admin (Sonnet │
                          ▼                           (run in browser)   │ 5.5 to start, A/B test)  │
 ┌──────────────── Railway service, one process (uvicorn, 1 worker) ─────┴──────────────────────────┐
 │ FastAPI  server/   /api/* · /api/tools/{name} · /api/voice/token · /api/chat · /ws · /health · SPA │
 │          │ tool registry (server/tools.py) ── used by HTTP, text chat agent (agent/), voice tools │
 │          ▼                                                                                      │
 │ core/  (Python, pure)  kit BuildingMap (unchanged) · spatial solvers · resolve · routing +      │
 │        polylines + maneuvers · tour (Held-Karp) · edits/events replay · what-if · validate      │
 │ SQLite on volume /state: events, proposals, sessions, tours, markers, uploads, derived cache    │
 │ Image /app/data: kit buildings (read-only)   /app/web: built SPA (web/app, Vite + React + TS)   │
 └─────────────────────────────────────────────────────────────────────────────────────────────────┘
 Local, no Railway, no ElevenLabs:  bench/  answer(dir, text) = template parser → core.spatial.solve → serializer
                                            └─ fallback: Claude tool runner (Haiku 5.5 → Sonnet 5.5) → same solve → serializer
```

| Layer | Choice | Owner |
|---|---|---|
| Core | Python 3.12, `core/` wrapping `starter_agent/building_map.py` (kit file stays unchanged), shapely, networkx, numpy | Hagen's codex |
| Benchmark | `bench/` hybrid agent, official evaluator compatible, Sunday adapter | Lenard's codex |
| Product agent | `agent/` text chat agent (Anthropic Python SDK tool runner) sharing the server tool registry; voice prompts for the two ElevenLabs agents | Lenard's codex |
| Server | FastAPI, one uvicorn worker, SQLite (`sqlite3` stdlib) on `/state`, WebSocket fan-out in process | Manuel's codex |
| Frontend | One SPA `web/app/` (the prototype moved from `web/mobile/` with history), React 19, Vite, TypeScript, Bun, `DESIGN.md` visual system | Manuel's Claude |
| Voice bridge and camera internals | `web/app/src/voice/` (token, provider, client-tool handlers), `web/app/src/camera/ar/` (WebXR, marker frames) | Manuel's codex |
| Deployment | Multi-stage Dockerfile at repo root (Bun build stage → `python:3.12-slim`), Railway, volume at `/state` | Manuel's codex |

### 2.1 State model (summary of CONTRACTS §6)

- **Authoritative:** the base `building.json` files (immutable, identified by `content_hash`) and the append-only event log in SQLite. Sessions and tours are separate state.
- **Derived:** materialised building at a version, walk lengths and polylines per space, areas, adjacency, graphs. Cached per `(content_hash, version, profile, constraints)` in process; walk caches for large buildings are also stored as blobs in SQLite (`derived_cache`) so a restart is warm. This is the "precomputed building database" idea in a form that cannot drift from the source (decision D-06).
- **Benchmark path never touches `/state`.**

## 3. Product scope, tied to points and moments

| Rank | Scope | Serves | Status |
|---|---|---|---|
| 1 | Core port + benchmark solvers + warm-up kinds (H01) | 55 functionality points (benchmark) | mandatory |
| 2 | Benchmark submission: test CSV, Sunday adapter, `BENCHMARK.md` (L01, L03, L04) | 55 points | mandatory, never put at risk |
| 3 | Route polylines, maneuvers, optimal tour (H02) | Aha 1, Aha 2, interaction | mandatory |
| 4 | Server state, tools, sessions, tours, events, WS (M02) | Aha 1–3 | mandatory |
| 5 | Desk planning view with QR handoff (C01) | Aha 1, Aha 2 | mandatory |
| 6 | Phone journey with progress and live reroute (C02) | Aha 2, Aha 3 | mandatory |
| 7 | Admin close/undo with preview and confirm (H03 semantics, M02 storage, C03 UI) | Aha 3, Build "update" | mandatory |
| 8 | Voice navigator + admin via ElevenLabs, text chat fallback (L02, M02 bridge, C01–C03 UI) | interaction 25 points, Aha 1 and 3 | mandatory; text chat is the fallback |
| 9 | Hero building of the venue with printed position markers (H03 + humans) | live demo credibility, Aha 2 | mandatory for the physical walk; fallback: kit factory building on screen |
| 10 | JSON upload of a new building with validation (H03, C03) | Level 4 "Build", Sunday building in the app | mandatory (small) |
| 11 | Camera guidance: Android WebXR line, iPhone overlay arrow (M03) | creativity 10, Aha 2 | Level-5 extension, timeboxed |
| 12 | Plan import from SVG/PNG with scale calibration (H04) | "correct buildings built from plans" | timeboxed attempt after the journey gate |
| 13 | 3D stacked view, simulated part movement, mock presence (C04) | Aha 1 visual, liveliness | only after the journey gate; never presented as real tracking |
| – | Forklift demo, cross-building routing, custom LLM endpoint, visual localization (hloc/MegaLoc), Wi-Fi | – | out (D-19, D-20, D-21, D-17) |

**Cut order if time runs out:** 13 → 12 → iPhone overlay → Android AR → 3D everything. Ranks 1–10 stay; without camera, Aha 1 and Aha 3 carry the demo and Aha 2 runs on the 2D map with voice.

## 4. Harnesses: five different things

| Harness | What it is here | Decision |
|---|---|---|
| Development harness | Four coding agents (3 Codex, 1 Claude) on separate branches and worktrees, coordinated through this package, `STATUS.md` files and the integration captain | §8 and [OWNERSHIP_AND_DEPENDENCIES.md](OWNERSHIP_AND_DEPENDENCIES.md) |
| Product agent harness (text, benchmark fallback) | Anthropic Python SDK `client.beta.messages.tool_runner` with our typed tools, bounded loop | §4.2 |
| Voice conversation layer | Two ElevenLabs agents with client tools in the browser that call our tool API | §4.3 |
| Durable job workflow | None. Plan import is a single request with stored draft; no Temporal/queue | D-24 |
| Sandbox/execution infrastructure | None in the product. No code execution by the LLM; the LLM only fills typed tool arguments | D-25 |

### 4.2 Benchmark and product agent harness

**Benchmark (`bench.agent:answer`):**
1. Load the building (cached per path and content hash).
2. **Template parser** (port of `../repo/core/questions.py`, extended to the six warm-up kinds): exact regular expressions over the published English templates, entity resolution by full rendered label "Name (Floor)". Unknown wording or ambiguity raises; it never guesses.
3. **Typed solve:** `core.spatial.solve(kind, inputs)`.
4. **Serializer** writes the reply and the `Answer:` line (CONTRACTS §13).
5. **Fallback** only when step 2 raises and a key is configured: tool runner with `claude-haiku-5-5` (effort `low`), tools `building_facts`, `resolve`, `solve` (`strict: true` schema per kind), `submit_answer(kind, inputs)`; at most 8 tool iterations and 60 s; one escalation to `claude-sonnet-5-5` (effort `low`) if the inputs fail validation or `submit_answer` is not called. The model never writes the `Answer:` line; `submit_answer` runs `solve` again and the serializer formats it. API rules verified with the bundled Claude API reference on 24 Oct 2026: no `temperature`/`top_p`/`top_k` (400 since 21 Oct 2026), no forced `tool_choice` on Sonnet 5.5 (use `auto` plus prompt), no `thinking: disabled` on Sonnet 5.5, `output_config: {"effort": "low"}`, cache the stable system prompt and tool list.
6. **Measured separately:** template path on dev/train (free), LLM-only path on dev and on a paraphrase set (`--mode llm`, paid, small). Gold `inputs` are used only in tool-level tests, never at inference. Prices (Anthropic first-party, cached 6 Oct 2026 in the reference): Haiku 5.5 $0.10/$0.50 per MTok, Sonnet 5.5 $2/$10, Opus 5.5 $4/$20.

**Text chat (`/api/chat`, `agent/chat.py`):** Sonnet 5.5, effort `low`, the same tool registry as voice, session context injected per request, conversation history per session, at most 6 tool iterations per turn, `fallbacks: "default"` with beta `server-side-fallback-2026-07-01` (Claude API only). Clarify only when a required argument is missing or `resolve` returns `ambiguous`; show what was understood before an edit; never state a fact that did not come from a tool.

**Domain skills:** six short Markdown recipes in `agent/skills/` (`entities`, `routes_tours`, `areas`, `reachability`, `spatial_relations`, `edits_scenarios`) compiled into the chat system prompt and, condensed, into the two ElevenLabs agent prompts. A Markdown file does not activate itself; `agent/prompts.py` assembles them. Skills never replace computation.

### 4.3 Voice

- Two ElevenLabs agents (navigator for desk and phone, admin for the laptop), settings as in `docs/elevenlabs-agent-config.md`. Start with Claude Sonnet 5.5 at low reasoning, backup LLM "Default".
- WebRTC with a conversation token from `GET /api/voice/token?agent=…` (server calls `GET https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=…` with `xi-api-key`); client `startSession({ conversationToken })` inside `ConversationProvider` (`@elevenlabs/react`). Signed URLs belong to WebSocket mode and are not used. Verified against the ElevenLabs React docs on 24 Oct 2026.
- Client tools with "Wait for response" call `/api/tools/{name}`. Tool names are frozen in CONTRACTS §8.
- Interruption: the ElevenLabs turn-taking handles barge-in; a commit already sent to the server stays committed (idempotent by `proposal_id`), and the agent is told the result on the next turn.
- A/B test (Lenard's codex with a human speaking, ≤ 30 min, right after the first working voice slice): Sonnet 5.5 vs one ElevenLabs-hosted model vs one Gemini Flash model, the ten utterances of the plan review §9. Keep Sonnet unless another model passes more cases, or ties and is > 0.5 s faster to first word. Billed as ElevenLabs credits.
- Text chat is the always-available fallback and the reproducible interaction path for judges without ElevenLabs access.

### 4.4 Phone position and camera

- Baseline: tour start confirmation, printed position markers (`/m/{marker_id}`), manual "choose my room", manual "Got it" progress (CONTRACTS §10).
- Android: WebXR `immersive-ar` with `local` (required), `hit-test` and `dom-overlay` (optional); stop the QR camera stream before starting XR; route polyline drawn 2 cm above the floor using the marker frame (CONTRACTS §11). Re-anchor = leave AR, scan the next marker.
- iPhone: rear camera video with an arrow to the next waypoint; heading relative to the marker heading via `DeviceOrientationEvent` (permission needs a user gesture); no compass, no step counting, no claim of continuous localization.
- One "Start navigation" gesture requests camera, microphone, motion (iOS) and XR (Android); any denial keeps the 2D map.
- Visual localization (hloc/MegaLoc) is out: it uploads camera frames, which conflicts with the prototype rule "do not record, store or upload camera frames", and its registration into the floor-plan frame is unsolved (D-17).

## 5. Milestones, gates and time budget

**Clock:** all times Europe/Berlin. Launch target **T0 = 22:00 CEST Saturday**. If launch slips, gates G1–G5 slip by the same amount; the Sunday times are fixed. Effective builder time: 22:00 CEST → 03:00 CET is **6 h** (the clock goes back at 03:00 CEST); Sunday 07:00 → 13:00 CET is 6 h, of which ~3 h are reserved for recording, submission and recovery.

| Gate | Time | Pass criteria (evidence in [INTEGRATION_AND_ACCEPTANCE.md](INTEGRATION_AND_ACCEPTANCE.md)) | If it fails |
|---|---|---|---|
| G0 | 22:00 CEST | Package committed; H1 sibling files committed; four branches created; Railway project access confirmed | builders start on fixtures; H1 fallback = reimplement from CONTRACTS |
| G1 core | 23:00 CEST | `core.evaluate` dev text 138/138, structured 138/138, train structured 517/517; kit oracle still 369/369; `fixtures/` published; server `/health` local (Railway if access) | all builders except Claude help the core; no product merges until green |
| G2 M1 | 23:30 CEST | `submissions/test_answers.csv` validated (145 IDs, format), committed; official evaluator dev score per kind recorded with `bench.agent:answer` | gaps documented per kind; no placeholders |
| G3 slice | 00:30 CEST | On integrated `main`, local: desk shows a real building, `plan_tour` via API draws the computed route (real polylines if H02 has landed, else provisional segments flagged as such), QR opens `/go/{tour}` on a phone (LAN or Railway); one voice tool (`find`) works through the token path or text chat | fix the seam before adding features |
| G4 Aha 3 | 01:15 CEST | Admin closes the lift (text chat or voice in an admin session; the admin preview card if C03 has landed), phone with an active tour shows the new route ≤ 2 s, collected stops kept; wheelchair profile gives `no_route` honestly when applicable | reroute path before anything else |
| G5 journey | 02:15 CEST | On the Railway URL, both phones: all three aha moments in the hero building (or the factory fallback), timed against targets (route visible < 3 s, tour on phone < 2 s after scan, reroute < 2 s after "Yes"); camera optional | after this: no new infrastructure; misses are fixed first |
| Stretch | 02:15 CEST → 03:00 CET (≈ 1 h 45 min real time) | H04 import spike, M03 AR spike, L03 robustness run, C04 polish | anything unproven is cut and not shown as working |
| Sleep | 03:00–07:00 CET | No merges to `main`, no deploys, no unattended paid runs | – |
| G6 rehearsal | 07:00–08:00 CET | Fresh clone (Linux container) passes `scripts/check.sh`; Docker image builds and runs with an empty volume; a dev building run end to end through the Sunday adapter as if unseen | fix install path first |
| G7 dress rehearsal | 08:00 CET | Full 3-minute pitch with timer, phone mirroring, demo reset twice in a row | simplify the script |
| Recording | 08:30–09:30 CET | 1-min demo video (daylight; Android AR clip only if M03 passed), 1-min technical video | backup video from the G5 run |
| Feature freeze | 10:00 CET | Only Sunday-format adapter, data adapters and demo-critical bug fixes afterwards | – |
| Last deploy | 11:00 CET | Railway deploy of the release SHA; afterwards no deploys | previous good deploy stays |
| Sunday building | when released | Lenard's codex + a human run `bench.run_benchmark` immediately; load into the app via JSON upload | adapter fix within 20 min, else submit what validated |
| Submission | 12:15–12:45 CET | Upload on Hack & More: two videos, architecture notes, repository link, answers; confirm final remote SHA | – |
| Code freeze | 13:00 CET | – | – |

### Critical path

`H1 → H01 core port (G1) → L01 M1 submission (G2)` protects the 55 points.
`H02 polylines/tour → M02 tools/tours/events → C01 desk + C02 phone → G3 → G4 → G5` carries the demo.
Off the critical path but time-boxed: L02 voice A/B, M03 camera, H04 import, C04 3D.

### Workload (estimates for capable coding agents, not measurements)

| Builder | Before G5 (≈ 4 h 15 min) | Uncertainty | Critical-path risk | Reviewer | Spare capacity use |
|---|---|---|---|---|---|
| Hagen's codex | H01 1 h, H02 1 h 45 min, H03 1 h 30 min | medium (polylines, maneuver quality) | high (feeds everyone) | Lenard's codex reviews H01; Manuel's Claude checks route geometry visually | H04 import spike |
| Lenard's codex | L01 1 h 15 min, L02 chat 1 h (+ A/B 30 min after G4), L03 fallback 1 h 15 min | medium (LLM fallback quality, voice A/B needs a human) | high until G2, then low | Hagen's codex reviews solver use; Manuel's codex runs the A/B test environment | Sunday adapter hardening, robustness set |
| Manuel's codex | M01 1 h, M02 2 h 15 min, M03 device-gate page 15 min (humans run it), merge windows throughout | medium (Railway access, WebSocket/reconnect, iOS/Android quirks) | high (integration captain) | Lenard's codex is backup captain | M03 AR spike, release work |
| Manuel's Claude | C01 2 h 15 min, C02 1 h 15 min, C03 45 min before G5 (admin card, demo mode); rest of C03 and C04 in the stretch window (largest design share) | medium (live data volume, mobile layout, voice UX) | high for the demo | Manuel's codex reviews API usage; Hagen's codex reviews map correctness | C04 polish, 3D |

Claude is protected from chores: Dockerfile, Railway, token endpoint, voice SDK plumbing, WebXR internals, fixtures and the OpenAPI export are owned by Codex builders.

## 6. Fallback ladder (demo)

1. Voice fails → type the same sentences into the text chat (same tools).
2. ElevenLabs credits or token fail → text chat only; agent config export still submitted.
3. Phone fails → open `/go/{tour}` in a second laptop browser window.
4. Camera/AR fails → 2D map + voice on the phone (Aha 2 still visible).
5. Hero building incomplete → kit building `proc-factory-dev-003` (two floors, lift and stairs) on screen; physical walk skipped.
6. Railway down → local server on the laptop with phones on the laptop hotspot (Android Chrome over USB port forwarding to `localhost` keeps a secure context; iPhone needs HTTPS, so iPhone becomes optional in this case).
7. Everything fails → backup video recorded at G5/08:30.

## 7. Demo and pitch (all scenes in one building)

- **Demo video (60 s):** 0–8 s Manfred, new in the hall: "I need five parts." · 8–25 s desk: "I need the filament, the torque wrench and the steel drum." Parts light up, optimal order, animated route, QR (Aha 1) · 25–42 s phone scans, tour opens, voice: "After the column, turn right." (Android camera line if passed) (Aha 2) · 42–55 s laptop: "Close the east lift." – "Yes." Phone mid-route: notice, voice, new line via stairs (Aha 3) · 55–60 s name and closing line.
- **Technical video (60 s):** one architecture picture (§2), "the LLM interprets, the rules decide", the "How I calculated this" panel, measured dev scores per kind and cost per question, the bonus `room_stacked` question ("Water is dripping from the ceiling in office 0.29. What's above it?"), import measurement if H04 produced one.
- **Final (3 min + 1 min Q&A):** problem 20 s; live Aha 1 → Aha 2 (2D) → Aha 3, AR as a short clip; how it works with measured numbers; why it matters. Prepare answers: how the app knows where I am (marker standing point, confirmation, AR tracking only on Android, no Wi-Fi); how exact routes are (kit model reproduced 369/369, dev 138/138); what happens with a new building (JSON upload works; image import as measured); cost and speed (measured).

## 8. Collaboration protocol (summary)

One branch and worktree per builder from the committed package SHA; small pushed increments; `STATUS.md` with one writer each; contracts changed only by their owner after a change request; **Manuel's codex is the integration captain** (backup: Lenard's codex) and merges ready increments into `main` with `--no-ff` in dependency order after running `scripts/check.sh`; never force-push `main`; merge windows at every gate. Details and templates: [OWNERSHIP_AND_DEPENDENCIES.md](OWNERSHIP_AND_DEPENDENCIES.md).

## 9. Release outcome (definition of submitted)

- `submissions/test_answers.csv` (145 rows, validated) and the Sunday `answers.json`/CSV produced by the documented command.
- `BENCHMARK.md` with the exact commands that were run, versions, profile, measured per-kind scores, cost, known limits.
- Root `README.md` section "Run it locally" (`uv sync`, `cd web/app && bun install && bun run build`, `.env.example`), public Railway URL, `ATTRIBUTION.md` respected (OSM-derived content stays ODbL with credit).
- ElevenLabs agent configs exported without secrets next to `docs/elevenlabs-agent-config.md`.
- Two 1-minute videos and architecture notes uploaded; the old architecture picture labelled as an initial draft.
- Fresh-clone rehearsal log with date and SHA; final remote SHA recorded in Manuel's codex `STATUS.md`.

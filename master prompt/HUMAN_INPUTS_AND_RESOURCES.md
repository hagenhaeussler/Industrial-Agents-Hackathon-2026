# Human inputs and resources

Only actionable items. Never paste secret values into repository files, STATUS files or chat logs; put them in `.env` (git-ignored) or Railway variables. Times are Europe/Berlin.

## A. Blockers (needed for the planned path)

| ID | What exactly | Why | Owner (human) | Needed by | Blocked task | Fallback if late | Cost / permission |
|---|---|---|---|---|---|---|---|
| H1 | **Commit reference copies of the sibling core** from the machine that has `../repo` (one level above this checkout). Run from the repository root: `mkdir -p research/sibling-repo-2026-10-24/core research/sibling-repo-2026-10-24/tests && cp ../repo/core/{spatial.py,questions.py,evaluate.py,export3d.py} research/sibling-repo-2026-10-24/core/ && cp ../repo/tests/test_spatial.py research/sibling-repo-2026-10-24/tests/ && cp ../repo/BENCHMARK.md research/sibling-repo-2026-10-24/BENCHMARK_kit_1_0.md`, then commit together with this package. Do **not** copy `../repo/submissions/team_answers.csv` (kit 1.0 rules). | measured 138/138 dev after a ten-line port (register A5); saves 1–2 h on the critical path | whoever owns `../repo` (the author of `PLAN.md` 16:38) | G0, 22:00 CEST | H01, L01 | Hagen's codex reimplements the solvers from CONTRACTS §4 and README §4 to the same acceptance (+1–2 h) | none; confirm the author agrees to share it in the team repo |
| H2 | Review and commit `master prompt/` (and H1) on `main`, push, then write the resulting SHA as `BASE_SHA` in `master prompt/README.md` (or tell the builders) | builders branch from it | Hagen | G0 | everything | builders branch from `a5656fe` and read the package from the human's checkout | – |
| H3 | **Railway:** create project and one service from this GitHub repo (Dockerfile build), attach a volume at `/state`, set variables `STATE_DIR=/state`, `TYB_PROFILE=kit_1_1_0`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN`, `PUBLIC_BASE_URL`; disable app sleeping; generate a public domain. Either give Manuel's codex a Railway token in its local environment or a human performs deploys on request | phones need HTTPS; journey gate runs on Railway | Manuel (or whoever holds the Railway account) | 23:00 CEST (first deploy), G3 latest | M01 deploy, M03, G3–G5 | local server + Android USB forwarding; iPhone becomes optional | Railway plan cost per the team's account; permission to deploy from this repo |
| H4 | **ElevenLabs:** create two agents exactly as in `docs/elevenlabs-agent-config.md` (navigator, admin; Eric voice, `eleven_v4_turbo`, Scribe v2 Realtime, `turn_v3`, English, LLM Claude Sonnet 5.5 low, backup "Default", authentication on). Add the client tools with names and parameters from CONTRACTS §8, each with "Wait for response" on (`spatial_query` on the navigator is optional but recommended). Put the agent IDs and API key into Railway and the local `.env` of Manuel's codex. Report the remaining credits | voice is the interaction layer (25 points) | Manuel or whoever holds the ElevenLabs account | G3, 00:30 CEST | voice in G3–G5, A/B test | text chat with the same tools | ElevenLabs credits from the organizers; agent LLM billed there |
| H5 | **Anthropic API key** with credits in `.env` for Lenard's codex and on Railway; check the balance on Hack & More/console and set a workspace spend limit (suggested: benchmark/eval $40, chat $30, development $60, reserve untouched) | text chat, LLM fallback measurements | team | G3 | `/api/chat` (L02), fallback measurements (L03) | template path needs no key; chat falls back to "not available" | from the $150-per-person credits |
| H6 | **Hero building:** choose the part of the venue for the physical demo (two floors connected by a lift **and** stairs if at all possible, or one floor with two door routes); walk it with a tape measure or laser (room outlines in metres, door positions and widths, lift/stair positions, floor heights); list 5–8 real objects with their room (they become the "parts") | physical Aha 2/Aha 3 | two humans on site | sketch by 23:30 CEST, measurements by 00:30 CEST | H03 hero building, demo | `proc-factory-dev-003` on screen, no physical walk | venue permission to walk the area |
| H7 | **Print and place position markers** from `/api/buildings/hero-<slug>/markers/sheet` (≥ 12 cm codes, with floor footprint sticker and heading arrow): at the start desk, every turn of the demo route, both sides of the lift and the stairs | phone start position, AR anchoring | humans | 01:30 CEST | G5 | start confirmation + manual room choice | printer access; tape |
| H8 | **Devices:** one Android phone with Chrome and ARCore, one iPhone with Safari, cables; on the demo laptop `scrcpy` (Android mirroring) and QuickTime (iPhone mirroring); a phone hotspot | device gate, journey gate, final | humans | 23:30 CEST (device gate) | M03, G5, G7 | single-device demo | – |
| H9 | **A human speaker for the voice A/B test** (≈ 30 min, quiet room, ten utterances) | model decision | any human | 01:30 CEST | L02 A/B test | keep Sonnet 5.5 without comparison | ElevenLabs credits |
| H10 | **Sunday standby:** one person from 09:00 CET watching Discord/Hack & More for the unseen building, running the Sunday command with Lenard's codex | Sunday benchmark | one human | 09:00 CET | L04 | – | – |
| H11 | **Upload** the submission on Hack & More (account holder): videos, technical explanation, repository link, answers | submission | team account holder | 12:45 CET | release | – | – |

## B. Organizer questions (ask on Discord now; record answer, person, time and link in `open questions for judge .md` or a new note)

| ID | Question (paste-ready) | Changes | Owner |
|---|---|---|---|
| Q-1 | "Please share the Sunday input/output schema and one example: is it `questions.json` → `answers.json` (brief) or the README CSV? Are route node IDs space IDs? How is 'no route' represented? Which question kinds can appear?" | only `bench/run_benchmark.py` | Lenard |
| Q-2 | "When is the unseen building released, and do we run it ourselves or do you run our command? Any runtime limit?" | Sunday schedule | Lenard |
| Q-3 | "Is 'correct buildings built from plans' tested with a plan image without JSON? Which format, with or without scale?" | H04 priority | Hagen |
| Q-4 | "Does an AR navigation with QR anchoring, shown in our own building in the video, count as the Level-5 extension even if you do not test it live?" | M03 priority | Manuel |
| Q-5 | "Can judges use an ElevenLabs agent configuration with their own account, or is the public URL plus a text-chat fallback sufficient for reproducing interaction?" | submission notes | Manuel |
| Q-6 | "Which data fields mark forklift aisles and production bays?" (only if time; no plan depends on it) | D-19 | Hagen |

## C. Decisions only humans can make (defaults apply if no answer)

| ID | Decision | Default | Consequence of the default |
|---|---|---|---|
| Q-7 | Product name and closing line for videos and pitch | working title "Talk to Your Building" | needed by 08:00 CET for the videos |
| Q-8 | Replace the German prototype texts with English (human decision: demo language English) | English everywhere | `index.html` `lang` becomes `en` |
| Q-9 | Reopen visual localization (hloc/MegaLoc), which would upload camera frames and change the prototype's privacy rule | **no** | camera navigation uses markers only |
| Q-10 | Mark `PLAN.md` as superseded (it still says TypeScript core) | humans add one line at its top when they commit this package | agents follow `master prompt/` regardless |

## D. Optional improvements

| ID | What | Benefit | Needed by | Fallback |
|---|---|---|---|---|
| O-1 | **Claude Design** access for Manuel's Claude (tell it whether it is available in its environment) | faster high-quality UI exploration | 22:30 CEST | `DESIGN.md` + the frontend design skill/guidelines in its own environment |
| O-2 | Bun ≥ 1.2 installed on the machines of Manuel's Claude and Manuel's codex (`bun --version`); it is **not** installed on the machine where this plan was written | builds and `bun test` | G0 | Docker build stage (`oven/bun`) |
| O-3 | `gh` authenticated on builder machines | PR review comments | – | captain merges branches directly |
| O-4 | A second Railway environment for testing deploys | safer deploys | – | deploy only at merge windows |
| O-5 | A quiet corner and external microphone for the demo video | voice quality | 08:30 CET | text overlay |

## E. Budget summary (estimates, verify balances first)

| Item | Estimate | Basis |
|---|---|---|
| Template benchmark runs (dev, train, test, Sunday) | $0 | no API calls (measured) |
| LLM fallback evaluation (L03) | ≤ $5 with Haiku 5.5, ≤ $15 with Sonnet 5.5 escalations | ~40 paraphrases + selected dev questions, ~20k input tokens per question; prices from the Claude API reference |
| Text chat during development and demo | ≤ $30 | Sonnet 5.5, effort low, cached system prompt |
| Plan-import spike (H04) | ≤ $3 | a few Sonnet vision calls |
| ElevenLabs | unknown | depends on the organizer credits (H4) |

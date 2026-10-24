# Ownership and dependencies

## 1. The four builders

| Folder | Builder | Title | Owns |
|---|---|---|---|
| [`Hagen's codex`](<Hagen's codex/00_START_HERE.md>) | Hagen's codex | **Core & Spatial Intelligence Lead** | `core/`, `tests/core/`, `fixtures/` (core files), `demo/hero/`, building validation and import |
| [`Lenard's codex`](<Lenard's codex/00_START_HERE.md>) | Lenard's codex | **Agent & Evaluation Lead** | `bench/`, `agent/`, `tests/bench/`, `tests/agent/`, `submissions/`, `BENCHMARK.md`, voice prompt texts, A/B results |
| [`Manuel's codex`](<Manuel's codex/00_START_HERE.md>) | Manuel's codex | **Platform & Live Integration Lead**, integration captain | `server/`, `tests/server/`, `Dockerfile`, `.dockerignore`, `pyproject.toml`, `uv.lock`, `scripts/`, root `AGENTS.md`, `.env.example`, `web/app/src/voice/`, `web/app/src/camera/ar/`, `fixtures/` (server files), release and submission upload |
| [`Manuel's Claude`](<Manuel's Claude/00_START_HERE.md>) | Manuel's Claude | **Experience & Frontend Lead** | `web/app/` (everything except `src/voice/` and `src/camera/ar/`), `web/app/package.json`, `web/app/bun.lock`, `web/app/DESIGN.md`, `web/app/AGENTS.md`, `demo/scenario.json`, demo script and video storyboard |

Integration captain: **Manuel's codex**. Backup captain: **Lenard's codex** (takes over merges if Manuel's codex is blocked for more than 30 minutes, announced in both STATUS files).

## 2. File and component ownership

One primary owner per path. Others propose changes through a change request (§6) or, for trivial fixes, a commit on their own branch that the owner reviews before merge.

| Path / component | Owner | Consumers | Reviewer |
|---|---|---|---|
| `starter_agent/`, `benchmark/`, `data/` (kit) | nobody: **read-only** | all | – |
| `core/building.py`, `core/spatial.py`, `core/resolve.py`, `core/routing.py`, `core/geometry.py`, `core/maneuvers.py`, `core/tour.py`, `core/edits.py`, `core/whatif.py`, `core/validate.py`, `core/schemas.py`, `core/errors.py`, `core/profiles.py`, `core/evaluate.py`, `core/check_geometry.py`, `core/export_fixtures.py`, `core/plan_import/` | Hagen's codex | server, bench, agent | Lenard's codex (solvers), Manuel's Claude (geometry on screen) |
| `bench/templates.py`, `bench/agent.py`, `bench/serialize.py`, `bench/llm_fallback.py`, `bench/run.py`, `bench/run_benchmark.py`, `bench/validate_submission.py`, `bench/paraphrases/` | Lenard's codex | judges, humans | Hagen's codex |
| `agent/chat.py`, `agent/prompts.py`, `agent/skills/*.md`, `agent/voice_prompts/*.md` | Lenard's codex | server `/api/chat`, ElevenLabs config | Manuel's codex |
| `server/app.py`, `server/state.py` (SQLite), `server/tools.py` (registry), `server/schemas.py`, `server/ws.py`, `server/voice.py`, `server/markers.py`, `server/openapi.json` | Manuel's codex | web, agent | Lenard's codex |
| `docs/elevenlabs-agent-config.md` | humans; Lenard's codex records the A/B result in a **new** section after asking a human (it has uncommitted human edits) | Manuel's codex | – |
| `web/app/src/api/` (client, `schema.gen.ts`), `web/app/src/geo/transform.ts`, all UI | Manuel's Claude | – | Manuel's codex (API use) |
| `web/app/src/voice/` (token fetch, `ConversationProvider` wrapper, client-tool handlers) | Manuel's codex | Claude's UI | Manuel's Claude |
| `web/app/src/camera/ar/` (WebXR session, frames, overlay arrow maths) | Manuel's codex | Claude's camera UI | Manuel's Claude |
| `pyproject.toml`, `uv.lock`, `.gitignore` additions (`.state/`, `web/app/dist/`) | Manuel's codex | all Python | – |
| `docs/elevenlabs-agents/*.json` (exported agent configs, new files) | Manuel's codex with the H4 human | judges | Lenard's codex |
| `web/app/public/devtest.html` (device gate page) | Manuel's codex (Claude agrees on placement) | humans | – |
| `demo/SCRIPT.md` (pitch and video script) | Manuel's Claude | humans | Lenard's codex |
| temporary adapters `bench/_sibling_adapter.py`, `agent/_stub_registry.py` (MOCK, delete after use) | Lenard's codex | – | – |
| `web/app/package.json`, `web/app/bun.lock` | Manuel's Claude | Manuel's codex (voice/AR deps requested via change request; Claude adds the known list in C01) | – |
| `fixtures/` | producer of each file (CONTRACTS §15) | consumers | – |
| `master prompt/CONTRACTS.md` | section owners (CONTRACTS header) | all | captain checks consistency at merge |
| `master prompt/<builder>/STATUS.md` | that builder only | all | – |
| other `master prompt/` shared documents | frozen after commit; corrections by the captain with a changelog line | all | – |
| `submissions/`, `BENCHMARK.md` | Lenard's codex | judges | Manuel's codex |
| root `README.md` "Run it locally" section | Manuel's codex | judges | Lenard's codex |
| `PLAN.md`, older plans, research | read-only history (humans may mark `PLAN.md` superseded) | – | – |

## 3. Milestone dependency graph

```text
H1 (humans: sibling files) ──▶ H01 core port ──┬──▶ L01 bench M1 ──▶ L03 fallback + Sunday adapter ──▶ L04 Sunday run
                                               │
M01 scaffold (deps, server skeleton, Docker) ──┼──▶ M02 state/tools/tours/events/WS/voice token ──┬──▶ G3 slice
                                               │                                                   │
H01 ──▶ H02 polylines/maneuvers/tour ──────────┘                                                   │
                                                                                                    ▼
C01 desk on fixtures ──▶ (fixtures from H01) ──▶ C02 phone on live API (needs M02) ──▶ C03 admin/trace/demo ──▶ G5
H02 ──▶ H03 edits/validate/hero building ──▶ M02 commit/undo semantics ──▶ G4 Aha 3
L02 chat agent + voice prompts (stub registry first, then M02) ──▶ A/B test after G4 (needs H4 voice agents + a human)
M03 device gate (needs a Railway URL or LAN HTTPS + phones) ──▶ AR after G4 ──▶ clip
H04 import spike, C04 3D/polish: after G5 only
```

No cycles: every consumer starts on fixtures or contract examples (CONTRACTS §15). The only external bootstrap dependencies are H1 (sibling files) for H01/L01 and H3/H4 (Railway, ElevenLabs) for deployment and voice.

**Can start immediately at G0:** H01, L01 (serializer, runner, CSV validator, warm-up templates against the kit `BuildingMap`), M01, C01 (on contract examples until `fixtures/` lands).

## 4. Handoff evidence (what "published" means)

A handoff is a pushed commit on the builder's branch plus a STATUS entry with: SHA, behaviour, exact commands run and their output summary, contract version, known gaps. Required handoffs:

| From → to | What | Evidence |
|---|---|---|
| Hagen → Lenard | `core.spatial.solve`, `core.resolve`, kinds incl. warm-up | `uv run python -m core.evaluate data/dev --check text` output |
| Hagen → all | `fixtures/*.json` real data | file list + generating command |
| Hagen → Manuel's codex | `route`, `plan_tour`, `preview_edit`, `apply_events`, `validate_building` | pytest names + example payloads in STATUS |
| Manuel's codex → Claude | live endpoints + `server/openapi.json` | `curl` examples in STATUS; Railway URL |
| Manuel's codex → Lenard | tool registry callable from Python | `from server.tools import registry` example |
| Lenard → judges | `submissions/test_answers.csv`, `BENCHMARK.md` | validator output |
| Claude → humans | demo route `/desk?demo=hero` | screen recording or screenshots + timings |

## 5. Git protocol

Base: the commit that adds `master prompt/` (humans record it as `BASE_SHA` in [README.md](README.md)). Working tree rules: never run `git stash`, `git reset --hard`, `git checkout -- .` or `git clean` in a checkout that contains someone else's uncommitted work. The humans' original checkout stays untouched; each builder uses its own worktree or clone.

```bash
# once per builder (example for Hagen's codex; replace branch and folder)
git fetch origin
git worktree add "../tyb-hagen" -b hagen/core origin/main      # or: git clone <repo> tyb-hagen && git switch -c hagen/core
cd "../tyb-hagen"
git status                                                     # must be clean
```

| Builder | Branch | Worktree folder (suggested) |
|---|---|---|
| Hagen's codex | `hagen/core` | `../tyb-hagen` |
| Lenard's codex | `lenard/bench` | `../tyb-lenard` |
| Manuel's codex | `manuel-codex/platform` | `../tyb-manuel-codex` |
| Manuel's Claude | `manuel-claude/web` | `../tyb-manuel-claude` |

- **Commit cadence:** small coherent commits at every runnable increment; push at least every 45 minutes and immediately when someone waits on you. Message style: imperative, e.g. `core: port spatial solvers to kit 1.1.0 graph`.
- **Staying current:** `git fetch origin` before starting a dependent task, after a teammate announces a handoff, and before asking for a merge. Integrate with `git merge origin/main` into your branch (do not rebase a branch you already pushed). Resolve conflicts by intended behaviour and contracts; ask the owner when it is their file; rerun your checks.
- **Reading a teammate's work:** `git fetch origin && git log --oneline origin/<branch> -5 && git show "origin/<branch>:master prompt/<Builder>/STATUS.md"`.
- **Merging into `main` (captain only):** in a clean worktree of `main`: `git fetch origin && git merge --ff-only origin/main && git merge --no-ff origin/<branch> && scripts/check.sh && git push origin main`. Merge in dependency order (core → server → bench/agent → web). If `push` is rejected: fetch, merge, re-check, push. **Never force-push `main`.** Never delete another builder's branch.
- **GitHub pull requests** are optional; if `gh` is available a builder may open a PR (`gh pr create --base main --head <branch>`) for review comments, but the captain's merge above is the integration path. Follow any commit/PR attribution rules your own tool session gives you.
- **Merge windows:** at each gate (G1 23:00, G2 23:30, G3 00:30, G4 01:15, G5 02:15 CEST; Sunday 07:30, 09:30, 10:00, 11:00 CET) and on request when a consumer is blocked.
- **Known working revision:** after each green gate the captain tags `gate-G<n>` (`git tag gate-G3 && git push origin gate-G3`).

## 6. Change-request protocol

1. The requester adds an entry to its own STATUS.md under "Change requests" (template below), pushes, and asks the human relay to tell the owner.
2. The owner replies in its STATUS.md ("accepted in C<n> at <sha>" or "rejected because …"), edits the CONTRACTS section, appends a changelog line, bumps the contract version, and pushes.
3. Consumers implement against the new version only after the owner's push. Breaking changes after G3 require the captain's agreement.

```markdown
### CR-<builder initial>-<n>: <short title>
- Contract section: CONTRACTS §<n>, current version C<k>
- Requested change: <exact field/endpoint/name change>
- Why: <user or benchmark impact>
- Migration effect: <who must change what>
- Needed by: <time>
- Status: open | accepted (C<k+1>, <sha>) | rejected (<reason>)
```

## 7. STATUS.md template

Every builder keeps exactly this structure, newest information at the top of each section, one writer.

```markdown
# STATUS: <Builder> (<Title>)
Last update: <YYYY-MM-DD HH:MM Europe/Berlin> · Branch: <branch> · HEAD: <sha> · Last sync with origin/main: <sha, time>
## Current task
<milestone file and step>
## Delivered (newest first)
- <sha> <behaviour> · checks: <command → result> · contract: C<n>
## Interfaces exposed / changed
## Evidence
<paths to logs, reports, screenshots>
## Blockers and resource requests
<precise blocker, who can unblock, fallback in use>
## Change requests
## Next handoff
<what, to whom, when>
```

## 8. Human relay

The agents do not share chat history and cannot message each other. Coordination goes through pushed STATUS files and contracts. The four humans relay "please fetch, X is pushed at <sha>" messages between sessions. Do not claim that a teammate saw a change because it was pushed.

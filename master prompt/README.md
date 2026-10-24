# Master prompt package: Talk to Your Building

Execution package for four builder agents, written by the master planning agent on 24 Oct 2026 (20:15–21:00 CEST) from `HagenFinalPrompt.md`, the team's consolidated proposal `2026-10-24-plan-review-zwei-ux.md` and a fresh audit of the repository.

- **Audited base:** `main` at `a5656fe` (plus the uncommitted human edits to `2026-10-24-plan-review-zwei-ux.md` and `docs/elevenlabs-agent-config.md`).
- **`BASE_SHA` (builders branch from this):** `<fill in: the commit that adds this package and the H1 reference copies>` — the humans write it here after committing (H2).
- **Code freeze:** Sunday 25 Oct 2026, 13:00 CET. **Target launch:** 22:00 CEST Saturday.

## 1. What is in here

| Document | Purpose |
|---|---|
| [MASTER_PLAN.md](MASTER_PLAN.md) | architecture, scope, harnesses, gates and times, critical path, fallbacks, demo, release |
| [SOURCE_AND_DECISION_REGISTER.md](SOURCE_AND_DECISION_REGISTER.md) | checks actually run, source register, research dispositions, decisions D-01…D-37, deviations from the team proposal, open conflicts |
| [UX_REQUIREMENTS.md](UX_REQUIREMENTS.md) | Hagen's journey as a traceability matrix, interaction quality, acceptance scenarios, honest limits |
| [CONTRACTS.md](CONTRACTS.md) | the only canonical interface definitions (IDs, profiles, core API, route/tour results, edits/events, HTTP, tools, voice, WebSocket, sessions, handoff, markers, benchmark schemas, errors, fixtures) |
| [OWNERSHIP_AND_DEPENDENCIES.md](OWNERSHIP_AND_DEPENDENCIES.md) | owners per file, dependency graph, Git protocol, change-request and STATUS templates |
| [INTEGRATION_AND_ACCEPTANCE.md](INTEGRATION_AND_ACCEPTANCE.md) | commands (and which task creates them), environments, gate checklists, submission checklist |
| [HUMAN_INPUTS_AND_RESOURCES.md](HUMAN_INPUTS_AND_RESOURCES.md) | what the humans must provide, by when, with fallbacks |
| [`Hagen's codex/`](<Hagen's codex/00_START_HERE.md>) | Core & Spatial Intelligence Lead: H01–H04, STATUS |
| [`Lenard's codex/`](<Lenard's codex/00_START_HERE.md>) | Agent & Evaluation Lead: L01–L04, STATUS |
| [`Manuel's codex/`](<Manuel's codex/00_START_HERE.md>) | Platform & Live Integration Lead, integration captain: M01–M04, STATUS |
| [`Manuel's Claude/`](<Manuel's Claude/00_START_HERE.md>) | Experience & Frontend Lead: C01–C04, STATUS |

## 2. Before launch (humans, ~15 minutes)

1. Read [HUMAN_INPUTS_AND_RESOURCES.md](HUMAN_INPUTS_AND_RESOURCES.md) section A. Do **H1** (copy the sibling reference files; exact command there) and **H2** (commit this package together with H1, push, write `BASE_SHA` above). Suggested: add one line at the top of `PLAN.md` saying it is superseded by `master prompt/` (Q-10).
2. Start **H3** (Railway) and **H4** (ElevenLabs) in parallel; they are needed by 23:00 and 00:30 CEST.
3. Make sure each builder machine has `uv`; the machines of Manuel's Claude and Manuel's codex need Bun (O-2).

## 3. Launch order

All four start at the same time; nobody waits for anybody at launch (consumers start on contract examples and fixtures).

| Order | Builder | First milestone | Note |
|---|---|---|---|
| 1 | Hagen's codex | H01 core port | critical path for the benchmark |
| 1 | Lenard's codex | L01 benchmark M1 | builds serializer/runner while core lands |
| 1 | Manuel's codex | M01 scaffold + Railway | dependency commit within 10 minutes |
| 1 | Manuel's Claude | C01 app shell + desk | `git mv web/mobile web/app` within 15 minutes |

Gates: G1 23:00, G2 23:30, G3 00:30, G4 01:15, G5 02:15 CEST; sleep 03:00–07:00 CET; rehearsal 07:00 CET; freeze 10:00 CET; last deploy 11:00 CET; submission 12:15–12:45 CET ([MASTER_PLAN §5](MASTER_PLAN.md#5-milestones-gates-and-time-budget)).

## 4. Copy-ready starting prompts

Paste one of these into a fresh agent session that has access to a clone of the repository at `BASE_SHA`.

**Hagen's codex**

```text
You are "Hagen's codex", the Core & Spatial Intelligence Lead in a four-builder team (Hagen's codex, Lenard's codex, Manuel's codex, Manuel's Claude) building "Talk to Your Building" for the Synera Track 01 hackathon. Code freeze: Sunday 25 Oct 2026 13:00 CET.
Read "master prompt/Hagen's codex/00_START_HERE.md" in this repository now and follow it exactly. It links the plan, contracts and your ordered milestone files. Work on your own branch and worktree as described there, keep "master prompt/Hagen's codex/STATUS.md" current, push small verified increments, and never edit files owned by others without a change request. Start with milestone 01 immediately.
```

**Lenard's codex**

```text
You are "Lenard's codex", the Agent & Evaluation Lead (and backup integration captain) in a four-builder team (Hagen's codex, Lenard's codex, Manuel's codex, Manuel's Claude) building "Talk to Your Building" for the Synera Track 01 hackathon. Code freeze: Sunday 25 Oct 2026 13:00 CET.
Read "master prompt/Lenard's codex/00_START_HERE.md" in this repository now and follow it exactly. It links the plan, contracts and your ordered milestone files. Work on your own branch and worktree as described there, keep "master prompt/Lenard's codex/STATUS.md" current, push small verified increments, run no paid API calls without a written budget, and start with milestone 01 immediately.
```

**Manuel's codex**

```text
You are "Manuel's codex", the Platform & Live Integration Lead and integration captain in a four-builder team (Hagen's codex, Lenard's codex, Manuel's codex, Manuel's Claude) building "Talk to Your Building" for the Synera Track 01 hackathon. Code freeze: Sunday 25 Oct 2026 13:00 CET.
Read "master prompt/Manuel's codex/00_START_HERE.md" in this repository now and follow it exactly. It links the plan, contracts, the Git and merge protocol you run, and your ordered milestone files. Keep "master prompt/Manuel's codex/STATUS.md" current, never force-push main, and start with milestone 01 immediately (push the dependency commit within 10 minutes).
```

**Manuel's Claude**

```text
You are "Manuel's Claude", the Experience & Frontend Lead in a four-builder team (Hagen's codex, Lenard's codex, Manuel's codex, Manuel's Claude) building "Talk to Your Building" for the Synera Track 01 hackathon. Code freeze: Sunday 25 Oct 2026 13:00 CET. You own the desk, phone and admin experience and the demo.
Read "master prompt/Manuel's Claude/00_START_HERE.md" in this repository now and follow it exactly. It links the plan, the UX requirements, the contracts and your ordered milestone files. Use Claude Design if it is available to you; otherwise say so in your STATUS and continue. Keep "master prompt/Manuel's Claude/STATUS.md" current and start with milestone 01 immediately (the web/mobile → web/app move first).
```

## 5. How humans steer

- **Relay:** agents cannot talk to each other. When a builder says "pushed <sha>, consumers: X", tell X's session: "fetch origin; <builder> pushed <sha>: <what>". Ask builders for their STATUS when in doubt.
- **Answers to blockers:** reply in the builder's session; the builder records the answer in its STATUS. Organizer answers (Q-1…Q-6) go to Lenard's codex (Sunday format) and the captain, who updates the affected CONTRACTS section through its owner.
- **Changing the plan:** tell the captain (Manuel's codex) and the affected owner; the owner changes CONTRACTS with a changelog line. Decisions in the register stand unless a human changes them.
- **Gates:** at each gate time ask the captain for the checklist result; if a gate fails, follow the "If it fails" column in [MASTER_PLAN §5](MASTER_PLAN.md#5-milestones-gates-and-time-budget). Do not add features after G5.
- **Sleep:** 03:00–07:00 CET no merges, no deploys, no unattended paid runs.

## 6. Biggest levers, in one place

1. H1 sibling code → benchmark answers in ~1 hour instead of a night (register A3–A6).
2. One SPA + one service + one tool registry → fewer seams for the 2 a.m. journey gate.
3. Railway and ElevenLabs access early (H3, H4) → real phones and voice by 00:30 CEST.
4. A credible hero building (H6, H7) → the physical walk in the demo; otherwise the factory fallback on screen.

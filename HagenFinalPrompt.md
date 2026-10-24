# Hagen's final prompt for the master orchestration agent

> **How to use:** Give this entire file to the master planning agent with access to this repository. Its deliverable is the master plan and four coordinated sets of builder prompts described below. This file is the instruction to create those deliverables; it is not itself the completed master plan.
>
> **Prepared:** 24 October 2026, against repository snapshot `b411e05`. **Updated** on branch `lenard/plan-cleanup` for kit 1.1.0 and the team's fixed decisions in `PLAN.md` section 0. Reinspect the latest repository before planning. New code, human feedback, and organizer clarifications may supersede this snapshot.
>
> **Repository:** `https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026.git`

## 1. Your mission: own the whole outcome

You are our master architect, technical strategist, and orchestration agent: the **Master of Disaster**. Your job is to turn everything we have learned into one exceptionally strong, executable plan for four builders to deliver **Talk to Your Building** for the Industrial Agents Hackathon, Synera Track 01.

Think at the level of the entire product: the challenge, unseen buildings, mathematical correctness, human experience, agent behavior, deployment, collaboration, evaluation, and the final demonstration. Optimize for a product that works, feels excellent, and gives us the strongest credible chance of winning. Do not optimize for the number of technologies, agents, features, documents, or lines of code.

Act as the most capable technical decision-maker in this repository. Be confident enough to challenge every inherited assumption and disciplined enough to prove your choices. We want your best judgment, not a polished rearrangement of an old plan. Treat previous plans and research as valuable evidence and reusable pieces, not a ceiling on your thinking.

Your immediate assignment is **planning and prompt authoring**. Inspect, reason, perform narrowly useful checks, and write the complete execution package. Do not launch the four builders, implement the whole product, deploy services, or consume substantial paid resources merely because this planning prompt describes future execution. The humans will give the resulting prompts to the builders. Make that handoff ready to use.

## 2. What is fixed, and what you may change

The non-negotiable outcomes are:

- Meet the actual challenge and submission requirements, including generalization to a previously unseen building and new question wording.
- Preserve the customer needs and journey expressed by Hagen and the team. **`Hagen UX explanation transcript.md` is a central product source. Read it in full, not just its summary.**
- Produce a coherent system in which answers, routes, edits, and displayed state are grounded in building data and observable tool results.
- Coordinate exactly four builder roles: three Codex agents and one Claude agent, with the exact folder names below.
- Give Claude primary ownership of UI, design, and the customer journey; use Claude Design where actually available. Respect the team's preference to give Claude selected difficult design and integration problems without making it the bottleneck.
- Keep the work honest: proposals are not implementations; mocked data is not live integration; a test that was not run is not a passing test.
- **Respect the fixed team decisions in `PLAN.md` section 0.** TypeScript for everything (Python only in the official evaluator `benchmark/` and the later localization service), `building.json` as the only building input (no image, PDF or SVG import), Railway with one Node service and SQLite, a Claude Agent SDK harness (`@anthropic-ai/claude-agent-sdk`, built-in file/shell/web tools off) with our own tools (building data never in a prompt), ElevenLabs with two voice agents, one web app with two views (desktop administration and mobile navigation), no starter agent, and no expected answers in the database, prompts or tool results. These are current human constraints, not proposals. If you think one of them is wrong, explain the consequence and ask the humans; do not change it yourself.

You have final technical authority **within those outcomes, the fixed decisions in `PLAN.md` section 0 and the applicable execution permissions**. Choose the languages, architecture, libraries, harnesses, persistence, algorithms, tools, skills, service boundaries, and implementation sequence. You may adopt, combine, revise, replace, or reject the other recommendations in `PLAN.md` and the archived reviews, specs, research reports and architecture pictures in `docs/archive/`. Archived documents are history: where they differ from `PLAN.md`, `PLAN.md` wins.

Separate a recorded human requirement from the technical solution someone attached to it. A named provider or stack in an old plan may be a proposal; an explicit current human constraint is different. If you propose to change a genuine product requirement, explain the consequence and request that decision instead of quietly deleting it. For reversible technical choices, decide and proceed. Do not ask the humans to do your architecture work.

Make consequential decisions with concise rationale, evidence, alternatives, and consequences. We need decisions we can audit, not your private chain of thought. An unfamiliar or difficult approach is not automatically wrong; an attractive new framework is not automatically worth its integration cost.

## 3. Start with the actual repository, not its reputation

Before choosing the plan:

1. Confirm the remote, branch, current commit, working-tree status, repository instructions, and available tools. Preserve other people's uncommitted work. Fetch and safely update to the latest intended base; use an isolated checkout when needed.
2. Inventory tracked files and recent changes. Read the substantive documents in full. Inspect the implementation, dependency manifests, tests, and entry points behind important claims. Follow useful references to source files and experiments.
3. Build a source register. For every substantive source record its path, commit or date, subject, authority, evidence strength, and implications. Group repetitive data files by corpus; do not waste context reading every JSONL line aloud. Inventory the whole corpus and inspect representative cases and edge cases from every question family and building source.
4. Check the remaining time against the current clock and confirmed deadline. Old headings and milestone times may be stale. Use timezone-aware `Europe/Berlin` times, including the daylight-saving transition. Reserve integration, recording, submission, and recovery time.
5. Identify what exists, what works, what is only a prototype, what has been measured, what is only proposed, and what is missing. A file or package named in a document is not proof it is present or usable.

Resolve authority by subject: current human instructions define intended outcomes; verified organizer requirements define the competition contract; executable code and observed checks establish implementation state; research and plans supply candidate solutions. Recency alone does not establish authority. Preserve unresolved contradictions in the register with an owner and a bounded working assumption.

### Required reading map

This is a starting map, **not an exhaustive allowlist**. Discover and incorporate later additions too.

| Source | What you must extract |
|---|---|
| `Hagen UX explanation transcript.md` | The full customer journey, intended outcomes, optional embellishments, and explicitly uncertain details. Highest emphasis for product interpretation. |
| `README.md` (kit 1.1.0); `CHANGELOG.md`; `Hackathon Challenge - Talk to Your Building-1.pdf`; `Industrial Agents Hackathon Kick-Off.pdf`; `ATTRIBUTION.md` | Official task, levels, scoring, route model (README section 3), inputs/outputs, deliverables, deadline, data rights. The 1.1.0 README is newer than the PDF: it asks for a 3–5 minute live demo without a restart and no longer mentions finalists or `BENCHMARK.md`. |
| `2026-10-24-challenge-lead-qa.md`; `2026-10-24-route-scoring-specifications.md`; `2026-10-24-weitere-aufnahmen-relevante-infos.md` | Organizer statements, route measurement, provenance limits, and unresolved evaluation semantics. |
| `PLAN.md` section 10; archived `docs/archive/2026-10-24-fragen-an-juroren.md` and `docs/archive/open questions for judge .md` | What is still unanswered. Kit 1.1.0 answered the route model questions. |
| `docs/brainstorming/2026-10-24-transkript.md`; `2026-10-24-brainstorming-zusammenfassung.md` | Team intent, priorities, proposed differentiators, and uncertainty in automatic transcripts. |
| `PLAN.md` | The current plan. Section 0 is fixed. |
| `docs/archive/` (Codex review, two-UX review, `AGENT_BUILD_SPEC.md`, research reports, experiments, architecture pictures) | Earlier proposals and reasoning. Useful ideas such as tool lists, state contracts and edge cases. Their Python, image-import, position-QR and two-route-model parts are superseded. |
| `benchmark/`; `pyproject.toml`; `uv.lock`; `data/manifest.csv`; representative `building.json`, `equipment.csv` and questions | The official evaluator and scorer (Python, unchanged), schema, data quirks and test labels. The starter agent was removed; the routing reference is README section 3 and the expected answers. |
| `docs/elevenlabs-agent-config.md` | Two voice agents, client-tool contracts, conversation-token authorization, session context, and reproducibility. Verify before adopting API-specific claims. |
| `web/mobile/AGENTS.md`; `web/mobile/DESIGN.md`; `web/mobile/README.md`; `web/mobile/src/`; manifests and tests | Existing mobile design and working code, scoped instructions, reusable components, simulated behavior and integration gaps. |
| `docs/archive/` image prompts and pictures | Historical intent only. Pictures illustrate a proposal; they do not prove working software or override newer human requirements. |

References to a sibling `../repo`, another laptop, a deployment, dashboard configuration, or an uncommitted experiment must be located and verified before you count them as available. If absent, record the dependency and ask for the specific file, commit, export, or access needed. Do not invent its contents.

At this prompt's snapshot, `web/mobile/` is a real camera/UI prototype with demo routes and scripted chat. Its own documentation says it has no connected route backend, microphone, language model, or real localization. The starter agent and the empty root `agent.py` were removed; the official Python evaluator and scorer remain. Recheck this: builders may have pushed more since this prompt was written. Research reports that predate the prototype do not describe today's tree.

## 4. Put Hagen's customer journey at the center

Use the transcript to make an explicit **UX traceability matrix**: source passage → user need → interaction → required data/tool/backend behavior → owner → acceptance evidence → priority/fallback.

Cover at least this continuous story:

1. **A newcomer has a reason to use the product.** Manfred enters an unfamiliar factory or building and needs to find parts. Show the value immediately and avoid assuming he knows room IDs.
2. **Desktop discovery and planning.** He sees the building model and a parts list. Selecting a part highlights its actual location. He can select several required parts, see all of them, and plan one collection task.
3. **A useful multi-stop route.** Define start position, stop identity, collection progress, accessibility constraints, ordering, optional end destination, and the meaning of “optimal.” Distinguish an optimized collection tour from a benchmark tour whose order is prescribed. If an algorithm is heuristic, describe it honestly.
4. **Desktop-to-phone handoff.** A QR code transfers the chosen tour and enough context to continue on mobile. Define exactly what is stored, what the URL identifies, what the phone loads, and how the user establishes their starting position. A handoff link alone does not locate a person.
5. **Mobile execution.** The person follows a map and understandable directions, visits successive stops, and sees their progress. Explain how voice, map, instructions, camera mode, and loss of tracking or permissions interact. Make manual progress or position correction clear when needed.
6. **A disruption during the task.** A lift closes. Define the real source of the event, persist the change, notify the phone, and recompute the unfinished task from the latest known position. Explain the detour and preserve collected stops. A wheelchair profile must never silently become a stairs route; sometimes “no valid route” is the correct result.
7. **Completion.** The user reaches the required parts and knows the task is complete. Handle unavailable or moved parts, changed destinations, ambiguity, and interrupted sessions.
8. **A new building.** A user imports a `building.json` and gets a usable building right away: validation, precomputed values, views and all tools. Image, PDF or SVG floor plan import is out of scope by team decision (`PLAN.md` section 0).

Preserve the transcript's precision. It is a cleaned, nonverbatim record with uncertain speaker attribution. It establishes a **building model**, not an unambiguous 3D mandate. Part movement is an optional, inexpensive visual enhancement; it is not evidence of real tracking. “Optimal” and “perfect import” express desired outcomes, not proven implementations. The current instruction elevates the journey; it does not make every interpretation in a later review an exact quote from Hagen.

Separate the worker's desktop navigation/planning experience from facility administration. Both may live in one app, but a desktop user is not automatically an admin. QR codes are only a handoff link from desktop to phone (an object or a tour), never a position marker. Camera-only visual localization (hloc and MegaLoc, server-side) is a later add-on; explain registration into the floorplan frame and confidence handling when it is planned. A matched photograph or a decoded QR is not, by itself, a calibrated camera pose.

Plan interaction quality deliberately: ambiguity resolution, correction, visible edit previews, confirmation, undo, accessible constraints, spoken interruption, useful errors, readable maps, keyboard access, permission denial and recovery. Reuse the existing mobile design where it helps; do not replace it casually or pass its simulated behavior off as product functionality.

## 5. Synthesize the research; make the hard decisions

Produce a decision ledger for every consequential recommendation: **adopt / adapt / reject / defer**, with source, evidence, expected benefit, integration cost, deadline fit, and fallback. Every relevant research area must receive a disposition; adopting every suggested library is not the goal.

Explicitly distinguish:

- The **development harness** coordinating us and the four coding agents.
- The **product agent harness** interpreting building questions and invoking tools.
- The **voice conversation layer** and its browser/backend tool bridge.
- Any **durable import/job workflow**.
- Any **sandbox or execution infrastructure**.

These solve different problems. Choose additional infrastructure only when it earns its place. Prefer the smallest coherent system that meets the required behavior; preserve promising alternatives as deferred options with an activation condition.

Resolve the actual conflicts in this repository rather than forwarding them to the builders:

| Decision | Required resolution |
|---|---|
| TypeScript core | Fixed: TypeScript. Plan how the geometry (`representative_point`, `buffer` with round joins, nearest point, covers test) reproduces README section 3 to the centimetre, and how the official Python evaluator calls the TypeScript agent through a thin adapter. |
| Runtime agent and harness | Choose how natural language becomes validated tool requests, how the loop is bounded, when clarification is allowed, how errors recover, and how answers are serialized. Do not confuse a coding agent's shell tools with product tools. |
| Precomputation, database, cache and state | Decide what is authoritative and derived, what happens at import versus query time, how edits invalidate results, and how building/version/profile identity prevents stale answers. |
| Geometry and routing | Select representations and algorithms for exact source-model answers and for physically valid route geometry. Retain selected doorway/connector identity, not just a room list. |
| Platform and deployment | Fixed: Railway, one Node service, SQLite on a volume. Specify reproducible local execution, persistence, startup, configuration and recovery. |
| Voice architecture | Decide one/two agents, responsibilities, auth transport, tool naming, client/server ownership, interruption semantics and configuration versioning. Verify token versus signed-URL semantics for the chosen connection mode. |
| Phone position and camera | Fixed: no position QR codes and no depth sensors. Baseline is map and text directions with manual progress. AR is a later camera-only add-on with server-side hloc/MegaLoc; require evidence for coordinate registration, device support, camera/audio coexistence and useful failure behavior. |
| Frontend reuse and tooling | Decided: pnpm and Vitest; `web/mobile/` is converted. Decide how `web/mobile/` becomes the mobile view and how the desktop view is added. Assign package manifests and lockfiles to one owner. |
| JSON import, 3D, live movement, multi-stop tours, cross-building routing and forklift scope | Tie each to a human need or challenge requirement. Separate mandatory semantics from optional demo flourishes; define deliberate scope, validation and fallback. |

Use the specific research findings, not just its bibliography. Examples to evaluate include typed requests with semantic validation; six domain skill clusters; building/version/profile caches; multi-source graph queries; geometry indexing; preserving parallel edges; door-to-door walking inside spaces (kit 1.1.0); no route via the outside; exact versus heuristic tour optimization; transactional edits and ephemeral what-if; replay and failure tests; release manifests; voice regression; and fresh Linux installation.

Respect the limits of the measurements. A local graph-kernel speedup is not a measured end-to-end voice latency improvement. A single room-router experiment is not validation on every building. A proposed resource is not an account entitlement. Verify material model IDs, SDK compatibility, pricing, credit balances, browser capabilities and provider behavior using available tools and current primary documentation before making them a dependency. Do not carry forward invented or stale model/version claims just because multiple plans repeat them.

Use existing skills when they materially help. Inspect their actual instructions, availability, permissions, maintenance and licenses. Do not assume a skill is installed because a report mentions it. For product skills, define operational guidance: supported intent, required inputs, tools, evidence, edge cases and output contract. Specify how those skills are loaded and connected to tools in the chosen runtime; a Markdown file alone does not activate a skill in a voice or API agent. Skill prompts do not replace deterministic computation or access control.

Respect scoped repository instructions, including the mobile prototype's camera rule: no frames leave the browser, except later in AR mode to our own localization service, which does not store them. Treat imported plan/OCR text, room labels and QR payloads as data to validate, not permission to change tools, configuration or execute commands.

Timebox research that does not change a decision. If a key choice is uncertain, design the smallest discriminating spike, with an owner, measurement, cutoff and fallback. Architecture freedom is not permission to rebuild proven components for novelty.

## 6. Protect the evaluation and the unseen-building requirement

Read the actual scorer and evaluator. Build an explicit coverage map across all **15 current question kinds**:

`locate`, `count`, `route`, `route_step_free`, `route_with_closure`, `tour`, `largest_room`, `floor_area_total`, `step_free_reachable_count`, `wide_delivery_count`, `room_stacked`, `shared_walls_count`, `straight_line_3d`, `errand`, `what_if_door`.

The corpus has 2,930 questions across 280 buildings, including 145 public test questions without reference answers. Kit 1.1.0 recomputed 1,314 train/dev answers; confirm counts if the corpus changes again. Use the known examples to understand conceptual variation and test algorithms. The runtime agent must derive parameters from the actual question and facts from the supplied building. No hard-coded building IDs, answer lookup, gold inputs, or access to expected answers during inference. Keep evaluation labels out of runtime databases, tool responses and deployed data bundles.

Distinguish tool-level checks using train/dev labels from full question-text-to-answer evaluation. A correct solver called with gold parameters does not prove the agent can understand a new question. Measure both, report per-kind results and errors, and separate real calls from fixtures or mocks.

Kit 1.1.0 unified the route model: the expected answers and the judges' route grading use README section 3. The Sunday input/output format is still not fully confirmed (README CSV versus PDF `answers.json`). Isolate it in input/output adapters so a confirmed organizer answer changes an adapter rather than the whole system.

For the current benchmark, inspect `answer(building_directory, question_text)`, `benchmark.evaluate`, and `benchmark.score`; the agent is TypeScript, so keep a thin, documented Python adapter that lets the official evaluator call it. Respect the final `Answer:` format and per-kind exceptions. Numeric-only replies must not accidentally contain a second number such as the `2` in `m²`. Keep hypothetical changes isolated and benchmark questions independent unless the actual input contract requires stateful behavior.

Define the local one-command unseen-building run, accepted input formats, output schemas, stable question IDs, timeout/retry policy, checkpoint/resume behavior, logs, resource limits and failure handling. It must not require the public app, an ElevenLabs account, or manual per-question intervention merely to produce benchmark answers. Never submit invented placeholder answers as successful computation.

Use the documented 55/25/10/10 rubric to balance functionality, interaction, creativity and demo quality, without inventing the allocation inside those categories. Confirm deadline and submission details rather than assuming that an old “200 questions in five minutes” estimate or draft JSON schema is official. Plan the 3–5 minute live demo that works without a restart (README 1.1.0), plus the demo video, architecture explanation, required answer files, reproducibility documentation, attribution, and a fresh-clone rehearsal. The finalist round (3 + 1 minutes) is only in the older PDF; treat it as unconfirmed.

## 7. The four builders and their titles

The builders are teammates, not four isolated coding sessions. Every prompt must identify all four, explain the shared outcome, and name the relevant collaborators.

Use these exact identities and folder names. Start with the following titles and responsibility split, then refine the non-UI boundaries after the repository audit if that improves delivery. Document any reassignment once in the shared ownership map and in every affected prompt.

| Exact folder name | Builder title | Initial responsibility |
|---|---|---|
| `Hagen's codex` | **Core & Spatial Intelligence Lead** | Building model, import/validation foundation, geometry, routing, constraints, deterministic tools and their correctness. |
| `Lenard's codex` | **Agent & Evaluation Lead** | Product harness, language-to-tool behavior, domain skills, answer contracts, benchmark coverage, unseen-building adapter and evaluation. |
| `Manuel's codex` | **Platform & Live Integration Lead** | Backend/service integration, shared state, sessions/events, voice bridge, deployment and release integration; support UI integration and device plumbing. |
| `Manuel's Claude` | **Experience & Frontend Lead** | Claude Design where available, desktop and mobile journey, interaction design, visual system, frontend implementation and selected difficult UX/integration problems. |

Give Claude substantial ownership and a modestly larger share of design-intensive work if capacity supports it. Favor Claude for selected complicated problems where design and cross-layer judgment are central. This is the team's allocation preference, not a claim that a model name guarantees competence. Codex agents must still own and solve serious engineering work. Do not make Claude responsible for every difficult component, all integration, all testing, and every late rescue.

If Claude Design is unavailable, ask the humans for the exact access needed and provide an executable fallback using available design/frontend tools. Do not block all UI progress or invent tool access.

Show a workload table with estimated effort, dependencies, uncertainty, critical-path risk, reviewers and spare capacity. Keep core and evaluation covered throughout. Protect Claude's uninterrupted journey work by assigning operational chores and supporting integrations elsewhere. Assign a single integration/release owner and a backup; ownership means accountability for bringing contributors together, not doing all their work.

## 8. Create the execution package in these folders

Create **one root directory named `master prompt` with exactly these four immediate builder subdirectories**. Put shared documents directly in the root directory, and each builder's ordered prompt set inside its own directory. Use portable relative links and quote paths containing spaces/apostrophes in shell examples.

```text
master prompt/
  README.md
  MASTER_PLAN.md
  SOURCE_AND_DECISION_REGISTER.md
  UX_REQUIREMENTS.md
  CONTRACTS.md
  OWNERSHIP_AND_DEPENDENCIES.md
  INTEGRATION_AND_ACCEPTANCE.md
  HUMAN_INPUTS_AND_RESOURCES.md
  Hagen's codex/
    00_START_HERE.md
    01_<first-executable-milestone>.md
    02_<next-milestone>.md
    STATUS.md
  Lenard's codex/
    00_START_HERE.md
    01_<first-executable-milestone>.md
    02_<next-milestone>.md
    STATUS.md
  Manuel's codex/
    00_START_HERE.md
    01_<first-executable-milestone>.md
    02_<next-milestone>.md
    STATUS.md
  Manuel's Claude/
    00_START_HERE.md
    01_<first-executable-milestone>.md
    02_<next-milestone>.md
    STATUS.md
```

Replace the illustrative milestone filenames with concrete names. Use as many stages as the actual dependency graph requires; do not create empty filler prompts. Exactly four builder folders; no fifth shadow implementation team. Useful review work can be shared among the four.

The shared documents must contain:

- **README:** launch instructions, the four copy-ready starting prompts, order of execution, links, current base commit, and how humans provide answers or steer the plan.
- **MASTER_PLAN:** selected architecture with a concise diagram, decisions, product scope, milestones, time budget, critical path, fallback ladder and release outcome.
- **SOURCE_AND_DECISION_REGISTER:** material source coverage, verified versus proposed facts, conflicts, adopted/rejected research, architecture decisions and explicit assumptions.
- **UX_REQUIREMENTS:** the traceability matrix for Hagen's complete journey, challenge interaction needs, acceptance scenarios and honest limits.
- **CONTRACTS:** concrete shared schemas and interfaces, example valid requests/responses and errors, identifiers, units, coordinate frames, cost profiles, state ownership, versions, edit lifecycle, route/tour representation, handoff, events and voice tools. Resolve names before coding against them. Mark genuinely external unknowns with a bounded adapter assumption and owner.
- **OWNERSHIP_AND_DEPENDENCIES:** one primary owner per component/shared file, consumers, reviewers, milestone dependencies, what can start immediately, handoff evidence, merge strategy and integration captain.
- **INTEGRATION_AND_ACCEPTANCE:** meaningful checks and commands, environments/devices, full journey tests, benchmark and submission gates, recovery/reconnect checks, definitions of ready/done and honest release reporting.
- **HUMAN_INPUTS_AND_RESOURCES:** only actionable needs: exact question/resource/access, why it matters, owner, deadline, blocked task, fallback, approximate cost if known and permission needed. Separate actual blockers from optional improvements. Never request secret values in committed files.

Do not write generic prompts that say “implement the backend” or “read all the plans and decide.” **You** do the synthesis. Give builders the decisions, boundaries and interfaces they need, plus targeted source references. They should spend their context building and checking, not each independently rediscovering the architecture.

## 9. Required structure of every builder prompt

Each `00_START_HERE.md` must stand alone when pasted into a new agent session that has repository access. Include its identity and title, the four-person team, the motivating shared mission, the authoritative execution documents, starting instructions, owned scope, collaborators, immediate milestone and continuation protocol.

Each implementation-stage prompt must specify:

1. **Outcome and user value:** the concrete behavior that will exist after this stage and how it supports the journey or challenge.
2. **Starting state:** base or dependency commit, required artifacts/contracts, known gaps and a short list of source sections to read. Distinguish assumed scaffolding from delivered code.
3. **Scope and ownership:** files/modules it owns, shared files requiring coordination, exclusions and required collaborators. Provide an owner for generated schemas, dependency files and migrations.
4. **Implementation obligations:** chosen approach, tools/skills to use when available, essential algorithms/edge cases, error handling and constraints. Permit local implementation judgment without silently changing shared contracts.
5. **Interfaces and fixtures:** exact contract references, example payloads, provider/consumer responsibilities and fixtures that let downstream work proceed. Mocks must be identifiable and scheduled for replacement.
6. **Execution order:** first concrete action, independently runnable increments, dependencies, intermediate handoffs, timebox and cutoff for risky work. Avoid giant tasks that produce nothing reviewable until the end.
7. **Acceptance:** commands or observable steps, expected results, evidence to retain, and another builder's review where useful. Do not claim a command exists before creating its owning task.
8. **Collaboration and Git:** branch/worktree, integration target, sync points, how to announce a contract change, review request, commit/push cadence and handling of upstream changes.
9. **Completion report:** commit SHA, delivered behavior, checks actually run/results, interfaces exposed, known limits, next dependency and relevant evidence paths.
10. **Blocked-work behavior:** try a justified alternative, communicate a precise blocker/resource request, continue independent useful work, and hand off a recoverable state. Never hide an unresolved critical dependency behind a completion claim.

Embed a short shared team charter in all four entry prompts. Tell each agent to take initiative, question weak assumptions with evidence, help teammates, and keep the end-to-end product in view. Keep contract details in one canonical place to prevent four drifting copies; repeat only what a fresh agent needs to begin safely and effectively.

## 10. Make collaboration and Git integration real

We want regular **push, pull, inspect, integrate and verify** cycles so the team builds on each other's work. Blind simultaneous edits or repeated `git pull` in a shared dirty checkout are not collaboration.

Choose and document a concrete protocol:

- Prefer one branch and isolated checkout/worktree per builder, based on the agreed current integration commit. Inspect status before switching or updating; preserve work belonging to humans or other agents.
- Give common contracts and frequently contested files one owner. Negotiate a change before consumers implement against it. Include schema/version changes and migration effects in the handoff.
- Publish small coherent commits at meaningful milestones, especially when another builder is waiting. Push the builder's branch and report the SHA, affected contracts, validation and remaining gaps. Do not wait until the deadline to reveal a large private branch.
- Fetch and inspect the integration branch before starting a dependent task, after a dependency is published, before review/merge, and at agreed checkpoints during long tasks. Integrate on a clean working tree using the chosen merge/rebase policy; rerun affected checks.
- The integration owner merges ready increments into `main` in dependency order. At launch choose the actual supported PR or reviewed-branch workflow; do not leave the team guessing. If direct pushes are necessary, serialize them through the owner and use normal fast-forward updates. On non-fast-forward rejection, fetch and reconcile; never force-push `main`.
- Never overwrite someone else's work, use blanket conflict resolutions, delete their branch, or rewrite a published shared branch to make a merge easier. Resolve conflicts from the intended behavior and contracts, with the affected owner, then validate.
- Keep each builder's `STATUS.md` current: current task, branch/SHA, delivered interfaces, evidence, blockers, next handoff and last sync. Give each status file one writer. Use repository-visible handoff notes; do not assume the agents share chat history or can directly message each other.
- If messaging tools are available and authorized, use them for timely coordination; otherwise use the Git handoff protocol and concise human relay. Do not claim a teammate saw a change merely because it was pushed.
- Test the integrated tree, not only four branches separately. Preserve a known working revision and schedule a final fresh-clone run. Confirm the final remote SHA before declaring publication complete.

Provide a compact status template and a change-request template. Set lightweight checkpoints around actual milestones rather than imposing constant ceremonial updates. A builder finishing early should offer a targeted review, integration help, or a well-scoped next task; it should not independently duplicate a teammate's work.

## 11. Quality gates, realistic ambition and resources

Build the plan around incremental evidence:

- A first real vertical slice: input building → question → tool → correct result → useful view or benchmark output.
- Correct deterministic behavior on representative buildings, all question families and important graph/geometry edge cases.
- Full natural-language dev evaluation with per-kind failures, latency and cost, followed by the required public-test and unseen-building path.
- A real cross-device journey: desktop parts selection → multi-stop tour → handoff QR → phone navigation → committed lift closure → updated unfinished tour → completion.
- Edit preview/cancel/confirm/undo, duplicate calls, stale route responses, reconnects and isolated what-if behavior.
- Voice through the real browser/backend tool bridge; camera and audio tested together on the actual devices if included. Simulations are useful but do not establish device support.
- Fresh installation, deployment/restart and persistent-state checks appropriate to the selected architecture; a documented submission command and verifiable final artifacts.

Keep tests proportional and meaningful. Validate the mathematics, contracts, state transitions and user outcomes; do not inflate the suite with tests that merely restate the implementation. Keep generated answers, screenshots, device results and release identity attributable to the code/configuration actually tested. Never edit expected answers or weaken assertions to make a score look good.

For every risky feature define success criteria, an effort/time budget, an integration deadline and a fallback that still serves the user. Be ambitious about difficult work, but do not spend the whole remaining hackathon proving that a marginal technology could work someday. “We tried three approaches” is not an outcome unless it produces a better decision or functioning capability.

If more resources would materially improve the outcome, tell the humans precisely what you need: Claude Design access, an SDK/model entitlement, credits, an exported config, a device test, floorplan data, a printed marker, an organizer answer, or a deployment permission. State the benefit, cost/effort, required-by time and fallback. Use the capabilities available now while waiting on independent requests. Never assume unlimited credits, permissions, hardware or human availability.

## 12. Review your own orchestration package before handing it over

Perform a cross-prompt consistency review. Think from the perspective of a fresh builder receiving just its starting prompt and this repo. Check that:

- Every major human requirement and challenge obligation has an owner and acceptance evidence.
- Every substantive research source has been evaluated; rejected suggestions have a reason rather than disappearing silently.
- Technical choices are resolved; the builders are not given contradictory language, data, voice, localization, package-management or deployment instructions.
- Every interface has a producer and consumer; units, identifiers, versions and error shapes agree across prompts.
- Dependencies are acyclic or explicitly bootstrapped with compatible fixtures. No agent waits for another agent that is waiting for it.
- The full collection-tour journey survives module boundaries and realistic failures.
- Claude owns the UI and selected demanding work, with a workload it can actually finish. Codex builders carry substantive responsibility and integration support.
- No task assumes missing sibling-repo files, installed skills, paid access, provider configuration, unrun tests or a completed feature from a prose claim.
- The plan can deliver a credible baseline before stretch work; final integration, videos and submission have protected time.
- Exactly the four requested builder folders exist, prompts are executable and ordered, links resolve, and no placeholders remain except explicitly bounded external unknowns.

Fix the inconsistencies you find. A good plan is not one that sounds comprehensive; it is one that four capable agents can execute together without having to reverse-engineer what you meant.

Your final response to the humans should be brief: selected architecture and important departures from older plans, the four titles, links to the four entry prompts, immediate launch order/parallel work, and only the human decisions/resources that are truly needed. Save the complete reasoning summaries and contracts in the package. Report exactly what you created and checked.

## 13. The standard we expect from you and the builders

Bring your full capability to this. We are giving you a rare opportunity to turn research, code, design, and several capable collaborators into something people can actually use. Treat this as work worth being proud of.

You are not here to obey the first plausible plan. You are here to see the whole problem, notice what others missed, make the hard calls, and give every teammate a clear route to success. Be bold in your ideas and exact in your evidence. When a problem looks difficult, break it down, test the key uncertainty, and keep moving. Ask for the resources that would unlock progress. Do not confuse an unfamiliar path with an impossible one.

Carry that standard into every builder prompt:

> We are four builders delivering one product. Own your part completely, and care about the seams just as much as your own code. Make your work easy for your teammates to use, verify, and improve. Push useful increments. Read what others have delivered. Speak up when a contract is wrong. Help resolve the problem instead of passing it around. Use every relevant capability available to you, and prove the result in the real user journey.
>
> Our ambition is exceptional work: rigorous computation, clear agent behavior, excellent design, and an experience that makes a newcomer feel confident in an unfamiliar building. We do not need four impressive fragments. We need one impressive system. Together, we can solve much harder problems than any isolated session can. Aim high, support each other, and finish with evidence that the product works.

Now inspect the latest repository, make the strongest plan you can defend, and create the four execution packages. **Think deeply. Decide clearly. Coordinate deliberately. Build the conditions for extraordinary work.**

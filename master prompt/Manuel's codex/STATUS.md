# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 22:32 CEST · Branch: `manuel-codex/platform` · HEAD: C7 ready checkpoint (this revision) · Last sync with origin/main: `ea2a8447914dd014bd761491a014537073394719` (22:14 CEST)

Single writer: Manuel's codex. Structure follows OWNERSHIP_AND_DEPENDENCIES §7.

## Current task
Rechecking G3/G4 against core6fad985, Lenard e781afd and web9a65c0a. L02 still fails CR-M-5; L03's independent offline checks pass, but its branch includes L02. Web's C6 stairs, reconnect and display wiring pass preview; blocked voice context and optional-final-leg UI remain red. C7 and the independently consumed core fixes are now ready: full check350passed/2explicit L02-absence skips,39Bun,evaluations/build. Next is clean-main verification and production smoke. G1/G2 remain intact; no red team checkpoint is on main. Scope remains repository-only.

## Delivered (newest first)
- C7 ready increment: preserves active status with a remaining end leg; next_step guides it without claiming completion; reserved progress stop_id=end confirms explicit arrival in the same tour. Stale building/profile state refreshes before instructions. Core/kit tests cover closure/reopen, exact0/.25m coordinates, restart, idempotence and latest caller position. **169 server tests pass,2 explicit L02-absence skips;78 focused checks pass.** Independent follow-up review approved all fixes.
- Kit parity: collected middle stops retain their prescribed sequence when restored; physical stairs stay excluded for step-free routing even if source data wrongly flags them accessible. Four independent HTTP tests pass; loading the old adapter produced the two intended kit failures.
- Reusable `scripts/check_live_integration.py`: isolated loopback uvicorn/temp state, blank provider keys, budget0, real HTTP/WS timings, conflicts/idempotence, collected stops, wheelchair no_route, missed-change catch-up and hard restart. Normal and real TERM/INT-during-cleanup tests pass; all own processes/state removed.
- New `tests/server/test_chat_budget_boundary.py`: two actual-SDK HTTP seams. Agent-free main explicitly skips; published L02 genuinely fails both; proposed owner patch passes36 agent/seam tests in an ignored overlay. Tracked agent/bench files remain untouched.
- Core b1b8e2e consumed unchanged as54f3778, author retained: native GEOS concurrency lock, exact point endpoints, physical-stair safety and stable tour restoration.30 focused core tests pass. Whole core6fad985 includes failing L02, so it was not merged wholesale.
- Web9a65c0a preview: real3-part plan, decoded QR, phone confirmation/progress; admin-confirm→phone-banner266/267/230ms; missed-WS-change catch-up retains progress; explicit C6 stairs retains the same tour/3IDs/2collected/fixed order/width0.6/exclusions. Offline hook double verifies actual find highlight, instruction refresh and returned-tour navigation; no live SDK/provider claim.52 Bun tests and build pass. Remaining failures are below.
- Shipped C6: code main3af89ab, documentation mainea2a844; explicit partial replan constraints, mobility safety and exact production/restart smoke. Earlier C5 fixes exact/fuzzy lookup, closure lists and reopened fixed-stop ordering.
- M02 foundations: SQLite state/migrations, sessions/tour revisions/events/proposals, idempotency/conflicts/undo, WS, eleven tools, handoff/progress/replan, voice token/hook, chat adapter, uploads, markers and opt-in reset. M03 device probes/frame/arrow helpers are delivered; physical devices and AR rendering remain gated.
- M01:917980c dependencies pushed within ten minutes;682441a rules/environment;53eb592 server/Docker/checks. No kit edits.

## Interfaces exposed / changed
- C7 contract/code/OpenAPI are published with this ready checkpoint: final-destination semantics use existing progress and next_step. No new endpoint/tool or synthetic collection stop; C2–C6 remain valid. Consumers can now implement against this pushed checkpoint.
- A positive remaining final leg keeps status=active. next_step returns stop_id=end, complete=false and eventually at_end=true; directions alone never establish physical arrival.
- Confirm final arrival with POST /api/tours/{id}/progress body {"stop_id":"end","status":"collected"} and the phone's X-Session-ID. Requires an end, all collection collected and a fresh reachable route; records the exact end and completes the same tour. Pending is invalid for the reserved ID.
- C6 stairs remains explicit: PATCH profile=walk with existing session constraints plus step_free=false, then replan with constraints:{step_free:false}; other fields/progress remain. Non-walk profiles force step-free routing.
- Registry remains `from server.tools import registry`, json_schemas()/call(name,session_id,args). Chat constructor is ChatAgent(registry,store.get_session). API types come from server/openapi.json; Claude regenerates them.
- WS registration precedes version fetch; reconnect compares snapshot and saved-tour versions. GET tour does not recompute a route. Provider keys stay server-side; missing voice/chat returns explicit unavailability.
- Local API verification: `uv run python scripts/check_live_integration.py --output agent_output/reports/live-integration.json`. It cannot target an external service.

## Merge log (captain)
| Window | Main / inputs | Checks | Tag / deployment |
|---|---|---|---|
| Current C7 window | Pending; core54f3778 and server C7 on platform | Focused checks below; full C7/main/production checks pending | No G3/G4 tag; repository-only |
| C6 | Code3af89ab; final docs **ea2a8447914dd014bd761491a014537073394719** |305 Python,39 Bun,oracle369/369,devtext138/138,build,Docker/restart|G1/G2 preserved; repository-only|
| C5 | Coreb57d39f + platforme40e780 + benchee38da7 ->a8be9ec |275 Python,39 Bun,evaluations/build|G1/G2 preserved|
| G2 | platform1a5c491/core6452bda/benche1c2dfd ->**0e892435d7a37e2b201bccc0f26e22c40358833c**|250 Python,39 Bun,evaluations/build,officialdev/CSV|gate-G2|
| G1 | core4e6f956/platformd187ce5/bench4d93bdb/webe29fc43 ->**8baa2c65b1bda13b1596e28c652aaa6f41a00e99**|214 Python,39 Bun,oracle369/369,devtext138/138,structureddev138/138/train517/517,health/fixtures/build|gate-G1|

## Evidence
- Current reports: agent_output/reports/{l02-recheck,c02-recheck,c7-final-leg-review,g34-api-recheck}/. Each records exact published SHA or explicitly fingerprints the C7 working tree. Preview results are not main/gate claims.
- C7 platform full check exit0: **350 passed,2 skipped** (39.38s), oracle369/369,coredevtext138/138,39Bun,strictTS/Vite/device-gate build; /private/tmp/tyb-c7-platform-check.log. Skips mean L02 is absent, not that its failing budget tests passed. Native/core and server follow-up reviews are clear.
- L02 e781afd:125 owner agent/bench tests pass; Sunday15/15 answers,7 route/tour legs independently match paths/lengths. Two new server budget seams fail on unmodified published agent. Proposed terminal guard passes36/36 in isolation; no provider calls. agent/chat.py is unchanged from the original failing checkpoint.
- Web9a65c0a: actual mainC6 API/browser preview and source-module checks pass the flows listed above, but blocked voice context regression fails. C7 real API produces active17.1m with all parts collected; exact remote guidance returns currentLeg=null/index−1 and its done expression shows premature completion/hides the map. Two final-leg UI assertions fail.
- C7 focused backend:169 server tests passed/2 explicit agent-absence skips;78 end/move/fixed-order/tool/core-end checks pass. Core review30 pass, kit parity4 pass. The original stale-instruction, same-room-point and profile-safety regressions failed before fixing and now pass; independent follow-up review is clear.
- Exact existing mainea2a844 local API trials:78.30/66.37/63.65ms commit→WS→snapshot/tour refetch→replan; three parts plan49.16ms. Two collected IDs, wheelchair blocked reasons, duplicate commit/undo, version conflict, offline catch-up and exact session/tour/7event retention after SIGKILL pass. Physical phone/UI automatic reconnect are separate acceptance.
- Final verifier form before C7:114.37/88.40/80.01ms; real TERM+INT during bounded cleanup exercises timeout→kill and confirms JSON/state/process cleanup. Pre-fix failure retained. New-test platform full check before core/C7:305passed/2skipped,39Bun,oracle369/369,devtext138/138/build; /private/tmp/tyb-g34-platform-check.log.
- C6 production exact3af89ab: image tyb-c6-main sha256:d77669dfbb896c052b2740e8803c417247af5af5e9b379bc62eef2266d9e6bfa,129947276bytes arm64. Health/SHA/static/API, mobility/IDs, restart and runtime whitelist pass;280 buildings/equipment plus manifest, no evaluation labels/submissions. Report agent_output/reports/c6-main/ includes finalea2a844 full-check metadata. No external deployment.
- G2 CSV remains145 unique rows,6337bytes; SHA256 d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f; validator/independent officialdev138/138 pass. Hidden test accuracy unknown.
- No force pushes, paid/provider calls, external captain deploys or kit edits. Human checkout remains untouched.

## Blockers and resource requests
- L02 e781afd still fails CR-M-5. L03 has no separate concrete offline blocker, but shares that branch/dependency.
- Web9a65c0a still fails blocked speech and C7 final-destination UI. Its ordinary52 tests/build do not cover those failures.
- Human steering remains “just do all in the repo — elevenlabs agents will be implemented.” No credential/setup questions. Live voice/chat quality, real Android/iPhone, camera/AR and Railway release are unverified; venue measurements absent, factory fallback available.
- G3/G4 gate tags require corrected integrated main and actual remaining acceptance; preview/API timings alone do not establish physical-phone acceptance.

## Change requests
- **CR-M-5 to Lenard, still open at e781afd:** agent/chat.py reserves again after terminal end_turn. One actual request costs$0.00030, but a false second reserve under cap$0.04180 discards the answer/display. Exit the runner after a terminal response before reserving again; retain pre-request reservation for real calls. Do not simply advance the iterator before reservation. Proposed patch and before/after logs: agent_output/reports/l02-recheck/; automatic server seams will be pushed with this increment.
- **CR-M-3 remainder to Claude, web9a65c0a:** callback/new-tour display wiring now passes offline. guidance.ts context.replanned still uses order-only blockedReason, so an actual fully blocked tour says “replanned:0m,next none.” Inspect unreachable_stops/status; say no route and name the lost stop/reason. Add the actual blocked-context regression, and update owner STATUS to the tested tip/contract.
- **CR-M-6 to Claude, C7 optional end:** Journey's all-collected done shortcut prematurely shows completion and hides the map for an active17.1m final leg. Use server status for completion; select the remaining end leg/index/label when collection order is empty; show explicit arrival action POST progress stop_id=end/status=collected with X-Session-ID. Preserve blocked-end reasons and original collection IDs. currentLeg/currentLegIndex and voice context need this end concept. Exact real payload/module proof: agent_output/reports/c7-final-leg-review/. Consume after C7 code/schema push.
- **CR-H-4 accepted in C7 (this checkpoint):** preserve core end status, guide final leg and confirm exact arrival. Stale-instruction, exact same-room-point and effective-profile review failures are fixed and tested before main.
- **CR-M-2/4 and CR-C-1 resolved in9a65c0a preview:** lost visual stops, stale-version/reconnect recovery and explicit C6 same-tour stairs retain identity/progress/constraints. Remaining branch failures are separately listed above.
- Previous accepted changes remain: CR-L-1 atomic mobility (C4), CR-L-2 closure lists (C5), CR-L-3 resolution precedence (C5), CR-H-2 moved parts (d55d0ac), CR-H-3 production data whitelist (1a5c491), CR-M-1 admin/phone transport (C2).
- CR-L-4 Sunday spatial constraints remains explicitly unsupported/provisional; core/benchmark owners must agree semantics when organizer inputs arrive. No invented Sunday schema or paid result.

## Next handoff
- Lenard: fix CR-M-5, run `uv run pytest -q tests/agent tests/server/test_chat_budget_boundary.py` after consuming platform, republish. Existing exact CNC acceptance is green.
- Claude: fix blocked context and C7 final-leg UI, regenerate API types, keep real blocked/final-leg fixtures in tests and publish current STATUS. Backend/contract C7 is ready in this pushed checkpoint.
- Captain: finish C7/core/kit full check, publish runnable platform, integrate only green owner increments in clean main, run required check and production smoke, push normally. Preserve G1/G2. G3/G4 remain pending until demonstrated.
- M03 real device gate/AR, Sunday Linux rehearsal, real voice, release and final submission remain future acceptance work.

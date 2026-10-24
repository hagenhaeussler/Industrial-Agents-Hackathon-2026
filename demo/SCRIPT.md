# Demo script: Talk to Your Building

Working title: **Talk to Your Building**. Proposed closing line: **"Know what you need. Let the building show you where."** Humans may change both before recording. Use the kit factory `proc-factory-dev-003` ("Fertigung Ost 27") from `demo/scenario.json`; `demo/hero/README.md` records the pending venue-measurement handoff. Read distances from the current screen; they depend on the start, chosen parts, profile and closures.

Preview: [desk](https://hagen-core-test-testing.up.railway.app/desk?demo=hero), [admin](https://hagen-core-test-testing.up.railway.app/admin?demo=hero), [device checks](https://hagen-core-test-testing.up.railway.app/devtest.html). The admin code is shared privately, never in a link or recording. This is a shared preview building: coordinate resets/closures with coworkers or upload a separate JSON building for independent experiments.

Recording status: no two finished videos or physical-phone rehearsal are claimed by this script. The tables below are the shot list and operator runbook. Browser/API smoke evidence is recorded separately in the release report. Map and text/buttons are the reliable demo path; test actual microphone audio and camera permissions on each phone before including them.

The three moments: **Say what you need, not where it is** (desk) · **From screen to hand** (QR to phone) · **The building reacts** (closure, reroute).

## 0. Setup (10 minutes before, every run)

| Where | What |
|---|---|
| Server | `TYB_DEMO_MODE=true` and `TYB_ADMIN_TOKEN=<admin code>` (private environment variables); `/health` shows the expected release commit and a nonzero buildings count |
| Laptop window 1 (projector, 1280×800 or 1920×1080) | `https://<host>/desk?demo=hero` — the three parts are preselected, "You are at Hall access 0.19" |
| Laptop window 2 (second desktop or a tab) | `https://<host>/admin?demo=hero`; enter the admin code once (kept for this tab only), then keep the tab open |
| Phone | screen mirrored (Android: `scrcpy`; iPhone: QuickTime). Camera app ready to scan. Screen brightness up, auto-lock off |
| Reset | in admin, **Reset demo** (bottom of the panel) twice; the event log says "No changes yet" |
| Desk | "How do you move?" = **Walking**; press "Change parts" if an old tour is shown |

Positions on the projector: desk panel left, map right; the phone mirror goes on the right half over the map only after the QR is scanned.

## 1. Demo video (60 s)

| Time | Picture | Spoken line (voice-over) | Who clicks |
|---|---|---|---|
| 0–8 s | Manfred at the hall entrance, phone in hand (real hall or the factory map full screen) | "This is Manfred. First week in the hall. He needs three parts and has no idea where they are." | – |
| 8–25 s | Desk. Type or say: **"I need the 3D printer H-A3-A, the tool cabinet H-A1 and UPS unit 1.05."** The parts light up. If the agent has not already planned a tour, press **Plan collection tour**: numbered stops, optimal-order label and computed metres | "He says what he needs, not where it is. The building finds the parts on both floors and plans the shortest collection route." | Laptop operator |
| 25–42 s | Press **Send to phone** → QR → phone camera scans → tour opens → **Yes, I am here** → banner "Go through the door into Office corridor 0.16." → **Next step** to "Take the Office staircase to Floor 1." | "One scan and the same tour is on his phone, step by step, with landmarks." (voice agent if live: it reads the step) | Phone operator |
| 42–55 s | Admin window: **Office staircase → Close…** → preview with the actual affected-tour distances → **Confirm**. Cut to the phone: banner names the closure, Office lift and actual distance change, the line moves to the lift, the stairwell is hatched red | "Facilities close the staircase. Manfred's phone replans, tells him why, and takes him round by the lift." | Laptop operator, then phone close-up |
| 55–60 s | Phone: **Got it** on the last stop → "All 3 parts collected", happy avatar. If a finish was selected, complete its final leg with **I have arrived** first. Product name | "Talk to Your Building. Know what you need. Let the building show you where." | – |

Do not use the proposed filament/torque-wrench/steel-drum hero script: those assets are not in the shipped factory scenario.

## 2. Technical video (60 s)

| Time | Picture | Line |
|---|---|---|
| 0–12 s | Architecture picture (MASTER_PLAN §2): one web app, one service, Python core, tool registry, ElevenLabs/Claude agents | "One app, one service. The language model interprets; deterministic rules decide." |
| 12–25 s | Desk tour panel → open **How I calculated this**: route model, exact order, per-leg rooms and doors, tool trace | "Every number on screen comes from the core: the same route model that scores the benchmark." |
| 25–40 s | Read the current `BENCHMARK.md`: distinguish kit oracle 369/369, public-template dev 138/138 and separate paraphrase/live-model results. Template evaluation has no model cost; show live cost only from a dated report. Public test accuracy is hidden. | "We measure deterministic answers and new wording separately." |
| 40–52 s | Bonus (only if the chat agent is live): "Water is dripping from the ceiling in office 0.29. What's above it?" → the room above is highlighted on the next floor | "Spatial questions, answered from geometry." |
| 52–60 s | Admin upload of a `building.json` → validation report → "Open in desk" → plan a tour | "A new building is one upload away." |

## 3. Final pitch (3 minutes + 1 minute Q&A)

| Time | Beat | Spoken | Action | Fallback (MASTER_PLAN §6) |
|---|---|---|---|---|
| 0:00–0:20 | Problem | "New people in big buildings lose twenty minutes a day looking for things. Signs show rooms, not parts. Manfred knows what he needs, not where it is." | title slide or desk at rest | – |
| 0:20–1:00 | **Aha 1** | "So he just says it." Say/type the sentence. "The parts light up on two floors … and the building plans the shortest collection route." Read the metres and order label shown. | desk: ask → Plan if needed | voice down → type the same sentence; chat down → the ask box searches the parts list (it says so); everything down → tick the three parts in the list |
| 1:00–1:35 | **Aha 2** | "From screen to hand." Scan. "Same tour, same order. It asks where he is, because we never pretend to know." **Yes, I am here.** "Turn by turn, with landmarks." | Send to phone → scan → Yes → Next step ×2 | phone fails → open the short link in a second laptop window (mobile size) |
| 1:35–2:15 | **Aha 3** | "Now the building changes." Admin: Close the office staircase. "We see the affected tours before anything happens." Read the preview. Confirm. "His phone replans, tells him why, and keeps what he already collected." | admin Close… → Confirm → phone close-up | voice admin down → the Close… button is the primary path; WS down → the phone replans on reconnect |
| 2:15–2:40 | How it works | "Underneath: the kit's route model reproduced exactly, 369 of 369 oracle routes, 138 of 138 dev questions from text. Exact tour order up to twelve stops. Every answer can show how it was calculated." | open **How I calculated this** | – |
| 2:40–3:00 | Why it matters | "Any building with a floor plan and a parts list. Upload it, and it talks back." Name + closing line. | admin upload screenshot or live upload | – |

Wheelchair variant for Q&A (30 s target; rehearse on the actual phones): desk "How do you move?" → **Wheelchair**, plan via the Office lift, phone opens; admin closes the **Office lift** → phone names the lift, UPS and lack of a step-free route. **Show the route with stairs** is offered only on request. Read actual computed distances.

## 4. Q&A answers (short)

- **How does it know where I am?** It starts where the desk said, asks you to confirm, and position codes supply a declared standing point and direction. Progress comes from "Next step" and "Got it". The camera overlay is labelled direction only. Compatible Android browsers can try an experimental current-floor AR ribbon after standing/facing confirmation; alignment and drift still need a real-device check. No Wi-Fi positioning.
- **How exact are the routes?** The kit route model is reproduced exactly: 369/369 oracle routes, dev 138/138 from question text. "Optimal" means shortest under that model; exact up to 12 stops, labelled heuristic above.
- **A new building?** Upload a `building.json`: validated, then every tool works (shown live). Image import is a measured spike (H04), not the reliable path.
- **What does the LLM do?** It interprets what you say and calls tools. Every fact it states comes from the tools; edits always need a preview and an explicit yes, once.
- **Cost and speed?** Show the dated release's measured API/browser timings, separately from model response time and physical QR scan time. Template benchmark inference has no provider charge. Live Anthropic/ElevenLabs smoke costs and limits are documented in `docs/live-provider-setup.md`; no full voice/model comparison is implied.
- **Is the part movement real?** Only when an admin moves a part. Anything simulated carries a "Simulated" label.

## 5. Rehearsal log (fill in at G7)

| Run | Aha 1 (request → route) | Aha 2 (scan → tour) | Aha 3 ("Yes" → new route) | Total | Misses |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

Targets: route visible < 3 s after the request; tour on the phone < 2 s after the scan; new route ≤ 2 s after "Yes"; total ≤ 3:00.

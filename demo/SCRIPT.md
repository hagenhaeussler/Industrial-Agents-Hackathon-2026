# Demo script: Talk to Your Building

Owner: Manuel's Claude. Working title "Talk to Your Building" until the humans confirm the product name and closing line (Q-7). Building: the kit factory `proc-factory-dev-003` ("Fertigung Ost 27") as the fallback from MASTER_PLAN §6 step 5; switch to the hero building when `demo/hero/` exists (then update the names in square brackets).

The three moments: **Say what you need, not where it is** (desk) · **From screen to hand** (QR to phone) · **The building reacts** (closure, reroute).

## 0. Setup (10 minutes before, every run)

| Where | What |
|---|---|
| Server | `TYB_DEMO_MODE=true`; `/health` shows the expected commit and `buildings: 280+` |
| Laptop window 1 (projector, 1280×800 or 1920×1080) | `https://<host>/desk?demo=hero` — the three parts are preselected, "You are at Hall access 0.19" |
| Laptop window 2 (second desktop or a tab) | `https://<host>/admin?demo=hero` |
| Phone | screen mirrored (Android: `scrcpy`; iPhone: QuickTime). Camera app ready to scan. Screen brightness up, auto-lock off |
| Reset | in admin, **Reset demo** (bottom of the panel) twice; the event log says "No changes yet" |
| Desk | "How do you move?" = **Walking**; press "Change parts" if an old tour is shown |

Positions on the projector: desk panel left, map right; the phone mirror goes on the right half over the map only after the QR is scanned.

## 1. Demo video (60 s)

| Time | Picture | Spoken line (voice-over) | Who clicks |
|---|---|---|---|
| 0–8 s | Manfred at the hall entrance, phone in hand (real hall or the factory map full screen) | "This is Manfred. First week in the hall. He needs three parts and has no idea where they are." | – |
| 8–25 s | Desk. Type or say: **"I need the 3D printer H-A3-A, the tool cabinet H-A1 and UPS unit 1.05."** The parts light up, press **Plan collection tour**: numbered stops, "Optimal order · 97 m", the route draws itself | "He says what he needs, not where it is. The building finds the parts on both floors and plans the shortest round trip." | Laptop operator |
| 25–42 s | Press **Send to phone** → QR → phone camera scans → tour opens → **Yes, I am here** → banner "Go through the door into Office corridor 0.16." → **Next step** to "Take the Office staircase to Floor 1." | "One scan and the same tour is on his phone, step by step, with landmarks." (voice agent if live: it reads the step) | Phone operator |
| 42–55 s | Admin window: **Office staircase → Close…** → preview "1 active tour affected: 97 m → [N] m" → **Confirm**. Cut to the phone: banner **"Office staircase is closed. New route via Office lift (+[N] m)."**, the line moves to the lift, the stairwell is hatched red | "Facilities close the staircase. Within a second Manfred's phone knows, tells him why, and takes him round by the lift." | Laptop operator, then phone close-up |
| 55–60 s | Phone: **Got it** on the last stop → "All 3 parts collected", happy avatar. Product name | "[Product name]. [Closing line]." | – |

Hero-building variant (when it exists): "I need the filament, the torque wrench and the steel drum." / "Close the east lift." → "New route via Stairs B".

## 2. Technical video (60 s)

| Time | Picture | Line |
|---|---|---|
| 0–12 s | Architecture picture (MASTER_PLAN §2): one web app, one service, Python core, tool registry, ElevenLabs/Claude agents | "One app, one service. The language model interprets; deterministic rules decide." |
| 12–25 s | Desk tour panel → open **How I calculated this**: route model, exact order, per-leg rooms and doors, tool trace | "Every number on screen comes from the core: the same route model that scores the benchmark." |
| 25–40 s | Benchmark numbers from `BENCHMARK.md` (Lenard's codex): kit oracle 369/369, dev 138/138 from question text, train structured 517/517, cost per question [fill from BENCHMARK.md] | "Measured, not claimed." |
| 40–52 s | Bonus (only if the chat agent is live): "Water is dripping from the ceiling in office 0.29. What's above it?" → the room above is highlighted on the next floor | "Spatial questions, answered from geometry." |
| 52–60 s | Admin upload of a `building.json` → validation report → "Open in desk" → plan a tour | "A new building is one upload away." |

## 3. Final pitch (3 minutes + 1 minute Q&A)

| Time | Beat | Spoken | Action | Fallback (MASTER_PLAN §6) |
|---|---|---|---|---|
| 0:00–0:20 | Problem | "New people in big buildings lose twenty minutes a day looking for things. Signs show rooms, not parts. Manfred knows what he needs, not where it is." | title slide or desk at rest | – |
| 0:20–1:00 | **Aha 1** | "So he just says it." Say/type the sentence. "The parts light up on two floors … and the building plans the shortest round trip: three stops, 97 metres, optimal order." | desk: ask → Plan | voice down → type the same sentence; chat down → the ask box searches the parts list (it says so); everything down → tick the three parts in the list |
| 1:00–1:35 | **Aha 2** | "From screen to hand." Scan. "Same tour, same order. It asks where he is, because we never pretend to know." **Yes, I am here.** "Turn by turn, with landmarks." | Send to phone → scan → Yes → Next step ×2 | phone fails → open the short link in a second laptop window (mobile size) |
| 1:35–2:15 | **Aha 3** | "Now the building changes." Admin: Close the office staircase. "We see the effect before anything happens: one tour affected, a few metres longer." Confirm. "His phone replans immediately, tells him why, and keeps what he already collected." | admin Close… → Confirm → phone close-up | voice admin down → the Close… button is the primary path; WS down → the phone replans on reconnect |
| 2:15–2:40 | How it works | "Underneath: the kit's route model reproduced exactly, 369 of 369 oracle routes, 138 of 138 dev questions from text. Exact tour order up to twelve stops. Every answer can show how it was calculated." | open **How I calculated this** | – |
| 2:40–3:00 | Why it matters | "Any building with a floor plan and a parts list. Upload it, and it talks back." Name + closing line. | admin upload screenshot or live upload | – |

Wheelchair variant for Q&A (30 s, rehearsed): desk "How do you move?" → **Wheelchair**, plan (117 m via the Office lift), phone opens; admin closes the **Office lift** → phone: "Office lift is closed. UPS unit 1.05 can no longer be reached step-free: the Office lift was the only step-free way there. The other stops are replanned." → **Show the route with stairs** only on request.

## 4. Q&A answers (short)

- **How does it know where I am?** It does not track you. It starts where the desk said, asks you to confirm, and printed position codes on doors set an exact standing point and direction. Progress comes from "Next step" and "Got it". Between codes only the Android AR session tracks motion; the iPhone overlay shows direction, not position. No Wi-Fi positioning.
- **How exact are the routes?** The kit route model is reproduced exactly: 369/369 oracle routes, dev 138/138 from question text. "Optimal" means shortest under that model; exact up to 12 stops, labelled heuristic above.
- **A new building?** Upload a `building.json`: validated, then every tool works (shown live). Image import is a measured spike (H04), not the reliable path.
- **What does the LLM do?** It interprets what you say and calls tools. Every fact it states comes from the tools; edits always need a preview and an explicit yes, once.
- **Cost and speed?** Plan → route on screen in well under a second locally; building change → new route on the phone ≈ 0.15 s locally, ≈ 0.7 s commit-to-reroute on Railway (Hagen's cloud trials). Cost per benchmark question: [fill from BENCHMARK.md].
- **Is the part movement real?** Only when an admin moves a part. Anything simulated carries a "Simulated" label.

## 5. Rehearsal log (fill in at G7)

| Run | Aha 1 (request → route) | Aha 2 (scan → tour) | Aha 3 ("Yes" → new route) | Total | Misses |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

Targets: route visible < 3 s after the request; tour on the phone < 2 s after the scan; new route ≤ 2 s after "Yes"; total ≤ 3:00.

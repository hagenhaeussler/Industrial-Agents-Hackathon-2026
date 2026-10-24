# Open questions for the judges - ranked by importance

**Reviewed:** 24 October 2026, against team-repo commit `1537c04` and its supplied evidence, including the latest Cloudflare plan update pulled during this review. **Status:** questions still requiring confirmation; no answer below is presented as a new organizer decision.

The ranking reflects the risk of implementing the wrong scoring contract, submitting an unusable artifact, or spending the remaining time on the wrong scope. Ask **1-6 first**. Questions 7-12 are follow-ups; skip anything already settled by a definitive answer or reference implementation.

## Quick list

| Rank | Priority | Ask about | Decision it changes |
|---|---|---|---|
| 1 | Answered | Which routing/scoring rules apply to which evaluation? (kit 1.1.0) | Correctness of the core and numerical answers. |
| 2 | Critical | Exact Sunday input/output schema and question families. | Parser, serializer and valid submission. |
| 3 | Critical | Sunday execution, release window and runtime limits. | Reproducible evaluation and processing budget. |
| 4 | High | Minimum Build scope and whether raw-plan import is assessed. | Whether image import is optional in practice. |
| 5 | High | Allocation of the 55 functionality points. | Time allocation across benchmark, Build and scaling. |
| 6 | High | Machine-readable forklift and production-bay rules. | Valid vehicle routes and the logistics demo. |
| 7 | High | Judge-side ElevenLabs access and accepted fallback. | Whether the judges can reproduce the main interaction. |
| 8 | Medium | Exact route measurement in ambiguous cases. | Consistency with the new route scorer. |
| 9 | Medium | Whether cross-building routing is assessed, and with what links. | Scope of Level 3 beyond multiple floors. |
| 10 | Medium | How the 25 interaction points are actually tested. | Demo scenarios, device support and conversation behavior. |
| 11 | Medium | How track scores feed into the joint final. | Final pitch and live-demo preparation. |
| 12 | Lower | Whether benchmark questions share persistent edits. | Reset semantics and reproducible what-if answers. |

## Questions to ask

### 1. Which scoring model is authoritative for each evaluation?

**Answered by kit 1.1.0 (24 October 2026):** one route model now applies to all expected answers, including the hidden test answers. See `CHANGELOG.md` and README section 3. Routes start and end at the room's centre point (`representative_point`), the lift's 15 m counts once per ride, and there is no way round the outside. Do not ask this question. The text below is kept as history.

> Could you confirm, separately for the published 145-question test set and the unseen-building check, which route model and scorer apply? Does the new door-to-door geometry announcement replace the README model everywhere, or only for explicit route questions? In particular, what applies to `errand` distances and `what_if_door` counts?

**Why this is first:** The README uses room anchors, 12 m per floor for stairs and 15 + 6 m per floor for lifts. The saved announcement uses paths around corners, 15 cm wall clearance, and height-based vertical costs. The current `benchmark/score.py` checks committed numerical/room answers; it does not validate an ordered route or implement the announcement's best-length/returned-length score. A different route model can also change which item is nearest and how many rooms benefit from a new door.

**Useful confirmation:** A per-evaluation/per-question applicability table and the official versioned scorer or a small worked reference case. The two-model split in `PLAN.md` is a team assumption until confirmed. The copied announcement has no original message URL or posting timestamp.

**Evidence:** [README](README.md), route-model and scoring sections; [routing code](starter_agent/building_map.py); [answer scorer](benchmark/score.py); [saved route announcement](2026-10-24-route-scoring-specifications.md); [team plan](PLAN.md), sections 1 and 5.

### 2. What exactly must the Sunday command read and produce?

> Please share the final schema and one valid input/output example for Sunday. Is it `questions.json` and `answers.json`, JSONL plus the existing CSV, or separate formats for separate checks? Which question families can appear, what IDs belong in a route, and how should an unreachable result be represented?

**Specific gaps:** The PDF says ordered node IDs, while the route announcement says ordered spaces. The current CSV contains full text ending in `Answer:`. The published benchmark has nine families, while warm-ups add six families including direct routes and tours. The data folder contains no standalone Sunday schema/example-answer file of the kind promised as TODO in the PDF.

**Useful confirmation:** One example each for a numerical answer, located item, route/tour and unreachable case, including required fields and whether `kind` and structured constraints are supplied. Also confirm whether the original 145-question CSV remains a separate required artifact.

**Evidence:** [Challenge brief](<Hackathon Challenge - Talk to Your Building-1.pdf>), page 3; [README](README.md), sections 4-6; [evaluator](benchmark/evaluate.py); lead Q&A 20:25-24:26 in [the follow-up recording notes](2026-10-24-challenge-lead-qa.md).

### 3. How and when will the unseen-building run happen?

> Will Sunday input be released to teams before the 13:00 code freeze, or will the judges run our frozen code on private input? When does the timed window start, what counts toward it, and what runtime/API limits apply?

**Follow up as needed:** Include building preprocessing, allowed concurrency, network/model access, rate limits and the judge's execution environment. If judges run it, confirm the required command and configuration contract; if teams run it, confirm the result-upload deadline and channel.

**Why still open:** The README/PDF describe a team-run command plus a possible rerun. The lead also described judge-run code and used 200 questions/five minutes as an illustration. That was not an agreed limit. The overall Sunday 13:00 freeze is already documented; the missing information is the evaluation window around it.

**Evidence:** Challenge brief page 3; kickoff slide 32; [lead Q&A](2026-10-24-challenge-lead-qa.md), 20:25-24:26.

### 4. Do local edits satisfy Build, or is image-to-building import separately graded?

> To make our scope explicit: can local what-if operations on an existing building, such as adding a door or closing a lift, satisfy the assessed Build requirements? Is creating a new building from a raw floor-plan image separately tested or required for full functionality points? If so, what exact input and acceptance example should we support?

**Follow up:** Is a supplied `building.json` sufficient for the unseen-building check, and are preview/confirmation or manual corrections allowed in a separate import interaction?

**Why:** The written Level 4 and functionality rubric mention new buildings from plans. The lead emphasized local changes and said full reconstruction was not necessarily needed. His claim that JSON lacks room layouts also conflicts with the supplied polygons and JSON-only viewer. `PLAN.md` makes PNG import optional; that is not yet a definitive written exemption from the rubric.

**Evidence:** Challenge brief pages 1-3; [starter README](starter_agent/README.md), Level 4; [lead Q&A](2026-10-24-challenge-lead-qa.md), 01:09-03:05 and 05:55-08:47.

### 5. How are the 55 functionality points divided?

> How much of the functionality score comes from the published test CSV, the unseen-building run, route validity/optimality, Build and multi-building support? Are there feature-specific caps or minimum requirements, and are question types weighted equally?

**Why:** We already know the overall 55/25/10/10 rubric. What remains missing is the allocation inside functionality, which determines whether another hour should go into spatial accuracy, plan import or scaling. We are asking for the grading structure, not a guaranteed finalist score.

**Evidence:** Challenge brief page 3; [README](README.md), Judging; [lead Q&A](2026-10-24-challenge-lead-qa.md), 18:22-20:24.

### 6. Which data fields identify forklift aisles and destination-only production bays?

> For the forklift rule, which exact field/value mapping marks an allowed aisle versus a pedestrian walkway? Is an opening at least 3 m wide necessary but insufficient? Which room types count as production bays that may be entered as a destination but not used for transit?

**Follow up:** Please include how to treat `production_zone`, `assembly_zone`, `additive_zone`, `warehouse_zone` and `logistics_zone`, and whether the rule also permits leaving a bay used as the start.

**Why:** Across all supplied building records, spaces have `type` and `room_type` but no explicit forklift/pedestrian flag. Openings at least 3 m wide also occur in residential sources, so width alone cannot establish aisle semantics. The existing 1.1 m pallet/trolley questions should not silently inherit a different forklift constraint.

**Evidence:** [route announcement](2026-10-24-route-scoring-specifications.md); [manifest](data/manifest.csv) and building records; [PLAN.md](PLAN.md), sections 5 and 10.

### 7. How can the judges reproduce our ElevenLabs-based interaction?

> You confirmed OpenAI/Anthropic access. Can the judges also run an exported ElevenLabs agent configuration with their own account, or can interaction be assessed through our public app URL and video while the independently runnable fallback uses text with the same backend tools? What minimum setup must we hand over?

**Why:** The updated plan uses a public Cloudflare app, ElevenLabs-managed conversation and client tools in the browser, with a local benchmark independent of both services. Provider freedom does not establish ElevenLabs access or shared agent configuration. This question concerns reproducibility and interaction credit; selecting client tools versus webhooks remains our own engineering decision.

**Evidence:** [lead Q&A](2026-10-24-challenge-lead-qa.md), 10:07-12:23 and 24:24-25:33; [PLAN.md](PLAN.md), sections 2-4.

### 8. Can we match the reference route measurer on ambiguous cases?

> If a reference implementation is not available, could you provide a worked case specifying the start/end position within a room, the choice among multiple doors between the same spaces, the lift wait across several stops, and how outside travel is measured?

**Only ask unresolved parts after question 1:** Does the scorer infer the best compatible doorway/connector sequence from our space list? Is the 15 m lift charge once per continuous ride or per floor-to-floor edge? Does the free shared `outside` node survive in the new model? How is a door connected to the path after the 15 cm inset, especially when the inset splits a narrow space?

**Why:** The supplied records include two internal space pairs with multiple openings, 104 lifts serving at least three stops, and 135 buildings with multiple entrances. These cases make the difference observable. Do not spend judge time debating our algorithm if their scorer can settle the reference behavior directly.

**Evidence:** [route announcement](2026-10-24-route-scoring-specifications.md); [routing code](starter_agent/building_map.py); dataset audit below.

### 9. Is routing between buildings assessed, and where do the connections come from?

> Does Level 3 require routes between separate buildings for the scored check, or is several-floor routing sufficient for that check? If cross-building routes are assessed, will you supply outdoor links and a shared coordinate frame, or should teams author those links for their demo?

**Why:** The written level includes both. Existing files describe separate buildings with local coordinates and no supplied cross-building link graph. An arbitrary link invented by us would not be a reliable evaluation input.

**Evidence:** [README](README.md), Levels and Data format; [starter README](starter_agent/README.md), scaling suggestion; [manifest](data/manifest.csv).

### 10. How are the 25 interaction points tested beyond the video?

> Will you run a separate scripted conversation as described in the rubric, and what are its acceptance criteria? Please specify the test device/browser and language, whether selecting a start room or scanning a QR code is acceptable, and what counts for clarification, visible edit confirmation and responsiveness.

**Why:** A web app and creative use case were accepted, and the videos should emphasize interaction. The actual test conditions and rubric remain unspecified. Automatic indoor localization and Wi-Fi were not established as requirements.

**Evidence:** Challenge brief page 3; [lead Q&A](2026-10-24-challenge-lead-qa.md), 08:53-12:23 and 29:07-30:23; [earlier Q&A brief](2026-10-24-weitere-aufnahmen-relevante-infos.md).

### 11. What carries over into the joint final?

> Once the track jury selects its four finalists, do the technical/track scores carry over to the overall result, or is there a separate final rubric? What does that rubric reward, and is the three-minute slot expected to be a live product demo, a pitch, or either?

**Why:** The slot itself is settled: three minutes plus one minute Q&A. The lead was unsure about the general jury's video access. The team's earlier assumption that the final makes technical performance irrelevant was not confirmed.

**Ask:** Overall organizers/final jury, rather than relying solely on a track lead's guess.

**Evidence:** Kickoff slide 32; [lead Q&A](2026-10-24-challenge-lead-qa.md), 30:23-32:12; [brainstorming summary](2026-10-24-brainstorming-zusammenfassung.md).

### 12. Are unseen questions independent or stateful?

> Should every unseen benchmark question start from the original building, as in the shipped evaluator, or can a closure/edit from one question affect later ones? For a hypothetical door, should the change always be temporary unless explicitly committed?

**Why lower priority:** The current evaluator creates a fresh map/agent per question, so independent questions are a supported default. Confirmation matters only if the new Sunday contract introduces sequential tasks. The live app's persistent edits and the benchmark's what-if state should not be accidentally conflated.

**Evidence:** [evaluator](benchmark/evaluate.py), `StarterAgentRunner`; [PLAN.md](PLAN.md), session/version and commit semantics.

## Already answered - do not spend the next discussion re-asking these

- **Deadline and videos:** Kickoff slide 32 specifies Sunday 25 October at **13:00 Europe/Berlin**, a **one-minute demo**, a **one-minute technical video**, architecture notes and any partner submission requirements. The earlier notes calling video lengths unknown predate checking this slide. Delivery details in the live portal can be checked there first.
- **Final slot:** Four finalists per track; three-minute pitch, one-minute Q&A, with one-minute changeover on the kickoff slide.
- **Basic implementation freedom:** A web app is sufficient; different languages/models are allowed; post-training was discouraged. We do not need permission to use the supplied deterministic graph core.
- **Known test data:** 145 published test questions without answers; all answers must be generated by the system. The new input should test generalization, not a wholly unrelated domain. Avoid asking for hidden answers or exact future question texts.
- **Physical obstacles:** Equipment is not an obstacle in the supplied route model, and an item destination is its containing room/bay. Exact endpoint *measurement* remains question 8.
- **Optional features:** Wi-Fi positioning is not expected. AR, camera localization and multiuser features are ideas, not independently established prerequisites.

## Internal follow-ups, not questions for the judges

- `PLAN.md` is a plan, not proof of delivered code or official policy. Its image-import priority, two-model selection and one-wait-per-lift assumption need the confirmations above. The latest plan already records the `.env` cleanup; no judge clarification is needed for that completed repository fix.
- Several implementation claims and files in the plan point to a sibling `../repo`, outside this GitHub checkout. Verify those changes are actually integrated and runnable here before submission. This review did not independently rerun the claimed 369/369 result.
- Keep exact scorer formatting, safe configuration examples, dependency setup, independent benchmark state and a working text fallback as team responsibilities. API/model pricing and the team's credit balance are not judge-rubric questions.

## Review coverage and source limits

Reviewed the repository's challenge README, starter/evaluation code, team plan, route announcement, both PDFs, both stored full transcripts and all supplied meeting summaries/question notes. Prior architecture images are proposals; the newer team plan changes the orchestration details. This review did not fetch additional Discord/portal updates or transcripts absent from the repo.

The data audit read all **280 building JSON files**, the equipment CSV asset-ID inventories, **800 benchmark records** (517 train / 138 dev / 145 test) and **2,130 warm-up records** (1,761 / 369). Equipment CSV and JSON asset-ID sets match in all buildings. Geometry fields, room types, connectors, entrances and parallel openings were inspected in aggregate; this was not a visual inspection of every plan image or a new benchmark/model run.

Relevant PDF sections: [challenge brief](<Hackathon Challenge - Talk to Your Building-1.pdf>), pages 1-3; [kickoff slides](<Industrial Agents Hackathon Kick-Off.pdf>), pages 6, 31 and 32. The decisive scoring/submission pages were also visually checked. Recordings contain uncertain speaker mapping and speech-recognition errors; the route announcement's original author/time/link are not provided. Those limitations are why a written, versioned answer to questions 1-3 would be especially valuable.

After the discussion, record the responder, timestamp, exact confirmed rule and source link next to each resolved question, then update the implementation plan. The priority labels are our assessment, not organizer-assigned weights.

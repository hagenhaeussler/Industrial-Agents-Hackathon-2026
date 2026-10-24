# Challenge lead Q&A — answers and transcript

- **Challenge:** Track 01, “Talk to Your Building” — Industrial Agents Hackathon 2026.
- **Recorded:** 24 October 2026, 15:24:18 Europe/Berlin (13:24:18 UTC).
- **Original meeting title:** “Oct 24, 03:24 PM”.
- **Duration:** approximately 32 minutes 17 seconds according to Fireflies.
- **Source:** [Fireflies recording](https://app.fireflies.ai/view/01M5Q1ASS5PV7GJS1RBV09PC3T).
- **Transcript ID:** 01M5Q1ASS5PV7GJS1RBV09PC3T.
- **Coverage:** all 545 supplied transcript segments, 00:00–32:12, are reproduced below.

## Source and attribution

This recording is the follow-up conversation with the challenge lead identified by the recording owner. Fireflies labels the dialogue as Speaker 1 and Speaker 2 but supplies no verified speaker names. Speaker 2 appears to give the challenge-side answers; Speaker 1 contains the team's questions and may combine several people. No personal name is inferred.

The answers below are paraphrases with recording-relative timestamps. They distinguish what the lead said from editorial interpretation and checks against the local challenge kit. Fireflies returned “Partial results” with two unspecified field errors, and no audio or video URL. The text reaches close to the reported duration, but neither its completeness nor its wording was independently checked against audio. The appendix preserves the supplied wording, including speech-recognition errors, fragments and side conversations.

## Main takeaways

- The lead described the unseen buildings and questions as coming from the same distribution as the supplied data. Generalization matters; manually filling answers or hardcoding the known test set defeats the purpose.
- He framed building changes around local what-if operations, such as adding a door or blocking stairs or a lift. He did not require reconstructing an entire building for each change.
- A website is sufficient. Interesting interaction, usability and responsiveness matter; post-training was explicitly discouraged.
- Submit a runnable system and explain configuration so the judges can run it with their own keys. He confirmed access to OpenAI and Anthropic, not every possible model provider.
- Use the videos primarily to demonstrate interaction and useful product behavior. Briefly explain benchmark performance and architecture.
- Exact runtime limits, video lengths, the internal allocation of functionality points and the final jury's rules were not settled.
- His statement that JSON lacks room layouts conflicts with the supplied schema and starter implementation. Do not turn that statement into a confirmed requirement to rebuild the JSON pipeline around image recognition.

## Answers to the team's questions

### 1. Can we use JSON, SVG or PNG, and what does each contain? — 01:09–03:05

**Answer:** The lead said SVG or PNG can be used, with no stated preference. He mentioned floor heights/elevations in JSON and equipment positions in CSV. When the team suggested reconstructing everything from JSON, he said the PNG would be needed because JSON did not describe room/floor layouts. The team questioned this based on its existing visualization; the exchange ended without resolving the discrepancy.

**Checked against the kit:** At local commit `cb51a6f2e357db743b0c8b2b377fe902ee3ced13`, the README's schema includes room polygons, openings, vertical connectors and assets. `BuildingMap.load` reads `building.json`, and `viewer.py` draws room polygons from that model. This supports the existing JSON-based rendering path for the supplied buildings; it does not prove every detail in each image is duplicated in JSON or specify an unseen raw-plan import task.

### 2. What will unseen buildings and questions look like? — 03:06–05:49

**Answer:** The lead compared train, validation and test splits: different buildings, but the same underlying distribution and kinds of questions. Questions may refer to different rooms and objects; they are not necessarily identical question texts. He described the existing test split as containing multiple buildings.

He described equipment as point locations rather than physical obstacles with dimensions. Equipment does not need to be routed around as solid geometry in this model; passages, doors and closures govern navigation.

**Scope:** The later discussion separately refers to an additional unseen building. The existing multi-building test split and this extra generalization check should not be conflated. “Same distribution” also does not mean every layout or room type is identical.

### 3. Must Build create an entirely new building? What changes matter? — 05:55–08:47

**Answer:** The lead emphasized hypothetical or local changes: what happens if a door is added, an opening changes, stairs become unavailable, or an elevator cannot be used. Only the affected part needs to change; the whole building need not be rebuilt. When the team quoted “create or update a building from floor plans” and “minutes, not days,” he described full creation as one possible use case and again emphasized that individual questions may only require changing aspects of the building.

**Interpretation:** This supports prioritizing local edits and what-if reasoning. It is not a precise minimum acceptance example or an explicit replacement for all written Level 4 criteria. No required plan formats, import accuracy, persistence or multiuser behavior were specified.

### 4. Is model training expected, and is a web app enough? — 08:53–10:06

**Answer:** Correct functioning comes first; the implementation approach and interesting UX also matter. The lead said a website is sufficient and a native Android app is unnecessary. Voice was welcomed as an interaction option, with ElevenLabs credits mentioned. When asked about post-training, he replied, “Forget post training.”

**Scope:** This discourages spending hackathon time on post-training. It does not establish that voice is mandatory or prescribe a particular architecture.

### 5. How will interaction be demonstrated and tested? — 10:07–12:23

**Answer:** The team can show interaction in a video. The lead also said the judges would test the system if it is submitted, using their own API key if necessary. He asked for at least the code, while also acknowledging video demonstration as an alternative if the team does not provide it. He encouraged the team to choose its own creative use case rather than implement one prescribed scenario. He pointed to additional grading information posted in the challenge Discord channel.

**Scope:** Devices, browsers, languages, a fixed scripted conversation, start-position selection and automatic localization were not specified. No new Discord message was retrieved for this note.

### 6. What is the industrial motivation? — 13:42–18:16

**Answer:** The lead named factory-floor applications and understanding CAD geometry. He described questions about nearby parts, changes to assemblies and the consequences of material or geometry changes. He emphasized engineering precision and discussed limitations in CAD data availability and representations that models can reason about.

**Scope:** These are his explanations of the industrial context and research challenges, not additional required deliverables. Claims about the wider model market, companies or developer tooling in this side discussion were not independently verified.

### 7. How will the answers and overall solution be evaluated? — 18:22–20:24

**Answer:** The lead described automated comparison with held-out answers and numerical tolerances. He tentatively mentioned 1% for distance, and said routes must also be correct. Beyond accuracy, he mentioned implementation approach, efficiency/token use, 3D ideas, interaction, UX and latency. Design colleagues would help assess the experience.

**Checked against the kit:** The official scorer at the inspected commit uses answer-type-specific rules, rather than a universal 1% tolerance. The README specifies 1% with at least 1 m for errand distance, 2% for straight-line 3D distance, 5% for areas, and exact counts. It also requires the final `Answer:` line. His informal accuracy estimate is not a guaranteed achievable score.

**Still open:** No exact allocation within the 55 functionality points or minimum finalist score was given.

### 8. Who runs the unseen-building check, and how much time is allowed? — 20:25–24:26

**Answer:** The lead said submitted answer files can be scored automatically. With the code, the judges can also run the system themselves and inspect how quickly it works. The video can demonstrate loading a test building, processing it, asking questions and showing responsiveness.

The extra unseen building is intended to expose overfitting or manually completed answers. He said the judges could run submitted code; if code is not shared, he could send the input to the team for a timed run. He used roughly 200 questions in five minutes as an illustration of making manual answering impractical.

When asked what to submit in the end, he answered “the whole system,” with configuration instructions or an example environment file so the judges can insert their keys.

**Scope:** The five-minute/200-question example was not a confirmed limit. No final release time, code-freeze time, import window, runtime environment, network policy, cost cap or per-question call limit was agreed.

**Written submission contract:** The inspected README says teams run a single command documented in `BENCHMARK.md`, submit outputs, and may be rerun by judges. It requires a CSV with `question_id` and `answer`; the lead's casual “JSON or CSV” comment does not resolve that format discrepancy. Keep the documented CSV and reproducible command unless a later official update changes them.

### 9. Which programming languages and model providers can we use? — 24:24–25:33

**Answer:** The lead said any programming language and any model can be used. When asked about judge-side access, he confirmed OpenAI and Anthropic but said he did not have access to the latest Chinese open-weight models. Rate limits were mentioned as a practical problem. A GUI built with Lovable was also welcomed.

**Scope:** Provider freedom does not guarantee judge-side credentials or capacity for every model. The transcript does not clearly identify another model name mentioned near 25:01, so no provider is inferred from that phrase. Open-source attribution rules were not explicitly discussed.

### 10. Can we see Synera's own demo? — 25:40–26:26

**Answer:** The team asked for a demo video that appeared to be behind a contact form. The lead said he would look internally and share a link if he found one.

**Status:** This is an offer to look, not evidence that a link was subsequently sent.

### 11. What should the product and technical videos emphasize? — 29:07–30:23

**Answer:** The lead explicitly favored interaction. Benchmark performance and how it was achieved can be mentioned briefly; most of the video should show useful, interesting behavior and UI/UX. The team proposed explaining architecture rather than scrolling through code, which he acknowledged.

**Still open:** No exact video duration, file format, mandatory content checklist, or rule for identifying prepared versus live scenes was supplied. The conversation refers to a technical video and a demo video, but does not finalize their packaging.

### 12. Who watches the videos, and what happens in the joint final? — 30:23–32:12

**Answer:** The lead said he, a colleague transcribed as “Dino” (name unverified), and their head of design would watch. He was unsure whether the general jury would also watch. The team relayed an earlier conversation with an organizer about track selection and a broader final jury; the lead suggested there would likely be a live presentation.

**Scope:** The team's account is not a fresh confirmation from the organizer in this recording. The final scoring weights, whether technical scores carry over, and the general jury's exact role remain unresolved. The inspected README separately states four track finalists and a three-minute pitch plus one-minute Q&A.

## Practical implications for our plan

These are editorial recommendations, not new team decisions or promises from the lead:

1. Build a generic, automated building core shared by the app and benchmark. Preserve the documented CSV output and a reproducible one-command run.
2. Prioritize valid routing, numerical/spatial tools and local what-if changes. Treat full raw-plan import as a separate scope question.
3. Keep the working JSON-based data path; resolve the image/JSON discrepancy before investing in a replacement pipeline.
4. Demonstrate a clear user task with visible feedback and responsive interaction. Use the videos to show the product and briefly explain architecture and benchmark evidence.
5. Supply code, dependency/setup instructions and an example configuration without real credentials. Use a provider the judges can run.
6. Confirm the remaining limits and final submission details through the official challenge channel.

## Technical references checked

All links below are pinned to the local challenge-kit commit inspected for this note. They are separate evidence from the recording.

- [README: levels, judging, Sunday benchmark and submission process](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/README.md).
- [Building model loader and geometry operations](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/starter_agent/building_map.py).
- [Viewer drawing room polygons from the building model](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/starter_agent/viewer.py).
- [Official answer scorer](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/benchmark/score.py).

## Full Fireflies transcript

The following is the complete text returned by Fireflies, with only Markdown formatting added. Speaker labels and all supplied timestamps are retained. Apparent transcription mistakes are intentionally left in place; use the interpretation above for the Q&A findings.

**[00:00 - 00:00] Speaker 1:** It.

**[00:28 - 00:28] Speaker 1:** All right.

**[00:28 - 00:39] Speaker 1:** So we just read through the document you gave us and looked at the repo and everything and just kind of like brainstormed what we understand the challenge is.

**[00:39 - 00:41] Speaker 1:** And we'd like to.

**[00:41 - 00:49] Speaker 1:** We have some assumptions or made some assumptions and like, just to validate those that we're on the right track and we're not missing something.

**[00:49 - 00:52] Speaker 1:** And you intended to do it completely differently.

**[00:53 - 01:00] Speaker 1:** So I don't know, it's just gonna be one of us basically like asking questions out there and.

**[01:00 - 01:02] Speaker 2:** Yeah, keep them coming.

**[01:02 - 01:03] Speaker 1:** All right, perfect.

**[01:04 - 01:07] Speaker 1:** So one question was.

**[01:09 - 01:11] Speaker 1:** So we get a JSON file.

**[01:12 - 01:16] Speaker 1:** The building itself is a JSON file, but also there are png.

**[01:17 - 01:22] Speaker 1:** So we saw there PNG files, but also vector graphics in there.

**[01:22 - 01:25] Speaker 1:** And it looks like the vector graphics resemble the.

**[01:25 - 01:27] Speaker 1:** The PNG perfectly.

**[01:27 - 01:32] Speaker 1:** So we were wondering why there even PNG files in there and whether we're.

**[01:33 - 01:35] Speaker 2:** If you want something, you can use anything.

**[01:35 - 01:38] Speaker 2:** If you want to use some high dimension, I mean, you don't.

**[01:38 - 01:38] Speaker 2:** If you are.

**[01:38 - 01:39] Speaker 2:** If you.

**[01:39 - 01:45] Speaker 2:** If you think, for example, using an SVG works better, you can use SVG because SVG is like, there is no compression and so on.

**[01:46 - 01:47] Speaker 2:** So you can use either of them.

**[01:47 - 01:50] Speaker 1:** Okay, so you don't care which one.

**[01:50 - 01:50] Speaker 2:** Okay.

**[01:50 - 01:51] Speaker 1:** And I got the question.

**[01:52 - 01:54] Speaker 1:** The data was in the JSON.

**[01:54 - 02:00] Speaker 1:** Is that all what the PNG and SVG resembles or is there more in the css?

**[02:02 - 02:03] Speaker 2:** Yeah, that is true.

**[02:03 - 02:04] Speaker 2:** It is how it is.

**[02:04 - 02:08] Speaker 2:** For example, it also gives you height and stuff, right?

**[02:10 - 02:12] Speaker 2:** For different levels and stuff.

**[02:12 - 02:12] Speaker 2:** Yes.

**[02:12 - 02:15] Speaker 2:** And the second one is, for example, equipment.

**[02:15 - 02:15] Speaker 2:** CSV.

**[02:15 - 02:16] Speaker 2:** Right.

**[02:16 - 02:17] Speaker 2:** It contains the equipment and its positions.

**[02:17 - 02:18] Speaker 2:** That's not.

**[02:18 - 02:23] Speaker 1:** And yeah, okay, so we don't actually need the SVG and PNGs.

**[02:23 - 02:26] Speaker 1:** We can reconstruct the whole building with JSON.

**[02:27 - 02:27] Speaker 2:** How would you.

**[02:27 - 02:29] Speaker 2:** No, no, you would read the PNG.

**[02:29 - 02:29] Speaker 2:** Right.

**[02:29 - 02:31] Speaker 2:** Because you don't know if you look at the JSON.

**[02:31 - 02:31] Speaker 2:** Right.

**[02:31 - 02:34] Speaker 2:** It just tells you some of the elevation and whatnot.

**[02:34 - 02:34] Speaker 2:** Height or whatnot.

**[02:34 - 02:35] Speaker 2:** Right.

**[02:35 - 02:40] Speaker 2:** It does not tell you anything about the layout of the room or the layout of the floors.

**[02:40 - 02:40] Speaker 2:** Right.

**[02:40 - 02:44] Speaker 2:** You need the layout like where is the room and so on.

**[02:44 - 02:47] Speaker 1:** Did we create a visualization just from the JSON?

**[02:47 - 02:48] Speaker 1:** Did you create it?

**[02:50 - 02:52] Speaker 2:** Like, how do you know which room is next to another?

**[02:53 - 02:54] Speaker 1:** You had the visualization.

**[02:54 - 02:54] Speaker 2:** Sure.

**[02:54 - 02:55] Speaker 2:** Yeah.

**[02:55 - 02:57] Speaker 1:** But maybe it's created with the SVGs.

**[02:58 - 02:59] Speaker 2:** Oh, okay.

**[02:59 - 03:00] Speaker 2:** Ask would be.

**[03:00 - 03:01] Speaker 1:** Ask the.

**[03:01 - 03:02] Speaker 1:** Ask it.

**[03:04 - 03:05] Speaker 1:** Okay, that would be relevant.

**[03:06 - 03:06] Speaker 1:** Okay.

**[03:06 - 03:13] Speaker 1:** No, and then another thing, it also mentioned that we are going to get a new building and that's correct.

**[03:13 - 03:13] Speaker 1:** Right?

**[03:13 - 03:15] Speaker 2:** Yeah, but That's a test one.

**[03:15 - 03:15] Speaker 2:** Yeah.

**[03:16 - 03:19] Speaker 1:** Well, in the final test version we get a new building.

**[03:19 - 03:20] Speaker 1:** We don't know yet.

**[03:21 - 03:24] Speaker 1:** And also there was mention that there is a list of equipment.

**[03:25 - 03:29] Speaker 1:** So is it the same equipment that we used for or.

**[03:30 - 03:32] Speaker 2:** So if you look at the validation set, right.

**[03:32 - 03:33] Speaker 2:** The buildings are different.

**[03:33 - 03:34] Speaker 2:** They are not the same.

**[03:35 - 03:37] Speaker 2:** So you are given like the training center.

**[03:37 - 03:40] Speaker 2:** You have a bunch of buildings and what have you said as equipment, right.

**[03:40 - 03:42] Speaker 2:** And then you have the validation set.

**[03:42 - 03:44] Speaker 2:** It is exactly going to be like that.

**[03:44 - 03:46] Speaker 2:** The validation set has different set of buildings.

**[03:46 - 03:50] Speaker 2:** So whatever your algorithm should work across those buildings.

**[03:50 - 03:53] Speaker 2:** And the test set also has something very similar.

**[03:56 - 03:59] Speaker 1:** Just one building or a couple of buildings.

**[04:00 - 04:04] Speaker 2:** So the test set also has a bunch of buildings, just like the validation set.

**[04:04 - 04:05] Speaker 2:** It's very similar to the validation set.

**[04:05 - 04:07] Speaker 2:** You create a split out of the same data.

**[04:08 - 04:09] Speaker 2:** So it's nothing different.

**[04:10 - 04:11] Speaker 1:** Okay, good.

**[04:11 - 04:12] Speaker 1:** Good to know.

**[04:12 - 04:16] Speaker 1:** And so it also says we get a list of questions.

**[04:16 - 04:17] Speaker 2:** Yeah, it's already given that.

**[04:17 - 04:20] Speaker 1:** Yeah, it's going to be the same questions, just that we don't know the answer.

**[04:20 - 04:23] Speaker 2:** Not the same question, but the same distribution of questions.

**[04:23 - 04:24] Speaker 2:** You see what I'm saying?

**[04:24 - 04:25] Speaker 2:** What do you mean by that?

**[04:25 - 04:26] Speaker 2:** It comes from the same distribution.

**[04:26 - 04:28] Speaker 2:** Like there's nothing out of distribution data.

**[04:28 - 04:33] Speaker 2:** So what I mean by that is the same type of questions, not the same question, the same kind of questions.

**[04:33 - 04:33] Speaker 1:** Of course.

**[04:33 - 04:37] Speaker 1:** Okay, so conceptually the same, but they might refer to different objects.

**[04:37 - 04:38] Speaker 2:** Yeah, exactly.

**[04:38 - 04:39] Speaker 2:** All the rooms are different.

**[04:39 - 04:39] Speaker 2:** Right.

**[04:39 - 04:41] Speaker 2:** But for example, you will have questions, errand questions.

**[04:41 - 04:45] Speaker 2:** You will have what is the volume of the OI surface area of them.

**[04:45 - 04:45] Speaker 2:** So on.

**[04:46 - 04:46] Speaker 1:** Oh, I see.

**[04:47 - 04:48] Speaker 1:** Okay.

**[04:48 - 04:52] Speaker 1:** And the building we presume isn't going to be like totally different.

**[04:52 - 04:57] Speaker 1:** Like so now we have a space station or something and there are no other factors.

**[04:57 - 04:57] Speaker 2:** Okay, got it.

**[04:57 - 04:58] Speaker 2:** Unrealistic.

**[04:58 - 04:59] Speaker 1:** Yeah.

**[04:59 - 05:03] Speaker 1:** Okay, so most of the features that is in the training side are kind of like resembled.

**[05:03 - 05:03] Speaker 2:** Yeah.

**[05:03 - 05:06] Speaker 2:** And the second thing is that we also don't like equipment.

**[05:06 - 05:06] Speaker 2:** Right.

**[05:06 - 05:07] Speaker 2:** If you see the equipment, it's.

**[05:08 - 05:10] Speaker 2:** It doesn't necessarily occupy any space.

**[05:10 - 05:11] Speaker 2:** Like we are modeled as point spaces.

**[05:11 - 05:14] Speaker 2:** So it doesn't really matter the dimensions of the equipment.

**[05:14 - 05:15] Speaker 2:** They don't.

**[05:15 - 05:19] Speaker 2:** I mean they, first of all they don't block anything.

**[05:19 - 05:21] Speaker 2:** Like most of the navigation is to passages and so on.

**[05:21 - 05:22] Speaker 2:** So it's not like you have to go around.

**[05:22 - 05:27] Speaker 2:** I mean I just posted the channel, I also posted some how it is graded.

**[05:27 - 05:30] Speaker 2:** You can check that Cinera Challenge one.

**[05:31 - 05:35] Speaker 2:** So that also give you some hints as to how we model stuff.

**[05:35 - 05:41] Speaker 2:** But the equipment in principle is there, for example, kind of.

**[05:43 - 05:45] Speaker 2:** They're not treated as obstacles, essentially.

**[05:45 - 05:49] Speaker 2:** Okay, the door obviously is an obstacle.

**[05:49 - 05:50] Speaker 2:** There are some closed things.

**[05:52 - 05:53] Speaker 1:** Okay.

**[05:53 - 05:55] Speaker 1:** And guys, feel free to hop in.

**[05:55 - 06:03] Speaker 1:** But another question for the building versus the root and finding new objects and stuff.

**[06:03 - 06:05] Speaker 1:** If we, so we, we thought about this.

**[06:05 - 06:11] Speaker 1:** Okay, if we get a new floor plan, then this sounds like something you wouldn't do on a regular basis.

**[06:11 - 06:16] Speaker 1:** Like, oh, now I'm in this building and I have this new floor plan on my phone and drop it in there.

**[06:16 - 06:18] Speaker 1:** So our idea was to separate this.

**[06:18 - 06:23] Speaker 1:** So we have like a phone version where, okay, I'm in a building, the building isn't going to change like dramatically.

**[06:23 - 06:25] Speaker 2:** While I'm walking through it.

**[06:25 - 06:35] Speaker 1:** So I have a phone optimized version, web version maybe where I walk through and then another version where I give maybe a new floor plan.

**[06:36 - 06:42] Speaker 1:** But then also in the test agent, it said that one of the tools is to add a door, which is an example.

**[06:43 - 06:46] Speaker 1:** And add a door sounds more like a small change.

**[06:46 - 06:48] Speaker 2:** No, no, it's not about add a door.

**[06:48 - 06:52] Speaker 2:** It's like if a door was added, then what would happen?

**[06:52 - 06:57] Speaker 1:** Okay, so this is not for someone who walks through the building and changes the thing, life.

**[06:57 - 07:01] Speaker 1:** It's more about, okay, we get a new building and okay, use it.

**[07:01 - 07:01] Speaker 2:** Yeah.

**[07:01 - 07:03] Speaker 2:** Or maybe you want to like plan it.

**[07:03 - 07:03] Speaker 2:** Right?

**[07:03 - 07:04] Speaker 2:** Not a new building.

**[07:04 - 07:09] Speaker 2:** But let's say you want to say, okay, this door sucks, I want to make this as a door or something, something like that.

**[07:10 - 07:10] Speaker 1:** Okay.

**[07:10 - 07:11] Speaker 1:** Okay.

**[07:11 - 07:16] Speaker 1:** So one version would be to generate a new building and one would be to update the building.

**[07:16 - 07:20] Speaker 2:** No, you don't have to generate necessarily if you want, you can't generate a new building.

**[07:20 - 07:24] Speaker 1:** But I mean, it kind of hinted at that in the description you do may not.

**[07:24 - 07:24] Speaker 2:** Right.

**[07:24 - 07:26] Speaker 2:** For example, depends on where you change it.

**[07:26 - 07:26] Speaker 2:** Right.

**[07:26 - 07:30] Speaker 2:** Let's say if I want to change the door, so why would I have to change something on the top of this floor?

**[07:30 - 07:32] Speaker 2:** Like only this floor matters, right?

**[07:32 - 07:34] Speaker 2:** So in some sense I don't have to change the building.

**[07:34 - 07:37] Speaker 2:** I have to change this part of one room.

**[07:38 - 07:42] Speaker 2:** So let's say it depends on the kind of question you have, right?

**[07:42 - 07:44] Speaker 2:** So you may have to change them.

**[07:44 - 07:48] Speaker 2:** I mean, I don't know why you would want to change the entire building because the layout is not changed.

**[07:48 - 07:48] Speaker 2:** Right?

**[07:48 - 07:52] Speaker 2:** But what is changing is like where the opening and the closing, they are changing.

**[07:52 - 07:55] Speaker 2:** Or maybe you guys say that, okay, you cannot use the stairs.

**[07:55 - 07:56] Speaker 2:** Right?

**[07:56 - 07:57] Speaker 2:** So stairs are blocked now.

**[07:57 - 07:58] Speaker 2:** Right.

**[07:58 - 07:59] Speaker 2:** So then what do you do?

**[08:00 - 08:06] Speaker 2:** So it's not changing anything, but you just can't use the stairs for some reason or you can't use elevator because of fire instead of working.

**[08:06 - 08:06] Speaker 2:** Right.

**[08:06 - 08:09] Speaker 2:** You're not changing the building, but there's something is changing.

**[08:09 - 08:10] Speaker 2:** So.

**[08:10 - 08:10] Speaker 2:** Yeah.

**[08:11 - 08:12] Speaker 1:** Okay, got it.

**[08:12 - 08:21] Speaker 1:** Interesting, because just like to read from the instruction, it said create or update building from floor plan by conversation.

**[08:21 - 08:23] Speaker 1:** A new building should take minutes, not days.

**[08:24 - 08:24] Speaker 1:** So.

**[08:26 - 08:28] Speaker 2:** This is just, for example, one of the use cases.

**[08:28 - 08:32] Speaker 2:** You don't have to like, for example, this is like, these are the questions where.

**[08:33 - 08:35] Speaker 2:** For example, it depends on the kind of question.

**[08:35 - 08:36] Speaker 2:** I don't think you have to kind of.

**[08:36 - 08:43] Speaker 2:** Let's say if I ask questions like you want to change some aspects of the building as well, but you don't have to kind of reconstruct the entire building.

**[08:44 - 08:44] Speaker 1:** Okay, interesting.

**[08:44 - 08:45] Speaker 2:** Okay.

**[08:45 - 08:47] Speaker 1:** Probably it's going to be more clear when we read through the questions.

**[08:47 - 08:47] Speaker 2:** Yeah, thanks.

**[08:47 - 08:48] Speaker 2:** A question.

**[08:48 - 08:49] Speaker 1:** Okay, got it.

**[08:49 - 08:52] Speaker 1:** And then maybe a side question.

**[08:53 - 08:54] Speaker 1:** Do you put any.

**[08:55 - 09:00] Speaker 1:** So is most emphasis put on whether it works or not or also how it works?

**[09:00 - 09:02] Speaker 1:** Because I was just like thinking actually,.

**[09:03 - 09:05] Speaker 2:** Yeah, whether it works is like the first step.

**[09:05 - 09:07] Speaker 2:** The second is how it works is also interesting.

**[09:07 - 09:10] Speaker 2:** And if you do something interesting, ux, that's a plus.

**[09:10 - 09:17] Speaker 2:** I mean that's also important if you're doing interactivity or whatever because you have credits from 11 labs and maybe you can just talk to it or so on.

**[09:17 - 09:17] Speaker 2:** Right?

**[09:17 - 09:21] Speaker 2:** Yeah, we don't have to make an Android app or any such thing go crazy.

**[09:21 - 09:23] Speaker 2:** But like even the website would kind of do it.

**[09:23 - 09:32] Speaker 1:** I was more thinking about the back end, whether to use like one of the, for example, a cloud model to say, okay, we do some prompt engineering and change the prompt.

**[09:32 - 09:38] Speaker 1:** Or whether we say, okay, you put special emphasis on, I don't know, post training.

**[09:38 - 09:40] Speaker 1:** A model on this kind of data.

**[09:40 - 09:41] Speaker 2:** Forget post training.

**[09:41 - 09:41] Speaker 1:** Okay.

**[09:42 - 09:47] Speaker 1:** No, I don't know if you say, okay, yeah, sure, we do this all the time at Cinera.

**[09:48 - 09:51] Speaker 1:** It would be nice if you do a little bit of content.

**[09:51 - 09:53] Speaker 2:** I don't know, resources we will give for post training.

**[09:53 - 09:54] Speaker 2:** Right.

**[09:54 - 09:55] Speaker 1:** Okay.

**[09:55 - 09:56] Speaker 1:** All right, cool.

**[09:56 - 09:56] Speaker 1:** Okay.

**[09:56 - 10:02] Speaker 1:** And the main input source, should it be converted like the voice agent or should it be.

**[10:02 - 10:03] Speaker 2:** It could be.

**[10:03 - 10:03] Speaker 2:** If you're given.

**[10:03 - 10:06] Speaker 2:** If you have place you can use that app would be nice, I think.

**[10:07 - 10:12] Speaker 1:** And then if you look at the distribution of points, it's like 55 points for if the.

**[10:12 - 10:13] Speaker 1:** Just the questions.

**[10:13 - 10:17] Speaker 1:** So I presume we just get that as a question file and then we submit our answer file.

**[10:18 - 10:20] Speaker 1:** But then it also mentions interaction.

**[10:20 - 10:21] Speaker 2:** Yeah.

**[10:21 - 10:23] Speaker 1:** So is it as we understood it?

**[10:23 - 10:33] Speaker 1:** It's probably that you kind of have a separate part where you interact with it via voice, but that's not necessarily connected to those questions that are going to be asked.

**[10:33 - 10:34] Speaker 1:** So.

**[10:34 - 10:35] Speaker 1:** Okay.

**[10:35 - 10:36] Speaker 1:** And how do you.

**[10:36 - 10:37] Speaker 2:** Or you can have a video also?

**[10:37 - 10:39] Speaker 2:** There's a video thing where you interact with it and show it.

**[10:40 - 10:40] Speaker 1:** So you're not.

**[10:40 - 10:41] Speaker 1:** Have to.

**[10:41 - 10:45] Speaker 1:** You don't have to use it yourself as the jury.

**[10:45 - 10:46] Speaker 2:** No, we will use it.

**[10:46 - 10:48] Speaker 2:** I mean, in the sense that we will test it also.

**[10:48 - 10:49] Speaker 2:** I mean, if you submit it to us.

**[10:49 - 10:49] Speaker 2:** Right.

**[10:50 - 10:53] Speaker 2:** If you don't want to give us a key, we will use our own key and we will test it.

**[10:54 - 10:54] Speaker 1:** Okay.

**[10:54 - 10:55] Speaker 1:** Okay.

**[10:55 - 10:56] Speaker 1:** Okay, cool.

**[10:56 - 10:59] Speaker 1:** We have to make it available to you as.

**[11:00 - 11:01] Speaker 2:** Yeah, at least the code.

**[11:01 - 11:03] Speaker 2:** I would say if you can give us the code, that would be nice.

**[11:04 - 11:04] Speaker 1:** Okay.

**[11:04 - 11:06] Speaker 1:** Okay, great.

**[11:08 - 11:10] Speaker 2:** I mean, if you don't know, that's also fine.

**[11:10 - 11:11] Speaker 2:** But then you can show us in the video.

**[11:12 - 11:13] Speaker 2:** Okay.

**[11:13 - 11:13] Speaker 1:** Okay.

**[11:14 - 11:20] Speaker 1:** And in terms of interaction, there is not like a certain kind of way you'd like to interact with it.

**[11:20 - 11:24] Speaker 1:** Like for the other part we have like preset questions.

**[11:24 - 11:26] Speaker 1:** So it's pretty clear about that.

**[11:26 - 11:32] Speaker 1:** But for the interaction it seems more like, okay, we come up with a use case and yeah, sure, you can.

**[11:32 - 11:33] Speaker 2:** Go be as creative as you want.

**[11:33 - 11:34] Speaker 2:** You can.

**[11:34 - 11:35] Speaker 2:** Okay, yeah.

**[11:35 - 11:35] Speaker 1:** Okay, cool.

**[11:35 - 11:39] Speaker 1:** But I mean, just like to make sure that we don't develop something.

**[11:39 - 11:41] Speaker 1:** And you say, okay, but I had this specific use case.

**[11:43 - 11:43] Speaker 1:** Now I kind.

**[11:44 - 11:44] Speaker 2:** You can go crazy.

**[11:44 - 11:46] Speaker 2:** Let's say I want to commit suicide from this.

**[11:46 - 11:47] Speaker 2:** Which window should I jump from?

**[11:49 - 11:52] Speaker 2:** Yeah, I would be crazy, but yeah.

**[11:52 - 11:53] Speaker 1:** Okay.

**[11:54 - 11:55] Speaker 1:** All right.

**[11:55 - 11:56] Speaker 1:** Why is it doing this?

**[11:58 - 12:01] Speaker 1:** Okay, guys, feel free.

**[12:14 - 12:16] Speaker 1:** Just reading through the question one more.

**[12:16 - 12:18] Speaker 2:** Time if you can.

**[12:18 - 12:19] Speaker 2:** If you check the.

**[12:20 - 12:21] Speaker 2:** If you check the discord one.

**[12:21 - 12:21] Speaker 2:** Right.

**[12:22 - 12:23] Speaker 2:** So added some stuff there.

**[12:58 - 12:59] Speaker 1:** Unless he's a jedi.

**[12:59 - 13:00] Speaker 2:** Okay, it.

**[13:42 - 13:48] Speaker 1:** So what's the typical industrial case where this like tool would be used?

**[13:50 - 13:55] Speaker 1:** What's a typical case in industry where this tool would be used?

**[13:56 - 14:03] Speaker 2:** Yeah, so the thing is that for us, for scenario, so there are two applications.

**[14:03 - 14:09] Speaker 2:** One is probably the factory floor thing, which we are thinking of creating something on that.

**[14:09 - 14:13] Speaker 2:** And the second one is CAD geometry understanding.

**[14:13 - 14:23] Speaker 2:** So this is like we didn't want to give like a full fledged CAD challenge because that's super technical and you require like mechanical engineering expertise.

**[14:23 - 14:23] Speaker 2:** Right.

**[14:23 - 14:30] Speaker 2:** So part of the spatial reasoning can also be applied to CAD understanding.

**[14:30 - 14:31] Speaker 2:** So imagine, right.

**[14:31 - 14:35] Speaker 2:** There's a very complex, I don't know, part auto part.

**[14:35 - 14:35] Speaker 2:** Right.

**[14:36 - 14:45] Speaker 2:** This frame of a car and you want to optimize the materials and stuff.

**[14:45 - 14:49] Speaker 2:** You want to understand, for example, that if I change, for example, the beads.

**[14:49 - 14:54] Speaker 2:** So there are these beads inside this car thing, car frames which support the car.

**[14:54 - 14:58] Speaker 2:** If I change it here to kind of reduce the cost, how it would look like.

**[14:58 - 15:00] Speaker 2:** Ask questions about the CAD geometry.

**[15:00 - 15:01] Speaker 2:** What is the.

**[15:02 - 15:03] Speaker 2:** Or maybe you have more.

**[15:04 - 15:06] Speaker 2:** More complex, like ship building and stuff.

**[15:06 - 15:11] Speaker 2:** And what is the closest complex CAD assembly, What is the closest part to this part and so on.

**[15:11 - 15:12] Speaker 2:** Right.

**[15:12 - 15:13] Speaker 2:** So this kind of questions.

**[15:13 - 15:25] Speaker 2:** And the thing is that currently like there is like you have multimodal LLMs, they only accept images and maybe videos, but there is no way to accept B REP files.

**[15:25 - 15:30] Speaker 2:** B rep is a boundary representation file which kind of gives you all of those.

**[15:30 - 15:32] Speaker 2:** The boundary of the entire cat thing.

**[15:32 - 15:39] Speaker 2:** And there's no LLM which understands it at the moment, or at least not as good as.

**[15:40 - 15:46] Speaker 2:** So the thing is that we want to kind of learn from this and maybe apply it to this kind of problems.

**[15:46 - 15:47] Speaker 2:** That's another use case.

**[15:48 - 15:55] Speaker 2:** This is like the, like all LLMs are very good at text, for example, and engineering 3D CAD.

**[15:55 - 16:00] Speaker 2:** And the thing is, it's not simply some asset you see on a video game 3D CAD, right, because it's CAD stuff.

**[16:01 - 16:09] Speaker 2:** Like you have to be super Precise because like 1 millimeters of gap and then this table or screw doesn't fit and all of your manufacturing is useless.

**[16:09 - 16:10] Speaker 2:** Right.

**[16:10 - 16:11] Speaker 2:** It has to be highly precise.

**[16:11 - 16:12] Speaker 2:** And this is what for consumer.

**[16:12 - 16:16] Speaker 2:** It is like what to speak of like all of this crazy rocket engineering and whatnot, right?

**[16:17 - 16:18] Speaker 2:** To be super precise.

**[16:18 - 16:22] Speaker 2:** So that is an additional challenge.

**[16:22 - 16:26] Speaker 1:** And do you think you're going to get there in the next couple of years?

**[16:26 - 16:27] Speaker 2:** Eventually, yes.

**[16:27 - 16:27] Speaker 2:** Okay.

**[16:27 - 16:29] Speaker 2:** People are pouring a lot of money on this problem.

**[16:29 - 16:31] Speaker 1:** Yeah, I know, it's fine.

**[16:31 - 16:31] Speaker 2:** Eventually, of course.

**[16:31 - 16:32] Speaker 2:** Yeah, I think so.

**[16:33 - 16:40] Speaker 2:** The only problem is like if a software engineer, right, with all of those GitHub repos, you could just comb through them and train your model.

**[16:40 - 16:42] Speaker 2:** This data is not enough.

**[16:42 - 16:46] Speaker 2:** I mean, many of the CAD data sets, that artificial generator are proprietary and so on.

**[16:46 - 16:46] Speaker 2:** Right.

**[16:46 - 16:50] Speaker 2:** So yeah, so it will take some time, but it will happen.

**[16:50 - 16:59] Speaker 2:** I think with this Jeff Bezos start a Prometheus AI, they are hiring people from India to just kind of engineers from India just to create drawings for AI to training.

**[17:00 - 17:01] Speaker 1:** Interesting.

**[17:01 - 17:06] Speaker 1:** Okay, so you'd say it's more of a data problem than models.

**[17:06 - 17:26] Speaker 2:** There is a data problem and also a bit of model problem also because like you have to figure out a way to represent 3D geometry in a way which LLM transformer or some variation of that understands Right now they break down the image into this patches.

**[17:26 - 17:26] Speaker 2:** Right.

**[17:26 - 17:28] Speaker 2:** And send it to the transformer.

**[17:29 - 17:29] Speaker 2:** I don't know.

**[17:29 - 17:30] Speaker 2:** You can.

**[17:30 - 17:31] Speaker 2:** So yeah, okay.

**[17:31 - 17:35] Speaker 2:** You can take a 3D object, slices into different things, cross sections with them.

**[17:35 - 17:36] Speaker 2:** You can do that.

**[17:36 - 17:38] Speaker 2:** But there must be a better way to do this.

**[17:39 - 17:40] Speaker 2:** I think so, yeah.

**[17:40 - 17:45] Speaker 1:** What about the primitives that you just take the entire object and say like, okay, this.

**[17:45 - 17:46] Speaker 2:** Yeah, that doesn't work.

**[17:46 - 17:47] Speaker 1:** Okay.

**[17:47 - 17:48] Speaker 1:** It can't reason out.

**[17:48 - 17:49] Speaker 1:** Interesting.

**[17:50 - 17:53] Speaker 2:** Because the people are just doing feature engineering on these files.

**[17:53 - 17:56] Speaker 2:** Either images or some other metadata or some such thing.

**[17:56 - 17:58] Speaker 2:** You extract and try something.

**[18:00 - 18:04] Speaker 2:** There's some embedding based approaches also, but also not like.

**[18:04 - 18:05] Speaker 2:** It's not like a text embedding.

**[18:05 - 18:06] Speaker 2:** It doesn't work like that.

**[18:07 - 18:08] Speaker 2:** They don't generalize to everything.

**[18:09 - 18:13] Speaker 1:** Is Nvidia providing anything for developers in this regard?

**[18:13 - 18:15] Speaker 2:** No, no, no.

**[18:15 - 18:16] Speaker 2:** It would be nice if they did.

**[18:19 - 18:19] Speaker 1:** Interesting.

**[18:22 - 18:26] Speaker 1:** Okay, just going back to the challenge for a second.

**[18:28 - 18:37] Speaker 1:** So in, in terms of who judges what we do, I mean there's of course this, this part which is kind of clear where there's a score based on how good your question is.

**[18:37 - 18:39] Speaker 1:** Yeah, first, yeah, for that I had a question.

**[18:39 - 18:41] Speaker 1:** How is that going to be evaluated?

**[18:41 - 18:45] Speaker 1:** Do you have like a large language model that basically looks at the question and answers it?

**[18:45 - 18:53] Speaker 2:** Okay, yeah, so we have some held out answers and then we just evaluate like this with the meters, distance is numbers, there is a tolerance, so we'll see the tolerance.

**[18:53 - 18:59] Speaker 2:** Also how much tolerance we have for distance in meters and so on meter square or meter cube, whatever.

**[18:59 - 19:00] Speaker 1:** Oh, okay.

**[19:00 - 19:06] Speaker 2:** So based on that, and we also mentioned distance, it has to be 1% I think is a tolerance.

**[19:07 - 19:10] Speaker 2:** Distance and root also has to be correct.

**[19:10 - 19:13] Speaker 2:** Okay, so yeah, that.

**[19:13 - 19:15] Speaker 2:** And that would be automated stuff.

**[19:15 - 19:23] Speaker 2:** And then after that we have some design people who will also look at for example the UX interactivity, for example.

**[19:23 - 19:28] Speaker 1:** And yeah, okay, so there's not going to be like a qualitative question.

**[19:28 - 19:35] Speaker 1:** Like, okay, I don't know, like, like something where you don't have just like a number as output.

**[19:35 - 19:39] Speaker 2:** There will be, there will be a number as output that is like part of the evaluation.

**[19:39 - 19:50] Speaker 2:** Like, okay, if you have solved like, I think it's not so difficult in my view to, to get like hundred ninety percent plus accuracy thing.

**[19:50 - 19:55] Speaker 2:** There's also, for example, how do you go about it essentially?

**[19:55 - 19:59] Speaker 2:** Like how do you generate 3D stuff?

**[19:59 - 20:00] Speaker 2:** Any other ideas you had?

**[20:00 - 20:02] Speaker 2:** Some interesting.

**[20:02 - 20:04] Speaker 2:** Let's say how many tokens are used or something.

**[20:04 - 20:07] Speaker 2:** Or how efficient is the problem?

**[20:07 - 20:12] Speaker 2:** Maybe how efficient is the solution you propose, for example, and what sort of interactivity.

**[20:12 - 20:14] Speaker 2:** There's some UX thing also.

**[20:14 - 20:15] Speaker 1:** Interesting.

**[20:15 - 20:17] Speaker 1:** So okay, that as well.

**[20:17 - 20:19] Speaker 1:** And I guess latency as well, maybe.

**[20:19 - 20:20] Speaker 2:** Yeah, yeah.

**[20:20 - 20:21] Speaker 2:** That's part of UX, right?

**[20:21 - 20:22] Speaker 2:** Interactivity, right?

**[20:22 - 20:23] Speaker 2:** Yeah, yeah.

**[20:23 - 20:24] Speaker 2:** If it takes like 10 minutes to.

**[20:25 - 20:29] Speaker 1:** No, I mean, but for interactivity it makes sense, of course to have low latency.

**[20:29 - 20:33] Speaker 1:** But then also we get those questions and that was another question I had.

**[20:33 - 20:38] Speaker 1:** When we get the new building and the questions and we have to.

**[20:38 - 20:42] Speaker 1:** Or submit and upload our answer, how do you.

**[20:43 - 20:44] Speaker 1:** How much time do we have for that?

**[20:44 - 20:45] Speaker 1:** Do we have to disclose?

**[20:45 - 20:46] Speaker 2:** No, no.

**[20:46 - 20:50] Speaker 2:** So one is like if you want the automated evaluation, you can just send the answers and I'll run it.

**[20:52 - 20:53] Speaker 2:** That's one.

**[20:53 - 21:02] Speaker 2:** And second thing is if you submit a code, then we can also check, for example, or maybe in the video you can also share, for example, interactivity, how much time it takes.

**[21:02 - 21:04] Speaker 2:** For example, there, right?

**[21:04 - 21:06] Speaker 2:** You can take one of the test cases, right?

**[21:06 - 21:07] Speaker 2:** It has all of that.

**[21:07 - 21:23] Speaker 2:** You just put that as input and then you ask a question and maybe it will take some time to kind of process it and then you ask questions and then you can show, for example, how quick it is and what kind of cool questions you can ask.

**[21:23 - 21:24] Speaker 2:** These are the questions you definitely answers.

**[21:25 - 21:27] Speaker 2:** But maybe you can ask something else also.

**[21:27 - 21:30] Speaker 2:** You can just show off the usability of your.

**[21:31 - 21:31] Speaker 1:** Of course, of course.

**[21:33 - 21:35] Speaker 1:** For the interaction part, that makes total sense.

**[21:35 - 21:37] Speaker 1:** Just for the other part where you.

**[21:37 - 21:40] Speaker 2:** Just have to send the answer, the answer is JSON or CSV or whatever.

**[21:40 - 21:40] Speaker 2:** Both work.

**[21:40 - 21:42] Speaker 2:** So you are given the questions.

**[21:42 - 21:46] Speaker 2:** Yeah, but if you look at your data, right, you have like bunch of directories.

**[21:46 - 21:53] Speaker 2:** Inside each directory there is a JSON L file and JSON L file has like, I don't know, 10, 20 questions or something.

**[21:54 - 21:55] Speaker 1:** When will we get.

**[21:55 - 21:56] Speaker 2:** You already have it.

**[21:56 - 21:57] Speaker 2:** Should already have it.

**[21:57 - 21:58] Speaker 1:** The questions we already have.

**[21:58 - 21:59] Speaker 2:** The last building.

**[22:00 - 22:03] Speaker 2:** The last building is like we would do it.

**[22:03 - 22:10] Speaker 2:** Because the thing is, what we are slightly concerned about is in principle what you can do is like you can look at the test data, right?

**[22:10 - 22:12] Speaker 2:** And you can manually filter.

**[22:12 - 22:14] Speaker 1:** Yeah, manually fill that.

**[22:14 - 22:15] Speaker 2:** Right.

**[22:15 - 22:16] Speaker 2:** So then that's.

**[22:16 - 22:19] Speaker 2:** That that doesn't solve the purpose of the, of the hackathon.

**[22:19 - 22:19] Speaker 2:** Right.

**[22:19 - 22:27] Speaker 2:** So then that's why if we will get some building which nobody has seen, and then we'll try it out on that and see how it works.

**[22:27 - 22:28] Speaker 2:** But factory building or something.

**[22:28 - 22:29] Speaker 1:** But we won't see.

**[22:29 - 22:30] Speaker 2:** No, no, no.

**[22:30 - 22:30] Speaker 2:** Okay.

**[22:30 - 22:32] Speaker 2:** Before that Otherwise like you just can just kind of.

**[22:33 - 22:35] Speaker 1:** Because I understood it like this reading.

**[22:36 - 22:37] Speaker 2:** So this, this is something.

**[22:37 - 22:40] Speaker 2:** Yeah, yeah, Maybe we should have clarified it.

**[22:40 - 22:48] Speaker 2:** The thing is, the only thing is that if you super overfit on that test set and only works for that test set answer is 100%.

**[22:48 - 22:51] Speaker 2:** But then you give a slightly different building and just completely fails.

**[22:51 - 22:51] Speaker 2:** Right.

**[22:52 - 22:54] Speaker 1:** Okay, thanks.

**[22:57 - 22:58] Speaker 1:** That makes sense.

**[22:58 - 23:03] Speaker 1:** But if I guess like at 1pm or something, we get this new building.

**[23:04 - 23:08] Speaker 1:** Are we supposed to run the test with our system on that new building or are you guys.

**[23:08 - 23:11] Speaker 2:** Yeah, so if you give us the code, we will run it.

**[23:11 - 23:15] Speaker 2:** If you don't give us the code, then I'll send you the thing either way.

**[23:15 - 23:17] Speaker 1:** But just for example, just making sure.

**[23:18 - 23:24] Speaker 1:** If you send us the building and we just say, oh nice, let's manually answer it manually.

**[23:24 - 23:28] Speaker 2:** You have to do it in particular amount of time and manually.

**[23:28 - 23:31] Speaker 2:** If I give like 200 questions, 5 minutes is not possible.

**[23:31 - 23:32] Speaker 2:** Right.

**[23:32 - 23:32] Speaker 1:** Okay.

**[23:33 - 23:36] Speaker 2:** Unless I don't know if you have some other crazy time machine.

**[23:36 - 23:40] Speaker 1:** Yeah, we have like 100 friends or something like that.

**[23:41 - 23:46] Speaker 2:** And maybe if you have 100 friends who are willing to work like this, maybe you shouldn't deserve the price.

**[23:48 - 23:51] Speaker 2:** Guy who can recruit 100 people at like a moment's notice and.

**[23:54 - 24:00] Speaker 1:** Okay, so it's probably going to be more like we sent you the code and you run the.

**[24:00 - 24:03] Speaker 2:** If you don't want to share the code, I can also send the stuff to it.

**[24:03 - 24:04] Speaker 2:** Okay.

**[24:04 - 24:05] Speaker 1:** Proprietary code.

**[24:07 - 24:08] Speaker 1:** No, no.

**[24:08 - 24:11] Speaker 1:** I mean just what do you expect from us in the end?

**[24:11 - 24:14] Speaker 1:** Is it just going to be a file or is it going to be the whole system and.

**[24:14 - 24:15] Speaker 2:** Yeah, the whole system.

**[24:15 - 24:22] Speaker 2:** And maybe if you can also just tell us which like.nexample file and we will just put in our keys.

**[24:24 - 24:24] Speaker 2:** Sure.

**[24:24 - 24:26] Speaker 2:** And you can use any language you want.

**[24:27 - 24:28] Speaker 1:** Sure.

**[24:29 - 24:31] Speaker 2:** The language of intelligent English.

**[24:31 - 24:32] Speaker 2:** English is obvious.

**[24:34 - 24:36] Speaker 1:** And what about the model?

**[24:36 - 24:37] Speaker 2:** Should we.

**[24:37 - 24:38] Speaker 2:** Any model you want.

**[24:38 - 24:38] Speaker 1:** Any.

**[24:38 - 24:40] Speaker 1:** Okay, so you have access to any model?

**[24:41 - 24:43] Speaker 2:** Well, that's a good question.

**[24:44 - 24:54] Speaker 2:** Yeah, we have access to OpenAI and anthropic, but I don't have access to the latest open weight models from Chinese companies.

**[24:54 - 24:57] Speaker 1:** Like we're going to use one of those two anyway.

**[24:57 - 24:58] Speaker 2:** Probably.

**[24:58 - 24:59] Speaker 1:** We're going to figure it out.

**[25:00 - 25:01] Speaker 1:** Okay.

**[25:01 - 25:06] Speaker 2:** The Astra is possibility, but the problem is like if you get rate limited, then that's a problem.

**[25:07 - 25:07] Speaker 1:** Yes.

**[25:13 - 25:27] Speaker 1:** Okay, So the input through voice is just for the UX experience.

**[25:29 - 25:33] Speaker 2:** And if you want to use Lovable to create some nice gui, that's also.

**[25:34 - 25:35] Speaker 2:** Can you do that?

**[25:35 - 25:36] Speaker 1:** You have time, right?

**[25:36 - 25:36] Speaker 2:** Now?

**[25:36 - 25:36] Speaker 2:** Yeah, sure.

**[25:40 - 25:43] Speaker 1:** So we would like to know a.

**[25:43 - 25:45] Speaker 2:** Bit more about your platform.

**[25:45 - 25:53] Speaker 1:** And there's this seven minute demo, but I can't like, I could only get it through the contact form.

**[25:53 - 25:54] Speaker 1:** Can you give me the demo video?

**[25:55 - 25:58] Speaker 2:** No, actually I also will have to use the contact form.

**[25:58 - 25:59] Speaker 1:** Okay, fair.

**[26:00 - 26:02] Speaker 2:** There's no getting around the contact form, I guess.

**[26:02 - 26:02] Speaker 1:** Okay.

**[26:02 - 26:05] Speaker 1:** But they're probably not going to accept it until tomorrow.

**[26:05 - 26:05] Speaker 1:** 13.

**[26:07 - 26:09] Speaker 2:** Okay, but why would you need the.

**[26:09 - 26:16] Speaker 2:** Just to work like see if videos are posted on Vimeo.

**[26:17 - 26:18] Speaker 2:** Let me ask.

**[26:21 - 26:25] Speaker 2:** Okay, let me search my internal systems and I find a link, I'll share it with you.

**[26:25 - 26:26] Speaker 1:** Okay, sure.

**[26:26 - 26:26] Speaker 2:** Yeah.

**[26:32 - 26:33] Speaker 2:** Yes.

**[26:33 - 26:34] Speaker 2:** Any other questions?

**[26:34 - 26:38] Speaker 1:** Just reading one more time through them, but otherwise I think.

**[28:21 - 28:37] Speaker 1:** That's.

**[28:53 - 28:54] Speaker 2:** All right.

**[28:58 - 29:03] Speaker 1:** Okay guys, as far as I'm concerned, I just have one more question.

**[29:07 - 29:07] Speaker 1:** All right.

**[29:07 - 29:17] Speaker 1:** Regarding the, the technical video and the demo video, what are you looking for in.

**[29:17 - 29:20] Speaker 1:** What do you want to see in, in terms of interaction and in terms.

**[29:20 - 29:20] Speaker 2:** Of,.

**[29:23 - 29:29] Speaker 1:** I mean we have this, this catalog of questions and obviously the score kind of speaks for itself, so.

**[29:30 - 29:33] Speaker 1:** But still it's like 55% of the, the entire points.

**[29:34 - 29:37] Speaker 1:** So should we put emphasis more on that?

**[29:37 - 29:38] Speaker 1:** It works that way.

**[29:38 - 29:40] Speaker 1:** Or more on the interaction part?

**[29:40 - 29:41] Speaker 2:** The interaction part.

**[29:43 - 29:48] Speaker 1:** Okay, so just maybe in the technical video mention how we got to this score.

**[29:48 - 29:55] Speaker 2:** You can just briefly mention that and then mostly interaction, I think because if you give the code right, we would be able to see what the kind of stuff you did.

**[29:55 - 30:06] Speaker 2:** So I would maybe consider interactivity and just like showing off some nice cool stuff you built or some UI UX using the web or whatever.

**[30:06 - 30:07] Speaker 1:** Got it.

**[30:07 - 30:16] Speaker 1:** And for the technical video, as you already have the code, we probably won't show you that much code and just like maybe the architecture, how it works.

**[30:17 - 30:21] Speaker 1:** Because if we show you lines of code, it's like, okay, whatever I can already look at.

**[30:21 - 30:23] Speaker 2:** Yeah, okay, cool.

**[30:23 - 30:26] Speaker 1:** And then you know who will be watching the videos?

**[30:26 - 30:26] Speaker 2:** Yes.

**[30:27 - 30:30] Speaker 2:** So it will be me, my colleague Dino.

**[30:30 - 30:32] Speaker 2:** And we have.

**[30:32 - 30:36] Speaker 1:** But is it also the general Shuri watching or is it just Cinera?

**[30:37 - 30:38] Speaker 2:** I think I'm not sure that.

**[30:38 - 30:39] Speaker 2:** I'm not sure.

**[30:39 - 30:43] Speaker 2:** But we also have our head of design, he will also be watching.

**[30:44 - 30:55] Speaker 1:** I talked to Henrik and he said that for the first, basically like selecting the four teams that go on into the final round, it's going to be you guys mostly that or entirely that.

**[30:55 - 30:59] Speaker 1:** Do that part of judging and then afterwards everyone joins.

**[31:00 - 31:15] Speaker 1:** Okay, well, I mean you probably didn't know that then, but I was kind of like confused how we're supposed to explain something in a three minute demo if the others don't really understand what we actually did and also I think.

**[31:15 - 31:21] Speaker 2:** In that case I think they will ask you to do a live presentation or some some such thing okay yeah.

**[31:22 - 32:01] Speaker 1:** Oh okay because the also going to be three other teams that are kind of like presenting the same thing so if we explain the I don't know architecture of what we built everyone is kind of like yeah we kind of heard that before from the other team what is the point like maybe just like in terms of I guess we should maybe dial down the technical part of it and show more of the functionality maybe even or preferably even life then talking about something the others are going to talk about anyways okay cool I'm I'm super happy perfect all right thank you so much all the best.

**[32:01 - 32:06] Speaker 2:** If you have any other questions feel free to send them on Discord as.

**[32:06 - 32:09] Speaker 1:** Well yes sure Is this the.

**[32:11 - 32:12] Speaker 2:** Probably.


# Claude production prompt — Locora, 59-second product demo

You are our creative director, product storyteller, motion designer, editor and sound designer. Use Claude Design and its available capabilities to create a premium product demo film for our conversational indoor-navigation product. Use Claude Motion where available for animation and MP4 export, and Claude Code or available production tools for browser capture, editing, audio and rendering when needed.

Build the film, its editable production source and its final export. A written script or a static storyboard alone is not the finished deliverable. Make strong creative decisions and execute them. Aim for the clarity, pacing and craft of an excellent technology product launch: cinematic, minimal, precise, energetic and memorable.

## 1. The assignment

Create an English-language product demo for **Locora** that runs **59.0 seconds, strictly below 60 seconds including the end card and audio tail**. It tells one continuous story: Paul plans his route on desktop, scans the QR code, walks to a shelf, takes a photo that Locora uses to find his position, and picks up a Red Bull. Only after he has collected it do we introduce his boss Olaf, whose coffee is empty. Olaf requests another coffee; Locora guides Paul to the coffee machine and then to Olaf for the handoff. An unavailable lift can provide the rerouting obstacle on this second journey.

**The order is essential: desktop → QR → shelf → photo/localization → Red Bull pickup → boss with empty coffee → coffee request → coffee machine → delivery to boss → Locora end card.** The Red Bull errand is complete before the coffee request. The shelf scene belongs in the first half, and the coffee handoff is the human payoff near the end.

The audience must understand three things immediately:

1. You can talk to the building to find places and equipment.
2. The desktop plan becomes a mobile guide through the real building.
3. The guide adapts as conditions and tasks change.

Show a real product being used, with a few exceptional visual moments. Convey complexity through clear actions and visual cause and effect. Keep the interface readable and the story easy to follow even on a first viewing.

The product name is **Locora**. Use the supplied Locora logo and brand assets where available, and derive typography and colors from the actual product. If the repository still displays the older heading “Talk to your building,” treat that as legacy interface copy, not the film's product name. Use a clean Locora wordmark if no final logo asset is supplied. Keep name and logo replaceable from one production configuration value.

## 2. Inputs and preparation

**In the Claude harness running this prompt, you have access to the video snippets, their descriptive titles/comments and the full product repository.** The two creators play Paul and Olaf. Locate those supplied assets in your harness and thoroughly analyze them before editing; their absence from Git does not mean they are missing from your available inputs. Read the latest `AGENTS.md`, `README.md`, `web/README.md`, `docs/voice.md`, `docs/localization.md` and current frontend components. Inspect the application itself in both desktop and mobile browser viewports.

The baseline product checks below were prepared at `527713c`; this story revision was synchronized with `e884787` on `main`, on 25 October 2026. Treat the version available when you work as authoritative; features may have changed.

Useful application entry points:

- `/`: building selection.
- `/admin/:buildingId`: desktop workspace.
- `/b/:buildingId`: mobile guide and QR destination.
- `web/src/admin/`: desktop controls, equipment selection, route planning, team panel and QR sharing.
- `web/src/phone/`: mobile modes, camera overlay, route instructions and assistant dock.
- `web/src/voice/`: voice integration, transcript feedback and route synchronization.
- `docs/localization.md` and `localization/`: camera localization and mapping evidence.

The latest checked-in deployment document points to `https://web-production-99671.up.railway.app` for the web app. Verify the current URL before capturing. The former `hagen-core-test-testing.up.railway.app` deployment has been stopped and disconnected; use the current deployment or a local preview. Running and recording the app does not require a new deployment.

Capture your own high-resolution browser footage and screenshots. Use direct application interactions, deliberate cursor movements and clean mobile captures. Compose them with the supplied live-action footage. Inspect the local environment before choosing production tools; use the available tools that can actually perform the required capture, animation, audio mix and export.

Claude Design can establish the visual system and motion compositions. Claude Motion can export code-driven animations as MP4 where available. Neither should be assumed to supply every editing, audio or capture capability. Use a suitable available renderer/editor, such as Remotion plus FFmpeg, if that is necessary to assemble the finished film. Preserve editable timing and replaceable media. Do not settle for a browser animation without a playable video export.

If footage has not arrived, continue with the script, compositions, actual UI capture and a timed animatic. Use named placeholders with their exact required duration. Identify the missing files precisely; do not claim the final film is complete while placeholder footage remains.

## 3. Cast, setting and continuity

**Paul:** a BMW employee visiting an unfamiliar building. One creator plays Paul. Introduce him with a short, restrained name card: `Paul · BMW employee`. This is a fictional demo scenario, not a claim of a BMW customer relationship or endorsement.

**Olaf:** Paul's boss, played by the second creator. Introduce him as `Olaf · Paul's boss`. He is comfortably seated, discovers or shows that his cup is empty, then casually requests another coffee. Show the empty cup before the request so the motivation is immediately clear. Keep this moment dry, brief and human.

**The agent:** the building's conversational guide, heard through Paul's phone. Give it a calm, concise, capable voice, distinguishable from the narrator.

**The first errand:** find and collect the **Red Bull can on the shelf**. Use the actual can and shelf shown in the supplied clips. Match the desktop target, mobile destination, spoken request and pickup to that item and location. Show Paul arrive, take a photo, receive a position result, then take the can and leave. The photograph is used for **Paul's localization** against the mapped building; it is not automatically evidence that Locora visually recognized the can. Keep those two claims distinct.

**The building:** choose one visually strong building with several floors, a lift, stairs, the filmed shelf, a coffee machine and a plausible location for Olaf. Prefer Munich Urban Colab when the current model and available footage support the journey. All interface captures must use consistent building, floor, room and asset identities. Route one goes to the Red Bull shelf. After the pickup and Olaf's request, route two starts from Paul's current position, goes to the coffee machine and finishes at Olaf. If showing a lift failure, establish the lift on route two before replacing that leg with stairs.

The coffee request is a **new task after the Red Bull pickup**. Mark the Red Bull as collected before planning the coffee journey. Do not leave the shelf as a pending waypoint, return Paul to it later, or suggest that he must collect the Red Bull again. At the coffee machine show the usable action in the supplied footage—making, dispensing or picking up coffee—then the journey to Olaf and the handoff.

Use real creator footage for people. Preserve faces, clothing, phone, screen orientation, the collected can and the handed-off coffee across cuts. Check that cups and hands match between machine, walk and handoff shots. Use the actual app UI wherever it supports the scene.

## 4. Product fidelity and the requested demo scenario

Preserve the entire story below. Before recording, make a short internal capability check against the current app. Capture working flows directly. For a requested flow that is still missing, use a clearly identified concept/demo visualization in the edit, styled consistently with the product, and record the substitution in the production notes. Keep those scenes concise and polished. This is a video-production task; implement animation and editing assets without silently changing the product's behavior.

Specific checks from the repository snapshot:

| Requested beat | What needs verification before capture |
|---|---|
| Create a building by uploading floor plans and equipment | The checked-in home page selects existing buildings; an end-user upload/create flow was not present there. Use the real flow if newly available; otherwise depict this opening as an explicit concept sequence. Do not imply arbitrary files are parsed successfully unless demonstrated. |
| Desktop equipment selection, position selection, multi-floor routing and QR handoff | These have implementation paths. Capture actual controls, labels and route results. Verify the QR transfers the same route. |
| Mobile map, floor controls, camera guidance and voice | Inspect the current mobile UI and record the available modes. Use its actual labels; the camera mode may be called `Camera`, rather than `AR`. |
| Phone movement shown on desktop | Verify genuine shared position updates. Camera localization on the phone does not itself prove a desktop subscription exists. Use a labelled visualization if the shared update is still a concept. |
| Lift failure and rerouting | Closure-aware routing exists. Verify the event source, notification and screen update. A staged outage is a demo input, not evidence that the building detected a fault automatically. |
| Olaf's message starts the coffee task after the Red Bull pickup | The team panel contained sample content and browser-local state. Verify messaging and agent integration before presenting it as a live cross-user workflow. Show the completed Red Bull task, followed by coffee machine → Olaf. Preserve this story beat with a concept label if needed. |
| Paul's shelf photograph gives his position | Show the supplied picture-taking clip, the corresponding image/input, the localization step and a successful position result in that order. Verify that the current app supports a still-photo action; if it currently localizes streamed camera frames, use the corresponding real frame or identify a still-photo concept clearly. Do not invent a photo-upload control or present camera pose localization as Red Bull recognition. |
| Wi-Fi plus image/point-cloud positioning | The current rewrite documents visual localization using camera images matched against a prebuilt 3D map. Earlier Wi-Fi experiments are not proof of a working fused system in the current app. Verify both measurement sources and their integration before claiming fusion or accuracy. |

For positioning, the central explanation is now: **Paul takes a picture at the shelf; Locora matches the image to the building's visual map and finds Paul's position.** Place the beautiful, brief `photo → mapped 3D points → position on plan` transition in the shelf scene, before Paul takes the can. Retain the Wi-Fi mention only in the truthful treatment below and only if it fits without distracting from this causal sequence.

The shelf-scene narrator line is: **“Take a photo. Locora finds his position.”** If both Wi-Fi and visual measurements work together, a short callout can say `Wi-Fi + visual mapping`. If only visual localization is implemented, use `Visual mapping` and, if retaining the planned Wi-Fi mention, a readable `Wi-Fi support · in development` callout. Do not depict a working fusion pipeline that has not been implemented. Use “accurate” or a numerical precision claim only when the shown deployment and footage have matching validation evidence.

Keep any required `Concept preview` or `Demo scenario` labels consistent and legible. Do not bury the distinction in tiny end credits. These checks should support a strong film, not turn it into a technical presentation.

## 5. Locked 59-second story and suggested script

Use this timeline as the first cut. You may tighten wording and micro-timing after measuring the actual voices, while preserving the order and all story beats. The final runtime stays below 60 seconds. The suggested dialogue is intentionally short: show the features instead of explaining every click.

| Time | Picture, action and edit | Spoken audio | Designed text |
|---|---|---|---|
| **00:00–00:03** | Immediate hook: Paul at the desktop application in an unfamiliar building. Introduce him with one clean name card and reveal the building picker. | **Narrator:** “Meet Paul. New building. One thing to find.” | `New building.` → `Where do you start?` Small Paul name card. |
| **00:03–00:07** | Paul selects **Create building** in the real flow if available. Two tidy imports—floor plans and equipment—resolve into one building. Match-cut into the opened desktop workspace. Use a concept treatment if the import UI is missing. | **Narrator:** “Upload the plans. Bring the building to life.” | `Floor plans + equipment` → `One building.` |
| **00:07–00:11** | Three precise desktop highlights: set Paul's starting position; select the Red Bull/shelf destination; show the route through the building and relevant floors. Zoom into the important controls and back to the route. The shelf is the first destination. | **Narrator:** “Set your position. Find what you need.” | `You are here.` → `Red Bull.` → `Route ready.` |
| **00:11–00:14** | Paul completes route planning and opens the real QR sharing panel. Cut to the real-life shot of him scanning the desktop QR code. Match the QR's shape into the phone screen. The loaded mobile route must match the desktop route. | **Narrator:** “Scan. Your route comes with you.” | `Desktop → pocket.` |
| **00:14–00:20** | Split screen: readable phone UI on the **left**, Paul walking toward the shelf on the **right**. Start in map view; show the active floor, destination and voice state. Use the strongest portion of the walking/phone clip. Let the short voice exchange anchor the product. | **Paul:** “Locora, where's the Red Bull?” **Agent:** “Follow this route to the shelf.” Prefer the actual recorded exchange if its wording differs; keep the meaning and timing. | `Just ask.` → `This way.` |
| **00:20–00:27** | First payoff: Paul reaches the shelf, raises his phone and takes a picture. Match-cut to that image, then mapped 3D points and his position on the plan. Show the real mobile camera/localization state and a matching desktop marker if shared tracking is verified. Return to the live-action shot: he takes the Red Bull and starts walking away. This exact action order must remain clear. | **Narrator:** “Take a photo. Locora finds his position.” Leave a beat for the shutter/position confirmation and pickup. | `Photo → position.` → `Red Bull collected.` |
| **00:27–00:31** | Only now introduce Olaf. A close-up shows his empty cup, then his relaxed reaction and request. An eyeline, tilt of the cup or a brief cutaway makes “another coffee” immediately understandable. Show the message being sent if the supplied footage supports it. | **Olaf:** “Paul, I'm out. Coffee, please?” Use the actual recorded request if available and concise. | `Olaf · Paul's boss` and message `Another coffee, please.` |
| **00:31–00:35** | Back to phone-left/Paul-right. Paul receives the request after his Red Bull pickup. Locora plans from his current location to the coffee machine and then Olaf. Show the completed Red Bull task separately from the new route. | **Agent:** “Coffee machine first. Then back to Olaf.” | `New request.` → `Coffee machine → Olaf.` |
| **00:35–00:41** | Phone-left/desktop-right: establish that the coffee route uses the lift, trigger its unavailability, show the restrained red warning and redraw that leg via the stairs. Reconnect to a short real walking/stairs shot where available. The coffee destination stays active. | **Agent:** “The lift is out of service. Rerouting you via the stairs.” | `Lift unavailable.` → `Route updated.` |
| **00:41–00:47** | Paul reaches the coffee machine. Choose only the decisive actions from the actual snippets: arrival, machine/button/cup detail, dispensing or pickup, then departure with coffee. Condense waiting with a clean jump cut or a brief speed ramp on silent action. Establish that this coffee will go to Olaf. | **Narrator:** “Plans change. Locora keeps you moving.” Or let the machine sounds carry the beat if the cut is clearer without narration. | `Coffee stop.` → `Next: Olaf.` |
| **00:47–00:54** | Brief guided walk, then Paul hands the coffee to Olaf. Match cup, hand and direction of movement across the shots. Hold Olaf's satisfied reaction; this is the final human payoff. Paul has already collected the Red Bull—do not return to the shelf. | Optional **Olaf:** “Perfect. Thanks.” Favor a genuine reaction from the footage and leave space for the cup landing. | `Coffee delivered.` → `Two tasks. Done.` |
| **00:54–00:59** | A route line, locator marker or cup match cut resolves into the **Locora** logo/wordmark on a clean background. Hold the final composition; resolve the score and finish cleanly before 60 seconds. | **Narrator:** “Find your way. Find your thing.” | **Locora** and **“Find your way. Find your thing.”** |

The desired emotional arc is **uncertainty → desktop control → mobile freedom → photo/localization and Red Bull success → the boss's empty-cup interruption → an adaptive coffee journey → a satisfying handoff**. The shelf is the first product payoff. Olaf creates the second task and the smile. The lift is a short obstacle during that task. Coffee delivery completes the story.

Story clarity outranks clip coverage. It is better to use one excellent second from a long clip, or omit a redundant clip, than to distort this sequence. If the timeline becomes crowded, shorten repeated walking, machine waiting, extra UI clicks or the opening import montage first. Preserve the photo → localization → Red Bull pickup, the empty cup → request, and coffee machine → delivery relationships.

The narrator, Paul, Olaf and agent never speak over one another. Measure all recorded/generated lines before locking the cut. Aim for roughly 100–125 spoken words total with room for the photo, pickup and handoff to register; individual exchanges must fit comfortably into their allocated scenes. If a line is too long, shorten it rather than rushing the voice or speeding up a person's speech unnaturally.

## 6. Visual direction and animation

Extract the actual interface's visual language: warm light surfaces, dark ink, accent colors, corner radii, type and icon treatment. Let that system lead. Extend it with premium motion graphics and restrained cinematic framing. Keep the contrast strong enough for a projected hackathon demo.

- Use real UI footage as the visual anchor. Favor contextual zooms, sharp crops, tracked callouts, cursor emphasis and carefully timed click feedback.
- Keep one main action per shot. A short sequence of legible actions carries more information than many simultaneous overlays.
- Make the multi-floor route reveal a hero moment: stacked levels, one clear path, then a decisive zoom into the next interaction.
- Use the QR handoff as a signature match cut. It should visibly connect desktop planning to mobile navigation.
- Make the lift-to-stairs reroute visibly causal: red closure cue, old path disappears, new path draws, guidance updates.
- Use the same visual grammar when the coffee request creates the next journey. Clearly complete the Red Bull task first; the new route is coffee machine → Olaf.
- Show the camera/point-cloud relationship with actual mapping assets where available. Use a purposeful technical visualization rather than decorative particles unrelated to the scene.
- Keep phone-left/person-right and phone-left/desktop-right layouts consistent. The phone interface must remain readable in a 1920×1080 master; crop into the relevant portion when a full phone view becomes too small.
- Use fast, controlled motion with clean easing. Let key results settle. Reserve the strongest transitions for the QR handoff, shelf photo-to-position reveal and Locora end card.
- Avoid a generic slide-deck rhythm, constant camera drift, excessive glitch effects or visual clutter. Make the excitement come from confident editing, action and sound.

## 7. Voice-synchronized typography

The text is **designed kinetic typography**, integrated into the composition. It should feel like part of the film's visual language.

- Synchronize words or short phrases to the actual audio, using real word timestamps or manually checked alignment.
- Choose placement deliberately: upper right, upper left, lower left or free negative space, depending on the shot. Change placement between shots when composition motivates it.
- Hold placement within a phrase; do not make viewers chase moving words around the frame.
- Use short phrases, generally two to six words, with selective emphasis. Favor “Just ask,” “Lift unavailable,” “One more stop” and “Right there” over paragraphs.
- During narrator lines, show the key idea. During the central Paul/agent exchanges, make the important question and answer understandable with sound off.
- Avoid duplicating a full sentence in several simultaneous text elements. Do not cover faces, equipment targets, the QR code, navigation arrows or active controls.
- Use confident type scale, excellent spacing and a small number of consistent entrance/exit motions. An emphasized word may appear on a beat or as the agent completes its thought.
- Maintain safe margins and readable contrast. Supply a separate complete SRT or VTT for accessibility; the burnt-in kinetic text may be selective.

## 8. Voice, music and sound design

**Narrator:** premium English product-presentation voice. Warm, confident, clear and conversational, with human phrasing and intentional pauses. Avoid an exaggerated trailer voice, flat synthetic cadence or relentless enthusiasm. Use a suitably licensed voice from the available tools. No imitation of a recognizable presenter is needed.

**Paul and Olaf:** favor the creators' real recorded dialogue. Keep it intimate and natural. Clean noise, match loudness and preserve the character of their voices.

**Agent:** prefer a clean recording of the actual ElevenLabs-powered interaction. The agent should sound like a helpful guide in the product. If clean dialogue needs a separately generated take, use an available licensed voice and document that it is a scripted production take. Keep lip sync and phone-speaker playback credible.

**Music:** one cohesive dramatic instrumental cue, composed or edited to the 59-second story. A controlled electronic/cinematic pulse around 115–125 BPM is a good starting point. Adapt its intensity to the events:

- **00–14 s:** immediate intrigue, then rhythmic confidence as the building and route appear.
- **14–27 s:** momentum and discovery, room for Paul's voice interaction, then a precise accent on the shelf photograph/localization and the Red Bull pickup.
- **27–35 s:** a lighter rhythmic pocket for Olaf's empty cup and request, then renewed forward motion as Paul gets the coffee route.
- **35–41 s:** a brief tension dip or harmonic interruption for the lift failure, then a satisfying release as the stairs route draws.
- **41–54 s:** regain momentum at the coffee machine, condense the preparation rhythmically and land warmly on the handoff and Olaf's reaction.
- **54–59 s:** a short final lift and clean musical resolution under Locora and the slogan.

Use restrained, meaningful effects: a soft interface click, a QR confirmation, a distinct warning, a reroute confirmation and the coffee cup landing. Align them to visible events. Duck music under every spoken line; the voice must remain intelligible on ordinary laptop speakers. Keep dialogue, music and effects on separate stems. A useful web master target is approximately −14 LUFS integrated with peaks below −1 dBTP, subject to a listening check.

Use audio you have permission to include in the exported film. Record music/voice provenance in the asset manifest. Reuse available authorized services and assets; report missing access precisely instead of silently assuming tools are available.

## 9. Thorough footage review and edit decisions

You have the snippets and their titles/comments in your Claude harness. **Analyze all supplied clips before selecting takes; do not assemble the film from filenames alone.** Watch each clip from beginning to end, listen to its audio and inspect the key action frames. Read supplied titles, comments, captions, sidecar notes and available media metadata. Treat those descriptions as context, then verify what the picture and sound actually show.

For each clip, record its actual filename/title, duration, orientation, frame rate, actor, location, props, observed actions, useful dialogue, camera movement and any continuity or audio problems. Identify exact source in/out timestamps for the usable portions. Specifically find:

- Paul operating the desktop UI and scanning the QR.
- His approach to the shelf, the moment he takes the picture, the matching phone/image view, and the actual Red Bull pickup and departure.
- Olaf's empty-cup beat and coffee request; keep the motivation before the request in the edit.
- Paul receiving the new task, approaching the coffee machine, making/collecting the coffee, leaving with it, and delivering it to Olaf.
- Short reaction shots, walking connectors and any real screen recordings that strengthen those beats.

Write a compact `footage-review.md` and an `edit-decision-list.csv` with **actual source names, source in/out, selected action, destination scene/time, crop, playback speed, audio choice and reason for selection or omission**. A title/comment must never substitute for observed action. Do not invent clip contents or timestamp precision before inspecting the media.

Choose the strongest takes for the narrative, not the largest number of clips. Preserve clear starts and results of actions while removing dead time, repeated movements, setup and failed takes. Walking and coffee-machine waiting can use brief speed ramps or jump cuts; keep spoken dialogue, QR scanning, the photograph, the Red Bull grab and the coffee handoff readable at natural speed. Keep dialogue pitch natural and use room tone or the score to bridge action cuts. A long source clip may contribute only a second or two. Do not force unused footage into the film.

Match the supplied filenames to the following story slots by their actual content. These are descriptive slots, not required names to impose on existing files:

| Story slot | What to select from the supplied footage |
|---|---|
| Desktop interaction | Paul at the computer, with hands and screen available for the UI match cut. |
| QR handoff | The phone scanning the desktop QR and opening the guide. |
| Walk and voice | Paul walking toward the shelf and using/talking to the app. |
| Shelf photo | Paul reaching the shelf and taking the photograph; matching camera/image view where supplied. |
| Red Bull pickup | The decisive can grab, followed by Paul leaving the shelf. |
| Empty cup | Olaf checking, tilting or reacting to his empty coffee cup. |
| Coffee request | Olaf requesting another coffee, plus any corresponding phone action. |
| Coffee-machine arrival | Paul approaching the machine after the new request. |
| Coffee preparation/pickup | The clearest button, cup, dispensing or pickup action; use only the necessary moments. |
| Coffee delivery | Paul walking with the coffee, handing it to Olaf and the boss's response. |

Work with the supplied clips first. Request another recording only if a crucial action cannot be communicated with the available material. Capture the phone screen separately in portrait if needed and sync it to the real action. Favor original-resolution footage; do not enlarge a tiny phone recording and call it 4K.

Capture the actual Red Bull route and then the separate coffee-machine → Olaf route, relevant floor transitions, the coffee route's lift leg and alternative stairs. Choose screen takes in which the interface, carried objects and spoken directions agree. Show a real QR at a scannable size in the capture; motion styling should preserve the actual handoff.

## 10. Production workflow and deliverables

Work in a dedicated `demo-video/` production folder or equivalent. Keep original media intact and use an asset manifest with source filenames, selected in/out points, scene placement and any concept substitutions. Store large footage and exports locally unless the team explicitly requests uploading them.

1. Inspect the current product and thoroughly review the supplied media and comments as specified in §9. Resolve the real building, Red Bull shelf, coffee machine, Olaf destination, Locora logo, available voice tools and renderer.
2. Make a concise shot plan, footage review, edit-decision list and capability note. Preserve the revised Red Bull-before-coffee story while identifying any genuinely missing footage or concept scenes.
3. Record desktop and mobile UI. Select matching creator takes.
4. Produce or clean voice audio, obtain actual timings, then lock a sub-60-second animatic.
5. Use Claude Design for visual compositions, brand consistency and motion treatments. Use Claude Motion or the available rendering pipeline to produce the animations and assembled film.
6. Compose the music and effects around the actual dialogue and story beats. Refine typography against that audio.
7. Render and watch the entire export at normal speed. Also inspect key transition frames, split-screen readability, audio balance, text alignment and the final duration. Iterate until the film works as a coherent product story.

Deliver:

- **`product-demo-final.mp4`**: 1920×1080, 16:9, constant 30 fps, H.264 with AAC audio, exactly 59.0 seconds as the target and always below 60 seconds. Include all audio tails within that runtime. At 30 fps, the 59-second timeline contains 1,770 frames.
- Editable source/project with one master timeline, replaceable media slots and a single name/logo configuration.
- Final script and timed shot list.
- `footage-review.md` and `edit-decision-list.csv`, linking the chosen source portions to their places in the final story and explaining significant omissions or speed changes.
- Separate narration/dialogue, music and effects stems.
- Complete SRT or VTT timed to the finished audio.
- Asset/source manifest and a concise list of any remaining missing inputs or concept visualizations.

Before calling the export final, confirm that Paul and Olaf are introduced correctly; the film uses **Locora** consistently; the desktop route and QR handoff lead to the shelf; the photo is taken and used for localization before the Red Bull pickup; the Red Bull task is complete before Olaf's empty-cup request; the coffee-machine visit precedes the handoff; any lift reroute belongs to that coffee journey; the voice and text agree with the footage and screens; the final slogan is readable; and the media file actually plays with sound and finishes below 60 seconds. Reject any cut that accidentally returns to the old coffee-before-shelf order.

Start by inspecting the repository and available footage, then build the film. The final result should make someone think: **“I can talk to this building—and it will get me to the right place and the right thing.”**

## Tool references

These references explain the intended Design/Motion split; use the capabilities actually available in your session:

- [Claude Design: designs, prototypes, codebase context and Claude Code handoff](https://support.claude.com/en/articles/14604416-get-started-with-claude-design).
- [Claude Motion: code-driven animations and MP4 export](https://support.claude.com/en/articles/17454997-get-started-with-claude-motion).

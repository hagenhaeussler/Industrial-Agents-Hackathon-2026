# Office demo preparation

The phone guide has **Find an object** in map, steps and camera mode. At the final stop, open it, ask a question
(default: “Where is Dido?”), take a photo and tap **Analyze and speak**. Claude checks the photo and ElevenLabs
speaks the answer using the existing agent's voice. Navigation speech pauses first. If autoplay is blocked,
tap the visible audio Play control. Text remains available if speech fails. No microphone is needed for this action.

Describe an unfamiliar named object, for example “Dido, the yellow toy with the blue hat”, or make its label
readable. A name alone does not establish what an object looks like. Unclear, absent and ambiguous targets must
not receive invented locations. Directions are relative to the photographer's viewpoint, not the building map.

Photos go only after the explicit Analyze action. The browser resizes to 1600 pixels and re-encodes without EXIF;
the server decodes again, bounds size/pixels and removes metadata. The app does not persist photos or provider
payloads. Claude receives the photo and question; ElevenLabs receives only the short answer, with TTS logging
disabled. Provider retention policies still apply. These are separate from the camera frames used for localization.

## Configuration

On the existing Railway **voice-agent** service, set `ANTHROPIC_API_KEY` in its private variables. It already needs
`ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID`. Optional: `PHOTO_MODEL` (default `claude-sonnet-5-5`),
`PHOTO_VOICE_ID` (otherwise the configured agent voice), `PHOTO_DAILY_LIMIT` (default 10).
Keep the deployed web origin in `VOICE_CORS_ORIGINS`. The existing web `VITE_VOICE_SERVER` continues to point
to this service; no browser API keys are needed. `GET /api/voice/photo` reports availability without a paid call.
`POST /api/voice/photo?question=…` accepts a JPEG/PNG body, up to 4 MiB, and returns the answer plus optional MP3.

There is one simultaneous photo request per server process, a 55-second deadline and no automatic paid retries.
The UTC daily attempt counter is per process and resets on restart: it is a demo safeguard, not a durable billing
cap. Keep one replica, monitor provider usage and use provider-side spending controls for a broader rollout.

For local use, load the same private `.env`, set `VOICE_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`,
run `uv run python -m voice_agent serve data --port 8020`, and start the frontend with
`VOICE_SERVER=http://127.0.0.1:8020 pnpm --dir web dev`. The building API runs separately on port 8010 as usual.

## Add the real Demo office when ready

1. Supply a dataset-format `building.json` with a unique stable building ID and `building.name` set to `Demo`.
   Keep floor/space/opening/asset IDs consistent; include walkable spaces, connected doors, the start and final
   destination. Use metres in the geometry. The validator reports missing or inconsistent references.
2. **Add Demo JSON** on Home previews a validated upload. For the shared demo release, also commit that exact
   file as `data/demo/<building-id>/building.json`, run the checks and deploy main. This includes the same model
   in both web and voice images and survives replacement of the current ephemeral web database. A browser upload
   alone does not synchronize the separate voice catalog or make storage persistent.
3. Record a slow, overlapping walk through the new office, including the start, junctions and destination.
   Follow [the localization preparation workflow](localization.md) to build the visual map and align it to the
   JSON's floor IDs, space IDs, metre coordinates and heading. Install it on the existing localization GPU
   service under the exact same building ID. A JSON plan alone cannot provide visual tracking.
4. Verify a phone photo returns `reliable: true` from the new map in several known rooms. Check heading and
   floor as well as position; do not use a map of the previous office. Confirm two successive room fixes update
   the route, and loss of localization does not claim continued tracking.
5. On the actual demo phone over HTTPS, allow camera access, choose start and final destination, walk the route,
   then take the object photo. Test a visible target, an absent target and two similar targets. Use the audio Play
   control if the phone blocks autoplay. Check microphone permission separately for conversational navigation.

Until the file arrives, Home shows **Demo — Awaiting building.json** and the existing buildings remain usable
for the photo feature. No mock office or synthetic position is presented as the real demo. Mapped-building
workspace entrances now use an approximately five-second globe/approach/tilt sequence, with Skip and reduced-motion
support; failed or slow maps still release the workspace within five seconds.

## Release verification

Local checks on 25 October 2026: 154 Python tests, 102 web tests and 22 building-view tests passed; Ruff,
TypeScript and both production builds passed. Existing large-bundle warnings remain.
The live test used a synthetic labeled scene, not a venue photo: Claude correctly located Dido left of the blue
book, ElevenLabs returned MP3 audio, and the 390×844 browser completed 13.8 seconds of playback without an audio
error. The browser capture/upload and the real HTTP photo handler were exercised. No microphone or physical
phone was used. Offline tests cover ambiguous/absent results, upload rejection, cancellation, daily limits,
concurrency and speech failure. Real office localization still waits for the matching JSON and prepared scan.

The production services auto-deploy from main. The connected account used for this change has no access to that
Railway project, so production secrets and build status cannot be changed through it. Check the public photo
capability and configure the voice service variables above if it reports unavailable.

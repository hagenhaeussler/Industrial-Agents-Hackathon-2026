# Building voice bridge (CONTRACTS C1)

Claude owns the visible voice UI and mounts one `ConversationProvider` from `@elevenlabs/react` around it. Inside that provider:

```tsx
const voice = useBuildingVoice({
  agent: 'navigator', // 'admin' on the admin screen
  sessionId,
  onDisplay: display => updateVisibleBuilding(display),
})
// A user gesture calls await voice.start(); catch its error and keep text chat visible.
// voice.status, voice.isSpeaking and voice.error drive the UI; await voice.stop() ends it.
```

The hook fetches `/api/voice/token?agent=navigator|admin` and starts WebRTC using `startSession({ conversationToken })`. The server exchanges its key at ElevenLabs and returns only `{token, agent_id}`. Missing configuration or a provider failure returns HTTP 503 `voice_unavailable`; no live or paid provider calls are needed for the repository tests. Keys stay in the local/server environment.

`package.json` temporarily overrides `livekit-client` to `2.16.1`, as recommended by the ElevenLabs Agents integration guide. Newer clients can request `/rtc/v1`, which the ElevenLabs LiveKit server may not support, preventing the WebRTC handshake. Remove the override and refresh `bun.lock` after the upstream server/SDK compatibility issue is fixed and a WebRTC smoke test passes.

All eleven C1 client tools use `POST /api/tools/{name}` with `{session_id, args}`. A stable `op_id` is stored per session/proposal for `commit_edit`, including retries and page reloads. The server independently enforces roles and proposal idempotency. The callback receives `(display, fullResponse)` only after success. The agent receives valid JSON of at most 1,500 characters; large results keep key IDs and direct the user to the application. Failures remain `ok:false`. Configure every ElevenLabs client tool to **Wait for response**.

The hook shares a `next_step` request generation across handler recreations. A newer `next_step` (including `no_route`), explicit stop or session/agent teardown suppresses an older instruction before display and speech; committed admin operations still report their real outcome. A retired session cannot repaint its replacement. Context updates alone do not cancel a sole instruction that has already advanced the server index. Pending token requests are aborted and invalidated on stop or teardown; late responses resolve quietly without starting voice or showing a stale error. This covers cancellation before the SDK starts, with the SDK retaining responsibility for its own connection lifecycle.

Use `voice.sendContext(text)` after real application state changes; it wraps `sendContextualUpdate` while connected, which does not itself trigger a spoken reply. C1 phrasings:

- `Position: <space name> (<floor name>), source <marker|manual|tour start>.`
- `Tour <tour_id> loaded: <n> stops, next <label>.`
- `Building changed: <summary>. The active tour was replanned: <new length> m, next <label>.`
- `Building changed: <summary>. No route is available any more: <reason>.`
- `Stop collected: <label>. <k> of <n> done.`

Pass a new `sessionId` only after stopping an active conversation, so a spoken tool cannot act in a different session during a screen change. Return to text chat on permission denial or provider failure.

SDK reference: [ElevenLabs React SDK](https://elevenlabs.io/docs/eleven-agents/libraries/react), [WebRTC token endpoint](https://elevenlabs.io/docs/api-reference/conversations/get-webrtc-token), checked 24 October 2026. No camera frames are recorded or uploaded by this module.

The desk, phone chat and admin share the real voice transcript. `sendText(text)` submits a user turn to the connected ElevenLabs conversation; disconnected text chat continues through `/api/chat`. `sendContext(text)` supplies current app state without asking the agent to speak. Never send a session bearer or admin code in contextual text.

The compact `VoiceOrb` reflects actual connection, speaking, mute and sampled audio levels. `VoiceConversation` shows real messages, safe asynchronous failures, Retry, mute and End. Voice starts only from a user gesture. The SDK and token fetch have bounded connection/teardown waits; replacing a session retires its audio, requests, messages and UI callbacks.

Two browser-only planning desk tools, `update_selection` and `focus_floor`, are separate from the eleven server tools. They validate IDs against the currently loaded building and return actual outcomes. Phone and admin contexts do not expose these actions. Server authority, admin preview/confirmation and write idempotency are unchanged.

Navigator preview operations: 10 calls per day, at most 180 seconds per call, one concurrent conversation (user-approved). Admin retains its separate existing limits. These ongoing limits are separate from the $5 development testing budget.

# Building voice bridge

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

The backend tool names come from generated `api/agentTools.gen.ts`: 17 names in the shared catalog. `GET /api/agent/tools?session_id=...` returns definitions filtered by the session's role. The server also enforces the role on each call. The browser registers each real user transcript with `POST /api/agent/turns` and `{session_id, message}`. Only transcript events with `source=user` authorize a turn; agent messages and context updates do not. Accepted typed submissions register the user's text without requiring a provider echo. Matching echoes do not register a second turn.

Tools wait for the returned `turn_id`, then use `POST /api/agent/tools/{name}` with `{session_id, turn_id, args}`. Failed registration cannot reuse an earlier turn. A stable `op_id` is stored per session/proposal for `commit_edit`, including retries and page reloads. The server enforces proposal idempotency. An admin edit needs a preview and explicit confirmation of that preview in a later real user message. A model argument or tool result cannot supply that confirmation.

The display callback receives `(display, fullResponse)` only after success. The agent receives the complete compact `model_result` as JSON, with speech and any error, within 48 KiB (49,152 UTF-8 bytes). If the complete response exceeds that limit, it receives an explicit `result_too_large` error and a request for a smaller page or fewer entities. Rows and candidates are never silently truncated. Failures remain `ok:false`. Configure every hosted ElevenLabs client tool to **Wait for response**.

The hook shares a `next_step` request generation across handler recreations. A newer `next_step` (including `no_route`) suppresses an older instruction before display and speech. A new user turn supersedes pending results. Stop, retry or session/agent teardown retires conversation callbacks and blocks further tool calls. An already dispatched admin commit can still return its actual outcome after stop, but cannot repaint a retired view; a newer user turn suppresses its stale result. Context updates alone do not cancel a sole instruction that has already advanced the server index. Pending token and transcript requests are aborted and invalidated on stop or teardown. Late responses cannot start voice, reuse an old turn or show a stale error. The SDK retains responsibility for its connection lifecycle.

Use `voice.sendContext(text)` after real application state changes; it wraps `sendContextualUpdate` while connected, which does not itself trigger a spoken reply. Example messages:

- `Position: <space name> (<floor name>), source <marker|manual|tour start>.`
- `Tour <tour_id> loaded: <n> stops, next <label>.`
- `Building changed: <summary>. The active tour was replanned: <new length> m, next <label>.`
- `Building changed: <summary>. No route is available any more: <reason>.`
- `Stop collected: <label>. <k> of <n> done.`

Pass a new `sessionId` only after stopping an active conversation, so a spoken tool cannot act in a different session during a screen change. Return to text chat on permission denial or provider failure.

SDK reference: [ElevenLabs React SDK](https://elevenlabs.io/docs/eleven-agents/libraries/react), [WebRTC token endpoint](https://elevenlabs.io/docs/api-reference/conversations/get-webrtc-token), checked 24 October 2026. No camera frames are recorded or uploaded by this module.

The desk, phone chat and admin share the real voice transcript. `sendText(text)` submits a user turn to the connected ElevenLabs conversation; disconnected text chat continues through `/api/chat`. `sendContext(text)` supplies current app state without asking the agent to speak. Never send a session bearer or admin code in contextual text.

The compact `VoiceOrb` reflects actual connection, speaking, mute and sampled audio levels. `VoiceConversation` shows real messages, safe asynchronous failures, Retry, mute and End. Voice starts only from a user gesture. The SDK and token fetch have bounded connection/teardown waits; replacing a session retires its audio, requests, messages and UI callbacks.

Two browser-only planning desk tools, `update_selection` and `focus_floor`, are separate from the 17 backend tools. They validate IDs against the currently loaded building and return actual outcomes. Before each browser handler runs, the hook checks the registered turn with `GET /api/agent/turns/{turn_id}?session_id=...`. Both IDs are URL-encoded and the fetch uses `cache: 'no-store'`. The response must confirm the same turn. The hook checks the local turn and connection again after validation. Failed registration, failed validation, a newer turn or a retired connection blocks the UI action. This includes another voice or text request that supersedes the turn in the same server session. A remote `version_conflict` from validation or a backend tool clears cached turn authority and invalidates pending turn guards. A new real user registration can restore authority. The current backend conflict still reaches the model as a failure. Phone and admin contexts do not expose these actions.

Browser observations use the same complete-response rule and 48 KiB UTF-8 limit as backend observations. A successful selection response includes every selected asset ID and the total count. Unknown or ambiguous floor responses include every available or matching candidate. An oversized response returns `ok:false` with `result_too_large`; it never returns an incomplete list. The existing selection callback still applies the validated selection. Each selection request remains limited to 100 item entries.

Recorded Navigator preview limits: 10 calls per day, at most 180 seconds per call, one concurrent conversation (user-approved). Admin retains its separate existing limits. These ongoing limits are separate from the $5 development testing budget.

These limits describe the recorded hosted configuration. Local bridge, prompt and generated catalog changes do not update the hosted ElevenLabs agents. This integration did not change or verify provider accounts. Check the hosted tool definitions and prompts separately before claiming that this refactor is deployed there.

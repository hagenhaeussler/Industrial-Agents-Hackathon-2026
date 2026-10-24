# Live provider smoke setup

This is the limited smoke setup for 24 October 2026. Credentials remain in the local `.env` and Railway service variables; never commit them, print them, put them in URLs, or expose them through `VITE_*` variables.

## Environment and budget

The local builder repository's root `.env` is mode `0600` and ignored by Git and Docker. The application automatically loads that path without overriding existing environment variables. Keep it private and preserve those exclusions when preparing an image or checkout.

Set these **server-only** variables locally and on the Railway service:

- `ANTHROPIC_API_KEY` and a positive `TYB_CHAT_BUDGET_USD` for text chat.
- `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN` for voice.
- `TYB_ADMIN_TOKEN` for authenticated admin sessions. Keep `TYB_DEMO_MODE=0` and unauthenticated demo admin access disabled for this smoke.

The human-approved **$5 total** is allocated once:

| Smoke | Allocation |
|---|---:|
| Local Anthropic chat | $1 |
| Railway Anthropic chat | $1 |
| ElevenLabs conversations/evaluations | $3 |

Use `TYB_CHAT_BUDGET_USD=1` for each initial chat allocation. Chat metering is **per process and in memory**: a restart, redeploy, or extra worker is not a fresh spending authorization. Reconcile completed and interrupted calls, including provider-reported spend, before restarting; set any resumed process to the remaining allocation. Keep one server worker and a shared running total across local, Railway and ElevenLabs. Provider limits supplement this ledger; they do not replace the $5 ceiling. ElevenLabs usage is billed through its own workspace configuration, not automatically through the application's Anthropic key.

## Dedicated ElevenLabs agents

Account ownership was verified as **hagen.haeussler@berkeley.edu** through tool-creator metadata and an MCP read. These dedicated MCP-created test agents use authentication, audio recording disabled, a maximum conversation length of **60 seconds**, a daily limit of **2 conversations**, and concurrency **1** per agent:

| Role | Agent ID | Client tools |
|---|---|---|
| Navigator | `agent_0101m5qww08ffh2rxr13f8nzq98r` | `find`, `plan_tour`, `route`, `next_step`, `spatial_query` |
| Admin | `agent_3101m5qww3ddexhvqxb3cy7kxzz9` | `propose_edit`, `commit_edit`, `undo`, `what_if`, `set_scale`, `generate_markers` |

Use the tracked [navigator](../agent/voice_prompts/navigator.md) and [admin](../agent/voice_prompts/admin.md) prompts. Configure client tools to wait for responses and match [the server schemas](../server/tools.py). No custom dynamic variables or conversation overrides are required: the browser supplies the trusted application session when invoking tools. Admin changes still require an authorized admin session, a preview, and explicit confirmation. `set_scale` currently returns `not_available`.

The browser starts authenticated **WebRTC** with a newly generated short-lived conversation token from `/api/voice/token?agent=navigator|admin`; it receives no provider key. `livekit-client` is temporarily pinned to **2.16.1** because newer clients can request an unsupported `/rtc/v1` handshake. Remove the pin only after upstream compatibility is fixed and a WebRTC smoke passes. See [the voice bridge](../web/app/src/voice/README.md).

Navigator prompts use `plan_tour` with one item for a collection journey. The integrated frontend also renders standalone `route` geometry as a separately labelled preview without changing collection progress. Collection and final arrival remain explicit phone controls.

## Recorded evidence

Local real chat completed `find` and `route`, with **$0.042682** metered spend against the local allocation. Local navigator and admin token requests returned **HTTP 200** with **`Cache-Control: no-store`**. Token minting alone does not prove a live voice conversation or client-tool round trip.

The root agent records the final exact cloud SHA, test counts and deployment/provider outcomes in the PR's release-verification comment. Do not infer cloud or voice success from this setup document or from local checks.

Four ElevenLabs one-turn tool tests passed (lookup, visible planning, preview, and no unconfirmed commit), with provider-reported LLM/platform prices totaling **$0.023610225**. These use the provider testing stub and prove tool choice/arguments, not execution in a live browser. Secret-free configurations and test IDs are in [elevenlabs-agents/](elevenlabs-agents/).

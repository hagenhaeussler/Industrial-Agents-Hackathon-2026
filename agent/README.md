# Text and voice agents

`ChatAgent(registry, session_provider)` uses the shared platform registry. The server wires it to `/api/chat`. Each turn reads the current session, then runs at most six Sonnet tool iterations. History stays in memory per session. A server restart clears that history. Durable session position and tour state come from the platform.

Code blocks commits until a later explicit confirmation of the pending preview. Another session cannot confirm it. Repeated tool calls for the same confirmed proposal return the same result without another registry commit. The platform also checks roles and stores commits atomically.

The prompt modules are under `skills/`. The two dashboard-ready voice prompts are under `voice_prompts/`. Each voice file includes its first message and fits the 2,500-character limit. No edits were made to the human-owned ElevenLabs configuration document.

## Paid run configuration

No paid run is approved or measured in this checkpoint. Before enabling a run, write the dollar limit, scope and time in `master prompt/Lenard's codex/STATUS.md`. The human can then supply server-side configuration:

- `ANTHROPIC_API_KEY`.
- `TYB_CHAT_BUDGET_USD`: a positive dollar cap for this ChatAgent process.

The key alone does not enable requests. The shared process budget reserves a conservative maximum cost before each model request and settles it from usage afterward. Automatic SDK retries are disabled. Restarting the process resets the in-memory budget. A restart needs a new written run allocation. The rates come from the supplied master plan and need confirmation before a paid run if the provider changes them.

Keep live credentials absent from offline tests:

```sh
env -u ANTHROPIC_API_KEY uv run pytest -q tests/agent
```

Tests inject an offline client. They exercise real SDK tool wrappers, edit confirmation, session isolation, bounded settings, prompt limits and numeric grounding. This proves the code path, not live model quality. The human voice comparison and live text transcripts remain pending a written budget and provider setup.

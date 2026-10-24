# Text and voice agents

`ChatAgent(registry, session_provider)` uses the shared platform registry. The server wires it to `/api/chat`. Each turn reads the current session, then runs at most six Sonnet tool iterations. History stays in memory per session. A server restart clears that history. Durable session position and tour state come from the platform.

Code blocks commits until a later explicit confirmation of the pending preview. Another session cannot confirm it. Repeated tool calls for the same confirmed proposal return the same result without another registry commit. The platform also checks roles and stores commits atomically.

The prompt modules are under `skills/`. The two dashboard-ready voice prompts are under `voice_prompts/`. Each voice file includes its first message and fits the 2,500-character limit. No edits were made to the human-owned ElevenLabs configuration document.

## Paid run configuration

Write the dollar limit, scope and time in the running builder's STATUS before enabling a paid run. The current integration setup and measured smoke tests are recorded in [`../docs/live-provider-setup.md`](../docs/live-provider-setup.md); historical offline benchmark evidence is in [`../BENCHMARK.md`](../BENCHMARK.md). Configure credentials only server-side:

- `ANTHROPIC_API_KEY`.
- `TYB_CHAT_BUDGET_USD`: a positive dollar cap for this ChatAgent process.

The key alone does not enable requests. The shared process budget reserves a conservative maximum cost before each model request and settles it from usage afterward. Automatic SDK retries are disabled. Restarting the process resets the in-memory budget; keep any remaining allocation within the approved shared cap. The rates come from the supplied master plan and need confirmation before a paid run if the provider changes them.

Keep live credentials absent from offline tests:

```sh
PYTHON_DOTENV_DISABLED=1 ANTHROPIC_API_KEY= ELEVENLABS_API_KEY= OPENAI_API_KEY= uv run pytest -q tests/agent
```

Tests inject an offline client. They exercise real SDK tool wrappers, edit confirmation, session isolation, bounded settings, prompt limits and numeric grounding. This proves the code path; live text smoke evidence is reported separately in the setup document. The human voice model comparison remains unmeasured.

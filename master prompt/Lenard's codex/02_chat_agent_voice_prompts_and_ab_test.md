# L02: Text chat agent, voice prompts and the voice A/B test (chat by G3 00:30 CEST; A/B test 01:30–02:00 CEST, after G4)

## 1. Outcome and user value

People can talk to the building by voice (ElevenLabs) or text (our chat) and get the same grounded behaviour: one clarifying question when needed, a one-line confirmation of what was understood, directions with landmarks, previews before changes, and honest "no route" answers. This carries the 25 interaction points and Aha 1/Aha 3.

## 2. Starting state

- The chat agent needs `spatial_query` (CONTRACTS §8) for questions like "what is above office 0.29"; describe when to use it in the `spatial_relations` and `areas` skills.
- Tool registry `server/tools.py` arrives from Manuel's codex around 00:00 CEST (M02); its tool names and arguments are frozen in CONTRACTS §8 and match `docs/elevenlabs-agent-config.md`.
- The ElevenLabs agents are created by a human (H4) from the config doc plus your prompt texts.
- Read: CONTRACTS §8 (tools, ToolResponse, contextual updates), §10 (session), §14; UX_REQUIREMENTS §1 J2–J7, §2; plan review §9 (the ten A/B utterances).

## 3. Scope and ownership

Own `agent/__init__.py`, `agent/chat.py`, `agent/prompts.py`, `agent/skills/{entities,routes_tours,areas,reachability,spatial_relations,edits_scenarios}.md`, `agent/voice_prompts/navigator.md`, `agent/voice_prompts/admin.md`, `tests/agent/`, the A/B result table (in your STATUS and, after a human confirms the file is committed, a new section in `docs/elevenlabs-agent-config.md`). Manuel's codex owns `/api/chat` wiring and the registry.

## 4. Implementation obligations

1. **Skills as prompt modules:** six short recipes (≤ 25 lines each): intent cues, required inputs, which tools, evidence to show, edge cases, output style. `agent/prompts.py` assembles them into the chat system prompt (cached) and into condensed voice prompts. They contain rules, not computation.
2. **`agent/chat.py`:** `class ChatAgent(registry, session_provider)` with `reply(session_id, message) -> {"reply", "tool_calls", "display"}`. Anthropic tool runner, `claude-sonnet-5-5`, `output_config={"effort": "low"}`, `fallbacks: "default"` with beta `server-side-fallback-2026-07-01`, `tool_choice` auto, ≤ 6 iterations per turn, history per session (in memory, keyed by `session_id`; append-only), session context as a short block in the user turn (position, profile, active tour) taken from the session provider, never inferred from old turns. Tools are generated from the registry's JSON schemas (`strict: true`). Each `ToolResponse` with `display` is returned so the UI can update.
3. **Behaviour rules** (both chat and voice prompts): short acknowledgement first in voice; landmarks before room numbers; exactly one clarifying question when `resolve` is ambiguous or a required argument is missing (list ≤ 4 options with floors); "Press 4" is never "Press 14"; say clearly when something does not exist or no route exists, with the reason; for wheelchair/pram/trolley set the profile and keep it; navigator gives at most three steps then waits for "next"; admin always calls `propose_edit`, describes the preview, waits for an explicit yes, then `commit_edit` exactly once; on a `building changed` contextual update the navigator announces the new route in one sentence.
4. **Voice prompts:** `agent/voice_prompts/navigator.md` and `admin.md` ready to paste into the ElevenLabs dashboard (English, ≤ 2,500 characters each, tool usage spelled with exact names), plus a first message for each agent. Give them to the H4 human and Manuel's codex.
5. **Tests** (stubbed client): the agent turns a canned tool error with candidates into one question; an edit is never committed without a "yes" turn; no fact appears in the reply that is not in a tool result (simple check: numbers in the reply ⊆ numbers in tool results).
6. **A/B test** (with a human speaker, ≤ 30 min, after G4): the ten utterances from plan review §9 (where is the 3D printer; five parts; without stairs; the press (ambiguous); next; coffee machine (absent); interruption; close the east lift; yes; route without solution) against Claude Sonnet 5.5, one ElevenLabs-hosted model (e.g. Qwen3.5) and one Gemini Flash model, all other settings equal. Record pass/fail per utterance and time to first word (stopwatch or ElevenLabs conversation log). Rule: keep Sonnet 5.5 unless another model passes more cases, or ties and is > 0.5 s faster; the navigator may switch alone if latency is its only problem.

## 5. Interfaces and fixtures

Consumes the registry (CONTRACTS §8); until M02 lands, write against a local stub that wraps `core` functions with the same names and ToolResponse shape (`agent/_stub_registry.py`, marked MOCK, deleted after M02).

## 6. Execution order

Skills + prompts (25 min) → ChatAgent on the stub with tests (35 min) → switch to the real registry, run five conversations against the dev factory building and paste transcripts in STATUS (20 min) → voice prompts to the human (10 min) → start L03 → A/B test with the human after G4, around 01:30 CEST (30 min).

## 7. Acceptance

- `POST /api/chat` (after Manuel's codex wires it) handles: "Where is the CNC mill?", "I need the filament, the torque wrench and the steel drum" (tour), "the press" (one question), "coffee machine" (none), "close the east lift" in an admin session (preview, waits), "yes" (one commit).
- Five transcripts in STATUS; A/B table with the decision; prompt texts in the repo.

## 8. Collaboration and Git

Branch `lenard/bench`. Merge window G3 (chat) and G5 (prompt updates). Do not edit `docs/elevenlabs-agent-config.md` while it still has uncommitted human edits; ask your human.

## 9. Completion report

SHA; transcripts; A/B results and decision; prompt versions; costs.

## 10. Blocked-work behaviour

No ElevenLabs access by 01:15 CEST: skip the A/B test, keep Sonnet 5.5 as the documented choice, and strengthen the text chat path (it is the judges' reproducible interaction path). No Anthropic credits: chat returns `not_available`; voice still works via ElevenLabs-billed LLM.

# Rewrite architecture

Status: requirements and proposals. Only the evaluator exists today.

## Confirmed direction

- Use Python for the backend and SQLite for storage.
- Use TypeScript, React and Tailwind for the later frontend. Its framework remains open.
- Establish data storage and imports first. Build the agent and its tools next. Add the web application later.
- Adopt an existing agent harness. Do not build a custom model/tool execution loop.
- Start with Claude Sonnet 5.5, selected through `BUILDING_AGENT_MODEL`. Write agent prompts in English.
- Start with read-only agent tools. Keep later write operations possible without implementing them now.

## Responsibilities

| Area | Owns | Must not own |
|---|---|---|
| Data access | Validated building storage, imports and read queries | Evaluation labels or language-model decisions |
| Building tools | Building search, geometric facts, route calculations and explicit domain failures | Conversation policy or provider-specific behavior |
| Agent harness | Model interaction, context, tool execution, validation, retries and run records | Independent copies of calculation logic |
| Evaluation | Question loading, agent invocation, scoring and submission output | Supplying gold answers or generator inputs to the agent |
| Web integration, later | HTTP transport and conversation delivery | A separate calculation implementation |

These are responsibilities, not separate deployments or a requirement for one package per row.
Use focused files and small interfaces as implementation needs become clear.

The building tools use Shapely, backed by GEOS, for planar geometry and NetworkX for graph operations.
Follow the route model in [README.md](README.md). Changing the geometric engine or its parameters
requires a check against that model.

## Shared tools, separate agent hosts

Keep one implementation of each building tool. Our harness calls it through Python registration.
An ElevenLabs managed agent can call the same implementation through a thin HTTP tool adapter.
FastAPI is the current candidate for that adapter.

ElevenLabs can own its conversational loop. Its requests need not pass through our own language model.
Our own agent remains the initial benchmark entry point and can also serve later text conversations.
Choose the user-facing conversation host when that feature starts.

Each adapter must preserve argument validation, units, entity identities, result meaning and failure behavior.
Provider-specific schema conversion belongs in the adapter. Do not promise identical conversations from
different hosts merely because their tools match.

## Context and data isolation

Pass the original question text to the agent with the allowed building context. Do not classify the
question, extract targets, guess constraints or solve part of it before the agent sees it. Do not supply
dataset `kind`, `skill`, `inputs` or `answer` fields as hints.

Question-independent import calculations are allowed. A room's area, spatial index or walking graph can
be derived from building data. Such data must remain tied to the source and calculation version. Do not
cache benchmark answers or question-specific plans as building facts.

The runtime storage and deployed agent environment exclude question files, gold answers and generator inputs.
The evaluator holds those separately and sends only the question and building reference. Tools provide
validated operations rather than unrestricted file access, SQL or code execution.

## Output and conversation

Structured output is the first proposal for the own agent's final result. The harness validates it and
can return validation errors to the model for repair. Schema validity does not prove numerical correctness.
Results must remain tied to tool calculations.

A small deterministic formatter is recommended for the benchmark's exact `Answer:` line. It converts a
validated result to the required text; it does not interpret the question or calculate an answer. Conversation
text and the benchmark line can use the same result. This output design is proposed, not implemented.

## Next implementation steps

1. Agree on the first data interface and implement validated SQLite import and read access.
2. Verify import fidelity, isolation and derived facts. Document the real commands in README.md.
3. Adopt the harness and connect the first useful tools. Run one full question through the real evaluator.
4. Expand tool coverage and evaluate on dev before adding the web application.

The database details are in [docs/db.md](docs/db.md). Harness and output requirements are in
[docs/agent.md](docs/agent.md). Do not implement future write tools, sessions or frontend features as prerequisites.

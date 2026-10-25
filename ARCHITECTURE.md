# Locora architecture

Status: the evaluator, the building database, nine building tools with the route model, their MCP server and
the benchmark agent exist. The agent answers all 138 dev questions. The benchmark submission is in `SUBMISSION/`.
The building API, JSON uploads, web application and 2D and 3D building views exist. Organizer rules and the submission format are in
[docs/challenge.md](docs/challenge.md).

## Confirmed direction

- Use Python for the backend and SQLite for storage.
- Use TypeScript, React and Tailwind for the later frontend. Its framework remains open.
- Establish data storage and imports first. Build the agent and its tools next. Add the web application later.
- Adopt an existing agent harness. Do not build a custom model/tool execution loop.
- Start with Claude Sonnet 5.5, selected through `BUILDING_AGENT_MODEL`. Write agent prompts in English.
- Start with read-only agent tools. Keep later write operations possible without implementing them now.
- Store derived room areas as `STORED` generated columns. See [docs/db.md](docs/db.md).
- Use PydanticAI as the agent harness. Serve the building tools from one MCP server.
- The agent returns structured output. A deterministic formatter writes the benchmark `Answer:` line.
- FastAPI serves stored buildings and routes read-only. A separate JSON upload route uses the shared validated
  importer. TypeScript building types are generated from its OpenAPI schema.
- The building views are a framework-free TypeScript package: SVG for 2D, three.js for 3D.
  See [docs/visualization.md](docs/visualization.md).

## Responsibilities

| Area | Owns | Must not own |
|---|---|---|
| Data access | Validated building storage, imports and read queries | Evaluation labels or language-model decisions |
| Building tools | Building search, geometric facts, route calculations and explicit domain failures | Conversation policy or provider-specific behavior |
| Agent harness | Model interaction, context, tool execution, validation, retries and run records | Independent copies of calculation logic |
| Evaluation | Question loading, agent invocation, scoring and submission output | Supplying gold answers or generator inputs to the agent |
| Building views | Read-only building API, scene derived from `building.json`, 2D and 3D drawing of routes and positions they receive | Route or position calculation |
| Web integration, later | HTTP transport and conversation delivery | A separate calculation implementation |

These are responsibilities, not separate deployments or a requirement for one package per row.
Use focused files and small interfaces as implementation needs become clear.

The building tools use Shapely, backed by GEOS, for planar geometry and NetworkX for graph operations.
Follow the route model in [docs/challenge-kit.md](docs/challenge-kit.md). Changing the geometric engine or its parameters
requires a check against that model.

## Shared tools, separate agent hosts

Keep one implementation of each building tool and publish it through one MCP server.

- Our benchmark agent (PydanticAI) uses the server in the same process. No network or token is involved.
- The ElevenLabs conversational agent connects to the same server over Streamable HTTP. Because that endpoint is
  reachable from the internet, it requires a secret bearer token. ElevenLabs drops tools whose parameters contain
  objects, so `voice_agent` gives the route tools flat condition parameters. See [docs/voice.md](docs/voice.md).

ElevenLabs owns its conversational loop. Its requests do not pass through our own agent. Our agent is the
benchmark entry point. Same tools do not guarantee the same answer quality, so each host needs its own
end-to-end checks.

The MCP layer only translates. Argument validation, units, entity identities, result meaning and failure
behavior belong to the tool implementation, so both hosts get the same behavior.

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

Our agent's final result is structured output with a small set of answer shapes. The harness validates it and
returns validation errors to the model for repair. A deterministic formatter turns the validated result into the
benchmark `Answer:` line. It does not interpret the question or calculate anything. Schema validity does not
prove numerical correctness; values must come from tool results. Details are in [docs/agent.md](docs/agent.md).

## Next implementation steps

1. Done: validated SQLite import and read-back, with stored room areas.
2. Done: six lookup and spatial tools, checked against train and dev answers. See [docs/tools.md](docs/tools.md).
3. Done: PydanticAI agent with the MCP server, answer shapes and formatter. On dev it answers all 97 questions
   its tools cover. See [docs/agent.md](docs/agent.md).
4. Done: route tools. The agent answers all 138 dev questions.
5. Done: `SUBMISSION/` with `BENCHMARK.md`, the test answers in `answers.json` and the `run_benchmark` command
   for new buildings.

The database details are in [docs/db.md](docs/db.md). Harness and output requirements are in
[docs/agent.md](docs/agent.md). Do not implement future write tools, sessions or frontend features as prerequisites.

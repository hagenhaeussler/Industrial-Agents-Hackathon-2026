# Agent and tools

Status: decisions recorded. No harness or building tools are implemented yet.

## Harness and configuration

Adopt an existing harness. It must manage model/tool turns, validated tool arguments, conversation context,
structured results, repair attempts, cancellation and useful run records. Do not write a custom execution loop.

Selected: **PydanticAI**. It is a plain Python library and independent of the model provider. Its `MCPToolset`
connects to MCP servers in the same process, over stdio or over Streamable HTTP. It validates structured output
and returns errors to the model for repair. Offline tests can replace the model with its test models, so they
make no paid calls.

Considered: the Claude Agent SDK. It has strong MCP and structured-output support, but it runs the Claude Code
harness with built-in file and shell tools that we would have to disable for data isolation. It also supports only
Claude models and stores sessions as files.

Write prompts and tool descriptions in English. Start with Sonnet 5.5 through the direct Anthropic provider:

```dotenv
BUILDING_AGENT_MODEL=anthropic:claude-sonnet-5-5
ANTHROPIC_API_KEY=
```

`BUILDING_AGENT_MODEL` is the single model selection setting. The provider-qualified value permits a later
model change without editing prompts or domain logic. The key remains server-side. This planned setting is
recorded in `.env.example`; no runtime consumes it yet.

Do not introduce small fixed tool-call caps that cut off valid reasoning. PydanticAI's `UsageLimits` allows
50 model requests per run by default. Raise that limit deliberately. Use a generous `cost_limit` per run as the
provider budget, so normal runs never stop midway. A stopped run or exhausted output repair returns an explicit
failure result, never a guessed answer. The budget amounts are agreed before the first paid run.

For Sonnet 5.5, do not send `temperature`, `top_p`, `top_k`, forced `tool_choice` or `thinking: disabled`.
Any effort setting belongs in the provider's supported output configuration.

## Freedom with guidance

Give the agent the original question and allowed building context. Let it choose and combine tools. Do not
route requests through keyword templates, infer targets or calculate a partial answer before the model sees
the question. Do not pass dataset kinds, skills, gold answers or generator inputs as hints.

Guide the agent with clear tool descriptions, units, result types, examples and failure handling. Use ordinary
versioned prompt files initially. A separate skills mechanism is not required.

Each numerical claim must come from tool results. Keep a record of the relevant tool calls and computed values
so failures can be inspected. Do not ask the model to provide hidden reasoning as a substitute for that record.

Clear benchmark questions should proceed directly. For live conversations, ask for a missing location,
identity or constraint when it changes the result. Do not select an arbitrary room from ambiguous matches.

## Tools and host adapters

Tools should support useful operations over buildings: finding entities, filtering facts, computing geometric
relationships and calculating routes under explicit constraints. Design their exact interfaces after the data
interface is established. Return typed results with units, stable entity IDs and explicit failure states.

Keep the calculation implementation independent of PydanticAI, Anthropic and ElevenLabs. Publish the tools
through one MCP server, for example built with FastMCP:

- Our agent passes the server instance to `MCPToolset`. It runs in the same process without a token.
- ElevenLabs connects to the server's Streamable HTTP endpoint. MCP must be enabled once in the ElevenLabs
  workspace. The endpoint is public, so the server rejects requests without the secret bearer token from
  `BUILDING_MCP_TOKEN`. The same token is stored as a secret in the ElevenLabs tool settings.

ElevenLabs owns the conversational loop and calls the tools directly. It does not call our own agent. Check its
timeout and schema constraints when the HTTP endpoint is built.

Start with read-only operations. Keep writes possible through the same domain rules later, with explicit
validation and authority. Do not add placeholder write tools or allow raw SQL, shell or filesystem access.

## Structured output and formatting

Our agent returns structured output. A deterministic formatter writes the benchmark `Answer:` line from it.
These answer shapes apply only to benchmark submissions. The ElevenLabs conversational agent answers freely.
The nine benchmark kinds need only three answer shapes, plus failure:

| Shape | Fields | `Answer:` line | Kinds |
|---|---|---|---|
| Number | value, unit | `Answer: 214.7` | `floor_area_total`, `errand`, `straight_line_3d` |
| Count | integer | `Answer: 7` | `wide_delivery_count`, `step_free_reachable_count`, `shared_walls_count`, `what_if_door` |
| Room | room ref, optional area | `Answer: N5325, 79.48 m²` | `largest_room` (with area), `room_stacked` |
| Failure | reason | A line without a number | Any stopped or unanswerable run |

Every shape also has an `explanation` field for a short natural-language answer. The agent picks the shape from
the answer instruction in the question text, such as "Finish with a line 'Answer: <number>'". The dataset `kind`
is not passed to the agent. The formatter does not parse the question, choose a result or calculate a value.
It writes exactly one number for numbers and counts, and the room ref first for rooms.

What each part catches:

- A wrong form, such as `"area_m2": "about 80"`, fails validation. The model repairs it in one more step.
- A wrong value in the right form, such as the runner-up room, passes. Only correct tools and dev evaluation
  catch it.
- A failure stays a failure. The formatter never turns it into a plausible answer.

Exact field names, rounding and the repair limit are decided when the harness is built. Test the formatter
against `benchmark/score.py`.

## Evaluation

The evaluator calls the agent with a building reference and question text only. Expected answers remain with
the evaluator and are used after the agent replies. Exclude evaluation files from runtime storage and deployment.

Test tool behavior and failures, data isolation, model selection, structured-result validation and output
formatting. Offline harness tests can check execution and failure handling with a test model. They do not prove
live language-model quality. Use separately budgeted dev runs for end-to-end answer quality before test submission.

## References

- [PydanticAI agent](https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md): execution and usage controls.
- [PydanticAI output](https://github.com/pydantic/pydantic-ai/blob/main/docs/output.md): structured output and validation.
- [Anthropic models](https://platform.claude.com/docs/en/about-claude/models/overview): initial model identity.
- [PydanticAI MCP client](https://ai.pydantic.dev/mcp/client/): `MCPToolset` and transports.
- [PydanticAI usage limits](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/): default request limit and `cost_limit`.
- [ElevenLabs MCP](https://elevenlabs.io/docs/eleven-agents/customization/tools/mcp): custom MCP servers for agents.

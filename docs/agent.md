# Agent and tools

Status: requirements and proposals. No harness or building tools are implemented yet.

## Harness and configuration

Adopt an existing harness. It must manage model/tool turns, validated tool arguments, conversation context,
structured results, repair attempts, cancellation and useful run records. Do not write a custom execution loop.
PydanticAI is the first candidate. Check these requirements before adopting it.

Write prompts and tool descriptions in English. Start with Sonnet 5.5 through the direct Anthropic provider:

```dotenv
BUILDING_AGENT_MODEL=anthropic:claude-sonnet-5-5
ANTHROPIC_API_KEY=
```

`BUILDING_AGENT_MODEL` is the single model selection setting. The provider-qualified value permits a later
model change without editing prompts or domain logic. The key remains server-side. This planned setting is
recorded in `.env.example`; no runtime consumes it yet.

Do not introduce small fixed tool-call caps that cut off valid reasoning. Inspect and consciously configure
the harness's defaults. Use an agreed provider budget and cancellation/time controls to handle runaway runs.
A stop or exhausted output-repair policy must return an explicit incomplete/error result, never a guessed
answer. Validation retries and tool-call limits are separate controls. Exact policies remain to be chosen.

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

Keep the calculation implementation independent of PydanticAI, Anthropic and ElevenLabs. Register the same
Python operations with our harness and later expose them through authenticated HTTP tools for ElevenLabs.
An ElevenLabs managed agent can own the conversational loop and call these tools directly. It need not call
our own agent first. Check its schema, timeout and authentication constraints when building that adapter.

Start with read-only operations. Keep writes possible through the same domain rules later, with explicit
validation and authority. Do not add placeholder write tools or allow raw SQL, shell or filesystem access.

## Structured output and formatting

Structured output is the first option to test for our agent's final result. A candidate result distinguishes a
numeric answer, a room answer and an explicit clarification/failure. Numbers need their units; room answers
need stable references and an area when relevant. The exact schema is not decided yet.

The harness should validate the schema and feed validation errors back for repair. Provider-native schema
output and tool-based structured output are both options. Verify their support with the chosen model and
existing function tools. A valid schema cannot establish that a number is correct or supported by a tool.

Recommendation: retain a small deterministic formatter for the benchmark. It takes a validated result and
writes the exact `Answer:` line. It must not parse the question, choose a result or calculate a value. Numeric
answer lines contain one number; room lines identify the room before alternatives and include area when needed.

This keeps the submission contract independent of conversation wording and agent host. A conversational
response can include explanations or a clarification request while using the same tools and computed facts.
The formatter must reject incomplete results instead of converting a failure to a plausible answer.

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
- [ElevenLabs webhook tools](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools): shared backend access.

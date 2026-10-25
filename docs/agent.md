# Locora agent and tools

Status: the agent uses PydanticAI, the MCP server over the six building tools in [tools.md](tools.md), the
answer shapes and the formatter. It answers all 138 dev questions correctly.

## Measured results

Dev run `dev-6` on 25 Oct 2026, Sonnet 5.5, effort `medium`, 10 questions at a time, with all nine tools and the
route answer shape:

| Kind | Correct |
|---|---|
| `errand` | 19 / 19 |
| `floor_area_total` | 31 / 31 |
| `largest_room` | 20 / 20 |
| `room_stacked` | 9 / 9 |
| `shared_walls_count` | 24 / 24 |
| `step_free_reachable_count` | 1 / 1 |
| `straight_line_3d` | 13 / 13 |
| `what_if_door` | 2 / 2 |
| `wide_delivery_count` | 19 / 19 |
| Total | 138 / 138 |

The run took 66 s and cost $1.27, about $0.01 per question. The earlier run `dev-5`, before the route answer
shape, also had 138 / 138 in 72 s for $1.42. In `dev-6`, 94% of input tokens were cache reads. Before the route
tools existed (`dev-4`), the agent answered the 41 route questions with explicit failures and no guesses.

Other runs on the same day:

| Run | Result | Time | Cost |
|---|---|---|---|
| Test set, 145 questions, written to `SUBMISSION/answers.json` | 145 answered, 0 stopped runs | 68 s | $1.38 |
| An earlier test run | Same answer on 144 of 145 questions | 68 s | $1.50 |
| Dev warm-up route questions on 5 buildings, through `run_benchmark` | 30 / 30 with the exact space path and length | about 1 min | $0.74 |
| Dev warm-up locate and count questions on 10 buildings, through `run_benchmark` | 26 / 26, with the exact item ID in all 20 locate answers | about 1 min | $0.15 |
| `dev-7`, after the item ID and the production bay rule | 138 / 138 | 70 s | $1.47 |

In the one test difference, the earlier run looked for the nearest coat rack on the start floor only. The
submitted run searched the whole building, as the question and the errand definition require.

Fixes found in earlier dev runs:

- The model looped on one identical tool call until the request limit stopped the run. A repeat guard now refuses
  the third identical call and tells the model to use the earlier result or report a failure.
- The model returned a room's area as a number when the question asked which room and how big. Answers are now
  output tools (`answer_room`, `answer_number`, `answer_count`, `report_failure`), and the instructions say that
  "which space" questions use `answer_room`.
- The model recounted listed neighbours and subtracted an excluded corridor twice. `shared_walls` now returns
  separate `counted` and `not_counted` lists. Each answer shape puts the explanation before the value.

## Running it

```bash
uv run python -m building_agent.batch data/dev --workers 10 --name dev-run
uv run python -m benchmark.evaluate data/dev --agent building_agent.agent:answer --per-kind 1
```

`building_agent.batch` answers 10 questions at a time and scores with the official scorer after all replies are
in. It writes the same replies file and optional submission CSV as `benchmark.evaluate`, plus total cost, tokens
and cache use. The official evaluator stays the reference and runs one question at a time.

Instructions and tool definitions are cache breakpoints, because they are the same for every question. Parallel
questions read them from the cache. A third, automatic breakpoint caches the growing history within one run.

`answer(building_directory, question_text)` in `building_agent/agent.py` imports the building into
`buildings.sqlite3` if needed, starts an MCP server bound to that one building and runs the agent on the question
text. Each run writes a record with the tool calls, token use, cost and reply to `agent_output/runs/`. The
instructions are in `building_agent/instructions.md`; their hash is stored in each record as the prompt version.

| Setting | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Provider key, in `.env` only |
| `BUILDING_AGENT_MODEL` | `anthropic:claude-sonnet-5-5` | Model |
| `BUILDING_AGENT_EFFORT` | `medium` | Effort level sent in the provider's output configuration |
| `BUILDING_AGENT_COST_LIMIT_USD` | `1.00` | Cost limit per question. Above it the run stops with a failure reply. |
| `BUILDING_AGENT_REQUEST_LIMIT` | `60` | Model requests per question |
| `BUILDING_DATABASE` | `buildings.sqlite3` | Database file |
| `BUILDING_AGENT_RUNS` | `agent_output/runs` | Run records |

Without a key, or after any error or limit, the reply says that the run stopped and why. It has no `Answer:`
line.

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
model change without editing prompts or domain logic. The key remains server-side.

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

The prompt states the README definitions, such as "directly above" as the largest overlap, and tells the
agent which tool parameter expresses them, such as the number of floors for stacking. It describes concepts,
not question phrasings. Story details in a question, such as a leaking washing machine, are context only.
The benchmark answer follows the definition. [tools.md](tools.md) shows why.

Clear benchmark questions should proceed directly. For live conversations, ask for a missing location,
identity or constraint when it changes the result. Do not select an arbitrary room from ambiguous matches.

## Tools and host adapters

The tool list, its rules and the checked definitions are in [tools.md](tools.md). Route answers in the hidden
evaluation are scored by their space sequence, see [challenge.md](challenge.md).

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
The nine benchmark kinds need three answer shapes. Route questions on new buildings add a fourth. Failure covers
the rest:

| Shape | Fields | `Answer:` line | Kinds |
|---|---|---|---|
| Number | value, unit | `Answer: 214.7` | `floor_area_total`, `errand`, `straight_line_3d` |
| Count | integer | `Answer: 7` | `wide_delivery_count`, `step_free_reachable_count`, `shared_walls_count`, `what_if_door` |
| Room | room ref, optional area | `Answer: N5325, 79.48 m²` | `largest_room` (with area), `room_stacked` |
| Room with item | room, item ID | `Answer: Makerspace 0.08 (Ground floor)` | Warm-up `locate`: "Where is the laser cutter?" |
| Route | stops, conditions, leg conditions | `Answer: 12.99 m`, after a `Route:` line | Route questions on new buildings |
| Failure | reason | No `Answer:` line | Any stopped or unanswerable run |

The route shape holds only the stops and conditions the agent passed to `route`. The formatter calculates the
route again from them, so the space sequence and the length always come from the route tool. If no route exists,
the line is `Answer: No route exists under these rules.` An output validator sends unknown space or element IDs
back to the model for repair.

A room answer can carry the `asset_id` of an item the question asks for. The validator checks that the item
exists and is in the answered space. The `Answer:` line then names the room and its floor instead of its area,
and the answers.json entry also holds the item ID, name and position.

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

## Submission and run_benchmark

`uv run run_benchmark <building_dir> <questions.json> <answers.json>` runs the agent on every question about one
building, 10 at a time, and writes `answers.json`. It imports the building into a new temporary database, so a
stored building with the same ID and other content cannot block the import. `building_agent.batch` writes the
same file with `--answers-json`. The format and the commands are in [SUBMISSION/BENCHMARK.md](../SUBMISSION/BENCHMARK.md).

Each `answers.json` entry has the full reply, the text of its `Answer:` line and the answer as data. For routes
the data holds the space IDs in walking order, the element IDs and the length. The organizers did not publish a
schema, so the entry holds both the text and the IDs.

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

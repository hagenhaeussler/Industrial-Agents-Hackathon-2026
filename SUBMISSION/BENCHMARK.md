# Benchmark

This file explains how to run our agent on a building and reproduce `answers.json`.

The agent answers questions about one building. It uses Claude Sonnet 5.5 through PydanticAI. It sees only the
question text and nine calculation tools over the building data. The tools calculate every area, count,
distance and route. The model chooses the tools and their inputs. The program, not the model, writes the final
`Answer:` line and the route from the tool results.

## Setup

You need Python 3.12 or newer, [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
uv sync
cp .env.example .env    # then set ANTHROPIC_API_KEY in .env, or export it in the shell
```

## Run on a new building

```bash
uv run run_benchmark <building_dir> <questions.json> <answers.json>
```

- `<building_dir>` holds `building.json` in the kit format.
- `<questions.json>` holds one entry per question with `id`, the question in `question` or `text`, and optional
  `constraints`. A JSON list, an object with a `questions` list, an object keyed by question id, and JSON Lines
  all work. Constraints are added to the question text.
- `<answers.json>` is written. It holds one entry per question, in the order of the questions file.

The command answers 10 questions at a time (`--workers` changes this) and needs no manual step. It imports the
building into a new temporary database. At the end it prints the run time, token use and cost. In our runs one
question cost about $0.01, and a route question about $0.025.

## Test-set answers

`SUBMISSION/answers.json` holds our answers to the 145 test questions in `data/test`. This command wrote it:

```bash
uv run python -m building_agent.batch data/test --workers 10 --name test \
  --answers-json SUBMISSION/answers.json --submission-csv results/test_answers.csv
```

`results/test_answers.csv` holds the same replies in the CSV format of the kit README, section 6.

Room answers later got their room name and floor in `result`, read from the building data. No reply or `Answer:`
line changed.

## Format of answers.json

A JSON list. Each entry has these fields:

| Field | Content |
|---|---|
| `id` | The question id |
| `question` | The question text the agent got |
| `answer` | The text after the final `Answer:` line, or `null` if the agent could not answer reliably |
| `reply` | The agent's full reply, with a short explanation and the `Answer:` line |
| `result` | The answer as data. Its fields depend on `type`, see below. |

| `type` | Further fields |
|---|---|
| `number` | `value`, `unit` |
| `count` | `value` |
| `space` | `space_id`, `space_name`, `floor_level`, `floor_name`, `area_m2`. For an item the question asks for, also `asset_id`, `asset_name` and `position`. |
| `route` | `reachable`, `space_path` (space ids in walking order), `element_path` (door, opening, stair and lift ids in order), `length_m` (`null` if no route exists) |
| `failure` | `reason` |

A route entry looks like this:

```json
{
  "id": "osm-way27326387-Q02",
  "question": "How do I get from Generic room K03 (Basement 2) to Generic room K19B (Basement 2)?",
  "answer": "12.99 m",
  "reply": "Shortest route between the two rooms on Basement 2.\nRoute: Generic room K03 (Basement 2) -> Corridor K22 (Basement 2) -> Generic room K19A (Basement 2) -> Generic room K19B (Basement 2)\nAnswer: 12.99 m",
  "result": {
    "type": "route",
    "reachable": true,
    "space_path": ["osm-way27326387-F-2-S021", "osm-way27326387-F-2-S008", "osm-way27326387-F-2-S005", "osm-way27326387-F-2-S019"],
    "element_path": ["osm-way27326387-F-2-O0018", "osm-way27326387-F-2-O0020", "osm-way27326387-F-2-O0010"],
    "length_m": 12.99
  }
}
```

If no route exists under the question's rules, `reachable` is `false`, `space_path` is empty and the answer is
"No route exists under these rules."

## Our results

Measured on 25 Oct 2026 with Claude Sonnet 5.5, effort `medium`:

| Run | Result | Time | Cost |
|---|---|---|---|
| Dev set, 138 questions with known answers | 138 / 138 correct | 70 s | $1.47 |
| Route questions from the dev warm-up set, run with `run_benchmark` on 5 buildings | 30 / 30 with the exact space path and length | about 1 min | $0.74 |
| Warm-up locate and count questions from 10 dev buildings, run with `run_benchmark` | 26 / 26, with the exact item ID in all 20 locate answers | about 1 min | $0.15 |
| Test set, 145 questions | 145 / 145 answered, 0 stopped runs; no known answers | 68 s | $1.38 |

The tools give the same result every time. The model can choose differently between runs, so a repeated run can
differ on single questions. An earlier test run gave the same answer on 144 of 145 questions. In the one
difference the earlier run looked for the nearest item on the start floor only. The submitted run searched the
whole building, as the question asks.

## Settings

All settings are optional environment variables. `.env.example` lists them.

| Setting | Default |
|---|---|
| `BUILDING_AGENT_MODEL` | `anthropic:claude-sonnet-5-5` |
| `BUILDING_AGENT_EFFORT` | `medium` |
| `BUILDING_AGENT_COST_LIMIT_USD` | `1.00` per question |
| `BUILDING_AGENT_REQUEST_LIMIT` | `60` model requests per question |

A question that reaches a limit gets a reply that says why the run stopped. That reply has no `Answer:` line.

## Checks

```bash
uv run python -m unittest discover -s tests
```

The tests make no paid calls. They check the tools against the train and dev answers and the agent with test
models. More detail is in [docs/agent.md](../docs/agent.md) and [docs/tools.md](../docs/tools.md).

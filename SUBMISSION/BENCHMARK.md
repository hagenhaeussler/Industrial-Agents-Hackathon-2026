# Benchmark

Requires Python 3.12+, uv, and an Anthropic API key. Run from the repository root.

## Setup

```bash
uv sync --locked
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env`. The default model is Claude Sonnet 5.5.

## Run jury questions

```bash
uv run run_benchmark <building_dir> <questions.json> <answers.json>
```

- `<building_dir>` contains the jury's `building.json`.
- `<questions.json>` contains question objects with `id` or `question_id`, `question` or `text`, and optional
  `constraints`. JSON lists and JSON Lines are accepted.
- `<answers.json>` is the output file. Run once per building and question set. Add `--workers 1` to run sequentially.

Output is a JSON list with exactly `question_id` and `answer` per entry. Route IDs and length are included in
`answer` text. Failed answers are `null`; details are saved in `agent_output/runs/`.

## Reproduce the public test submission

```bash
uv run python -m building_agent.batch data/test --name test --answers-json SUBMISSION/answers.json
```

Both commands write the same JSON format directly. See [agent documentation](../docs/agent.md) for settings,
checks, and implementation details.

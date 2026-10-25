# Organizer information

Messages from the Synera track lead (Bhushan Kotnis) and the event organizer (Sid) in the hackathon channel,
24–25 Oct 2026. They add to the [kit README](challenge-kit.md). Where they differ from the README, these messages are newer.

## Deadline

On Saturday at 23:37, Sid wrote that the deadline is about 14 hours away, so around midday on Sunday 25 Oct.
The exact time is not confirmed. Clocks went back one hour at 03:00 on Sunday.

## Submission

The benchmark part is worth 55 points. The repository needs a folder `SUBMISSION` with exactly two files:

| File | Content |
|---|---|
| `SUBMISSION/BENCHMARK.md` | How to run the system and reproduce the answers |
| `SUBMISSION/answers.json` | A JSON list of dictionaries with `question_id` and `answer`. |

Spelling and capitalization must match exactly, or the benchmark cannot be graded. The reference image shows
the folder `SUBMISSION` at the repository root with `BENCHMARK.md` (capitals) and `answers.json` (lowercase).

On 25 Oct at 11:16, Bhushan Kotnis confirmed: "The submitted JSON file should be a list of dictionaries with
keys {question_id, answer}." Each submission entry therefore has exactly these two fields.

The README describes the CSV for the 145 test questions. The challenge brief PDF (page 3, "Sunday benchmark")
describes the Sunday run:

- Input: a new building in the usual format and `questions.json`, one entry per question with id, text and
  optional constraints such as step-free.
- Command: one command documented in `BENCHMARK.md`, for example
  `run_benchmark <building_dir> <questions.json> <answers.json>`, with no manual steps.
- Output: `answers.json`, one entry per question id with the located item or room id, the route as an ordered
  list of node ids and the route length in metres.
- The brief promised a schema and an example answer file in the data folder. They were not added before the
  format confirmation above.

Our decision: `SUBMISSION/answers.json` holds the 145 test answers. Both benchmark commands write the same
two-field format for jury test sets. `question_id` identifies the question. `answer` is text, or `null` when the
agent cannot answer reliably. For routes, that text includes ordered space and element IDs, reachability, and
length. For locations it includes the space ID and, when relevant, the item ID. It keeps the final `Answer:`
line for these detailed answers. Plain numbers and counts keep the existing final answer text.

Full replies and structured results also remain in the run records. The kit CSV remains in
`results/test_answers.csv`. Jury setup and commands are in
[SUBMISSION/BENCHMARK.md](../SUBMISSION/BENCHMARK.md). The outer JSON fields are confirmed by the
organizer. Our answer text encoding has not been checked against a private jury parser.

The judges add their own Anthropic key and run the system. A `run_benchmark` script for the hidden building
evaluation is allowed. The test-set answers must also be committed to the repository.

The remaining 45 points come from a form:

- The GitHub repository link.
- A demo video of at most 2 minutes, on YouTube or Luma. A suggested split: 60 seconds of motivation and demo,
  60 seconds of architecture and technical details.
- A short technical explanation of the solution.

UI and UX are judged. A good design reduces cognitive load. See
[Laws of UX: reducing cognitive load](https://lawsofux.com/articles/2015/design-principles-for-reducing-cognitive-load/).

## How route answers are scored

This applies to route questions in the automatic check on unseen buildings.

- The answer is the ordered list of spaces the route passes through.
- Each step must go through a real door, opening, stair or lift, and the route rules must hold.
- The judges measure the route with their own distance rule. Our distance numbers do not affect the score.
- Score = best possible length / our length. Within 1% of the best gives full marks. An invalid route scores 0.
- If no route exists under the rules, the correct answer says so.

The route tools must therefore return the space sequence, not only a length.

## Route rules

The building model and distance rule match README section 3:

- Walking distance is measured inside each space from door to door, about 15 cm off the walls, round corners.
- Stairs count 2 m per metre climbed. A lift counts 15 m plus 1 m per metre climbed.
- Furniture and machines are not obstacles. A route to an item ends in the room or bay that holds it.

Rules for some questions:

| Rule | Meaning |
|---|---|
| Without stairs | Lifts, ramps and doors only |
| Forklift | Forklift aisles and openings 3 m or wider only. Pedestrian walkways do not count. |
| Closed or blocked | Closed areas must be avoided |
| Production bays | A factory production bay can be a destination, but a route must not pass through it |

The forklift and production bay rules are not in the README, and no train or dev question uses them. In the 26
factory buildings, forklift aisles are corridors named "Main aisle". Production bays are spaces of type `hall`
with room types such as `production_zone`. Hall openings are 12 m or wider, factory entrances 1.8 m to 5 m and
doors at most 1.6 m. The route tools must still confirm this mapping.

Our decision: a forklift needs openings at least 3 m wide, and that is its only rule. Every opening of 3 m or
more joins halls, main aisles or the outside, so the width rule also keeps it off pedestrian walkways. The
production bay rule applies only when a question states it, and "production bay" means room type
`production_zone`. Before this rule, the model blocked production zones on its own in some forklift questions and
not in others, so the same question got different routes.

# Route scoring specifications — Synera challenge clarification

- **Challenge:** Track 01, “Talk to Your Building” — Industrial Agents Hackathon 2026.
- **Saved:** 24 October 2026.
- **Source:** Challenge announcement supplied in chat. The original author, posting time and message link were not supplied.
- **Editorial note:** The announcement's wording is preserved below; only Markdown headings, bullet markers and spacing have been added.

Hi all, a quick note on how route answers are scored in the automatic check, so you know what to aim for.

## How we model a building

- Every building is a set of spaces (rooms, corridors, aisles, stairwells, lifts) joined by doors, openings, stairs and lifts.
- Walking distance is measured inside each space, from door to door, staying about 15 cm off the walls. Paths go around corners, never through walls [unless the user is a Jedi]
- Stairs count as 2 m of walking per metre climbed. A lift counts as 15 m (waiting and doors) plus 1 m per metre of height.
- Furniture, equipment and machines are not treated as obstacles. Distances use the room and aisle outlines only.
- A route to a machine or other item ends in the room or bay that holds it, not at its exact position.

## Rules that apply to some questions

- Without stairs: lifts, ramps and doors only.
- Forklift: forklift aisles and openings only (3 m or wider). Pedestrian walkways don't count.
- Closed or blocked areas must be avoided.
- Factory production bays are destinations. You can drive into one to deliver, but not through one as a shortcut.
- If no route exists under the rules (e.g. upstairs without stairs and no lift), the correct answer is to say so.

## How your answer is scored

- Give your route as the ordered list of spaces you pass through.
- We check that each step goes through a real door, opening, stair or lift, and that the rules above hold.
- We then measure your route with our distance rule above. Your own distance numbers don't affect the score; what counts is picking the right sequence of spaces.
- Score = best possible length ÷ your length. Within 1% of the best counts as full marks. An invalid route scores 0.

Questions? Ask any of the Synera folks on site or in the channel.


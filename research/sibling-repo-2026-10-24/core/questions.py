"""Grounded parser for the nine published English benchmark question templates.

This is deliberately not a general natural-language agent. Unknown phrasing and
ambiguous names raise MapError; an LLM can instead call SpatialCore.solve directly.
"""

import re
from pathlib import Path

from core.spatial import SpatialCore
from starter_agent.building_map import MapError


def parse_question(core: SpatialCore, question: str) -> tuple[str, dict]:
    def floor(fragment):
        matches = re.findall(r"\bon the (ground floor|floor -?\d+|basement \d+)\b", fragment, re.I)
        if not matches:
            raise MapError("No target floor in question.")
        text = matches[-1].lower()
        level = 0 if text == "ground floor" else int(re.search(r"-?\d+", text)[0])
        if text.startswith("basement"):
            level = -level
        matches = [f["id"] for f in core.floors.values() if f["level"] == level]
        if len(matches) != 1:
            raise MapError(f"Unknown or ambiguous floor: {text}")
        return matches[0]

    def entity(fragment):
        # Full rendered labels disambiguate identical room names on different floors.
        fragment = fragment.strip()
        matches = [s["id"] for s in core.spaces.values()
                   if fragment.casefold() == f"{s['name']} ({core.floor_name(s['floor_id'])})".casefold()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise MapError(f"Ambiguous room label: {fragment}; candidates: {', '.join(matches)}")
        return core.resolve_space(fragment)

    def room_type(fragment):
        types = {s["room_type"] for s in core.spaces.values()}
        matches = [t for t in types if t.replace("_", " ").casefold() == fragment.strip().casefold()]
        if len(matches) != 1:
            raise MapError(f"Unknown room type: {fragment}")
        return matches[0]

    def entity_pair(fragment):
        pairs = set()
        errors = []
        for separator in re.finditer(" and ", fragment):
            try:
                pairs.add((entity(fragment[:separator.start()]), entity(fragment[separator.end():])))
            except MapError as error:
                errors.append(error)
        if len(pairs) == 1:
            return next(iter(pairs))
        if not pairs:
            for error in errors:
                if "Ambiguous" in str(error):
                    raise error
            raise MapError("No pair of known room labels could be resolved.")
        raise MapError("Ambiguous room label pair; use explicit space IDs.")

    def asset_type(fragment):
        normal = re.sub(r"[\s-]+", "_", fragment.strip().casefold())
        types = {a["type"] for a in core.assets.values()}
        if normal not in types:
            raise MapError(f"Unknown asset type: {fragment}")
        return normal

    text = question.split(" Finish with a line", 1)[0].strip()
    match = re.fullmatch(r"Which is the largest (.+?) on the .+?, and how big is it in m²\?", text)
    if match:
        return "largest_room", {"floor_id": floor(text), "room_type": room_type(match[1])}
    match = re.fullmatch(r"Facilities want the total floor area of every (.+?) on the .+? added together\. How many square metres is that\?", text)
    if match:
        return "floor_area_total", {"floor_id": floor(text), "room_type": room_type(match[1])}
    match = re.fullmatch(r"I'm in (.+?)\. I need to grab an? (.+?) from the room that has one closest to me, then carry it to the largest (.+?) on the .+?\. I can carry it on the stairs\. How far will I walk in total, in metres\?", text)
    if match:
        return "errand", {"start": entity(match[1]), "asset_type": asset_type(match[2]),
                          "floor_id": floor(text), "room_type": room_type(match[3])}
    match = re.fullmatch(r"We're soundproofing (.+?)\. How many other rooms on that floor share a wall with it\? Count every room whose wall runs along it for at least 1 m, with or without a door between them; corridors, stairwells and lifts don't count\.", text)
    if match:
        return "shared_walls_count", {"start": entity(match[1])}
    match = re.fullmatch(r"I'm moving a ([\d.]+) m wide .+?\. It can't go on stairs or steps \(lifts are fine\), and every door it passes through must be at least ([\d.]+) m wide\. It arrives through the entrance into (.+?)\. Into how many rooms on the .+? can it be delivered\?", text)
    if match:
        if float(match[1]) != float(match[2]):
            raise MapError("Conflicting delivery widths.")
        return "wide_delivery_count", {"start": entity(match[3]), "floor_id": floor(text),
                                      "min_width": float(match[1])}
    match = re.fullmatch(r"(.+?) is out of service\. A wheelchair user comes in through the entrance into (.+?)\. How many rooms on the .+? can they still reach\?", text)
    if match:
        return "step_free_reachable_count", {"closed": core.find_element(match[1]),
                                             "start": entity(match[2]), "floor_id": floor(text)}
    match = re.fullmatch(r"We're planning a wireless sensor link between (.+?) and (.+?)\. What is the straight-line distance in metres between the centres of the two rooms \(each room's floor-plan centroid, at its floor's elevation\)\?", text)
    if match:
        first, second = entity_pair(match[1] + " and " + match[2])
        return "straight_line_3d", {"first": first, "second": second}
    match = re.fullmatch(r"There's water dripping from the ceiling in (.+?)\. Which room is directly above it\?", text)
    if match:
        return "room_stacked", {"start": entity(match[1]), "direction": "above"}
    match = re.fullmatch(r"A washing machine is leaking onto the floor of (.+?)\. Which room directly below it will the water reach\?", text)
    if match:
        return "room_stacked", {"start": entity(match[1]), "direction": "below"}
    match = re.fullmatch(r"What if we add a door between (.+?) and (.+?), in the middle of the wall they share\? How many rooms on the .+? would then have a shorter walk out of the building, to their nearest entrance, by more than 1 m\?", text)
    if match:
        first, second = entity_pair(match[1] + " and " + match[2])
        return "what_if_door", {"first": first, "second": second, "floor_id": floor(text),
                                "door_floor_id": core.spaces[first]["floor_id"]}
    raise MapError("Unsupported question wording; use structured spatial tools instead.")


def answer(building_directory: Path, question_text: str) -> str:
    """Official benchmark adapter: reads building.json, never questions.jsonl."""
    core = SpatialCore.load(building_directory)
    try:
        kind, inputs = parse_question(core, question_text)
        return core.format_answer(core.solve(kind, inputs))
    except MapError as error:
        # A benchmark counts this as wrong; an interactive agent should ask for an ID.
        # Do not manufacture an Answer line or select a room by inspecting answer keys.
        return f"Cannot determine a unique answer: {error} Please specify an exact space ID or supported query."

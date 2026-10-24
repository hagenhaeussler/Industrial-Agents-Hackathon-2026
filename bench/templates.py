"""Parse published question wording into typed solver inputs, without answer keys."""

import re
from dataclasses import dataclass

from starter_agent.building_map import BuildingMap, MapError


def resolve_reference(building: BuildingMap, text: str, kind: str) -> str:
    """Use the shared resolver only after full rendered labels have been checked."""
    try:
        from core.resolve import resolve
    except ModuleNotFoundError as error:
        if error.name not in {"core", "core.resolve"}:
            raise
        raise MapError(f"Unknown or ambiguous {kind}: {text}; shared resolver unavailable.") from error
    result = resolve(building, text, kind)
    if result["status"] != "unique":
        labels = ", ".join(item["label"] for item in result["candidates"][:4])
        raise MapError(f"{result['status'].capitalize()} {kind}: {text}; candidates: {labels}")
    return result["candidates"][0]["id"]


@dataclass
class TemplateParser:
    building: BuildingMap

    def floor(self, fragment: str) -> str:
        matches = re.findall(r"\bon the (ground floor|floor -?\d+|basement \d+)\b", fragment, re.I)
        if not matches:
            raise MapError("No target floor in question.")
        text = matches[-1].lower()
        level = 0 if text == "ground floor" else int(re.search(r"-?\d+", text)[0])
        if text.startswith("basement"):
            level = -level
        matches = [floor["id"] for floor in self.building.floors.values() if floor["level"] == level]
        if len(matches) != 1:
            raise MapError(f"Unknown or ambiguous floor: {text}")
        return matches[0]

    def entity(self, fragment: str) -> str:
        fragment = fragment.strip()
        matches = [space["id"] for space in self.building.spaces.values()
                   if fragment.casefold() == f"{space['name']} ({self.building.floor_name(space['floor_id'])})".casefold()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise MapError(f"Ambiguous room label: {fragment}; candidates: {', '.join(matches)}")
        return resolve_reference(self.building, fragment, "space")

    def room_type(self, fragment: str) -> str:
        types = {space["room_type"] for space in self.building.spaces.values()}
        matches = [kind for kind in types if kind.replace("_", " ").casefold() == fragment.strip().casefold()]
        if len(matches) != 1:
            raise MapError(f"Unknown room type: {fragment}")
        return matches[0]

    def entity_pair(self, fragment: str) -> tuple[str, str]:
        pairs = set()
        errors = []
        for separator in re.finditer(" and ", fragment):
            try:
                pairs.add((self.entity(fragment[:separator.start()]), self.entity(fragment[separator.end():])))
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

    def asset_type(self, fragment: str) -> str:
        normal = re.sub(r"[\s-]+", "_", fragment.strip().casefold())
        types = {asset["type"] for asset in self.building.assets.values()}
        if normal not in types:
            raise MapError(f"Unknown asset type: {fragment}")
        return normal

    def asset(self, fragment: str) -> str:
        normal = re.sub(r"[\s-]+", "_", fragment.strip().casefold())
        matches = [asset["id"] for asset in self.building.assets.values()
                   if asset["type"] == normal or re.match(re.escape(fragment.strip()) + r"(?:\b|$)", asset["name"], re.I)]
        if len(matches) != 1:
            raise MapError(f"Ambiguous or unknown asset: {fragment}; {len(matches)} candidates. Please name the exact item.")
        return matches[0]

    def element(self, fragment: str) -> str:
        elements = {**self.building.connectors, **self.building.openings, **self.building.spaces}
        if fragment in elements:
            return fragment
        connectors = [element["id"] for element in self.building.connectors.values()
                      if element["name"].casefold() == fragment.strip().casefold()]
        if len(connectors) == 1:
            return connectors[0]
        matches = [element["id"] for element in elements.values()
                   if element.get("name", "").casefold() == fragment.strip().casefold()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise MapError(f"Ambiguous closure: {fragment}")
        return resolve_reference(self.building, fragment, "any")

    def count_asset_type(self, fragment: str) -> str:
        normal = re.sub(r"[\s-]+", "_", fragment.strip().casefold())
        types = {asset["type"] for asset in self.building.assets.values()}
        matches = [kind for kind in types if kind == normal or kind.endswith("_" + normal)]
        if len(matches) != 1:
            raise MapError(f"Unknown or ambiguous asset type: {fragment}")
        return matches[0]

    def parse(self, question: str) -> tuple[str, dict]:
        text = question.split(" Finish with a line", 1)[0].strip()
        match = re.fullmatch(r"Which is the largest (.+?) on the .+?, and how big is it in m²\?", text)
        if match:
            return "largest_room", {"floor_id": self.floor(text), "room_type": self.room_type(match[1])}
        match = re.fullmatch(r"Facilities want the total floor area of every (.+?) on the .+? added together\. How many square metres is that\?", text)
        if match:
            return "floor_area_total", {"floor_id": self.floor(text), "room_type": self.room_type(match[1])}
        match = re.fullmatch(r"I'm in (.+?)\. I need to grab an? (.+?) from the room that has one closest to me, then carry it to the largest (.+?) on the .+?\. I can carry it on the stairs\. How far will I walk in total, in metres\?", text)
        if match:
            return "errand", {"start": self.entity(match[1]), "asset_type": self.asset_type(match[2]),
                              "floor_id": self.floor(text), "room_type": self.room_type(match[3])}
        match = re.fullmatch(r"We're soundproofing (.+?)\. How many other rooms on that floor share a wall with it\? Count every room whose wall runs along it for at least 1 m, with or without a door between them; corridors, stairwells and lifts don't count\.", text)
        if match:
            return "shared_walls_count", {"start": self.entity(match[1])}
        match = re.fullmatch(r"I'm moving a ([\d.]+) m wide .+?\. It can't go on stairs or steps \(lifts are fine\), and every door it passes through must be at least ([\d.]+) m wide\. It arrives through the entrance into (.+?)\. Into how many rooms on the .+? can it be delivered\?", text)
        if match:
            if float(match[1]) != float(match[2]):
                raise MapError("Conflicting delivery widths.")
            return "wide_delivery_count", {"start": self.entity(match[3]), "floor_id": self.floor(text),
                                          "min_width": float(match[1])}
        match = re.fullmatch(r"(.+?) is out of service\. A wheelchair user comes in through the entrance into (.+?)\. How many rooms on the .+? can they still reach\?", text)
        if match:
            return "step_free_reachable_count", {"closed": self.element(match[1]),
                                                 "start": self.entity(match[2]), "floor_id": self.floor(text)}
        match = re.fullmatch(r"We're planning a wireless sensor link between (.+?) and (.+?)\. What is the straight-line distance in metres between the centres of the two rooms \(each room's floor-plan centroid, at its floor's elevation\)\?", text)
        if match:
            first, second = self.entity_pair(match[1] + " and " + match[2])
            return "straight_line_3d", {"first": first, "second": second}
        match = re.fullmatch(r"There's water dripping from the ceiling in (.+?)\. Which room is directly above it\?", text)
        if match:
            return "room_stacked", {"start": self.entity(match[1]), "direction": "above"}
        match = re.fullmatch(r"A washing machine is leaking onto the floor of (.+?)\. Which room directly below it will the water reach\?", text)
        if match:
            return "room_stacked", {"start": self.entity(match[1]), "direction": "below"}
        match = re.fullmatch(r"What if we add a door between (.+?) and (.+?), in the middle of the wall they share\? How many rooms on the .+? would then have a shorter walk out of the building, to their nearest entrance, by more than 1 m\?", text)
        if match:
            first, second = self.entity_pair(match[1] + " and " + match[2])
            return "what_if_door", {"first": first, "second": second, "floor_id": self.floor(text),
                                    "door_floor_id": self.building.spaces[first]["floor_id"]}
        match = re.fullmatch(r"Where is the (.+?)\?", text)
        if match:
            return "locate", {"asset": self.asset(match[1])}
        match = re.fullmatch(r"How many (.+?) items are on the .+?\?", text)
        if match:
            return "count", {"asset_type": self.count_asset_type(match[1]), "floor_id": self.floor(text)}
        match = re.fullmatch(r"How do I get from (.+?) to (.+?)\?", text)
        if match:
            return "route", {"start": self.entity(match[1]), "destination": self.entity(match[2])}
        match = re.fullmatch(r"Is there a step-free route from (.+?) to (.+?)\?", text)
        if match:
            return "route_step_free", {"start": self.entity(match[1]), "destination": self.entity(match[2]), "step_free": True}
        match = re.fullmatch(r"(.+?) is closed for maintenance\. How do I get from (.+?) to (.+?)\?", text)
        if match:
            return "route_with_closure", {"start": self.entity(match[2]), "destination": self.entity(match[3]), "closed": [self.element(match[1])]}
        match = re.fullmatch(r"Starting at (.+?), visit (.+?), then (.+?) in this order\. What is the route\?", text)
        if match:
            return "tour", {"stops": [self.entity(match[1]), self.entity(match[2]), self.entity(match[3])], "keep_order": True}
        raise MapError("Unsupported question wording; use structured spatial tools instead.")


def parse_question(building: BuildingMap, question: str) -> tuple[str, dict]:
    return TemplateParser(building).parse(question)

"""Compact English directions derived from the route's actual chosen doors."""

import math


def _at_distance(points, distance, reverse=False):
    points = list(reversed(points)) if reverse else points
    remaining = distance
    for first, second in zip(points, points[1:]):
        length = math.dist(first, second)
        if length >= remaining and length:
            t = remaining / length
            return [first[0] + t * (second[0] - first[0]), first[1] + t * (second[1] - first[1])]
        remaining -= length
    return points[-1]


def _turn(before, at, after):
    incoming = [at[0] - before[0], at[1] - before[1]]
    outgoing = [after[0] - at[0], after[1] - at[1]]
    if math.hypot(*incoming) < 1e-9 or math.hypot(*outgoing) < 1e-9:
        return None
    angle = math.degrees(math.atan2(incoming[0] * outgoing[1] - incoming[1] * outgoing[0],
                                    incoming[0] * outgoing[0] + incoming[1] * outgoing[1]))
    magnitude = abs(angle)
    if magnitude <= 30:
        return None
    if magnitude > 150:
        return "u_turn"
    side = "left" if angle > 0 else "right"
    return ("slight_" if magnitude <= 60 else "turn_") + side


def _landmark(b, point, space_ids):
    assets = [(math.dist(asset["position"][:2], point), asset["id"], asset["name"])
              for asset in b.assets.values() if asset["space_id"] in space_ids
              and asset.get("category") in {"machine", "equipment", "fixture"}]
    nearby = [asset for asset in assets if asset[0] <= 3.0]
    return min(nearby)[2] if nearby else None


def _short(text):
    return text if len(text) <= 90 else text[:86].rstrip(" .,;:") + "..."


def build_maneuvers(b, route):
    start, destination = route["from_space_id"], route["to_space_id"]
    segments = route["segments"]
    result = []

    def emit(kind, floor_id, at, distance, text, landmark=None, element_id=None):
        result.append({"i": len(result), "kind": kind, "floor_id": floor_id,
                       "at": list(at), "distance_m": round(distance, 2), "text": _short(text),
                       "landmark": landmark, "element_id": element_id})

    emit("depart", b.spaces[start]["floor_id"], route["start_position"], 0,
         f"Start in {b.spaces[start]['name']}.")
    pending = 0.0
    index = 0
    while index < len(segments):
        segment = segments[index]
        if segment["kind"] != "walk":
            # Merge flights of the same connector into a single spoken action.
            last = segment
            connector_distance = segment["length_m"]
            while index + 1 < len(segments) and segments[index + 1]["kind"] != "walk" and segments[index + 1]["element_id"] == segment["element_id"]:
                index += 1
                last = segments[index]
                connector_distance += last["length_m"]
            connector = b.connectors[segment["element_id"]]
            kind = "take_lift" if segment["kind"] == "lift" else "take_stairs"
            emit(kind, segment["floor_id"], segment["points"][0], pending,
                 f"Take the {connector['name']} to {b.floor_name(last['to_floor_id'])}.",
                 connector["name"], connector["id"])
            pending = connector_distance
            index += 1
            continue
        pending += segment["length_m"]
        following = segments[index + 1] if index + 1 < len(segments) else None
        if following and following["kind"] == "walk" and following["space_id"] != segment["space_id"]:
            leaving, entered = segment["space_id"], following["space_id"]
            point = segment["points"][-1]
            before = _at_distance(segment["points"], 1.5, reverse=True)
            after = _at_distance(following["points"], 1.5)
            kind = _turn(before, point, after)
            opening = segment.get("to_node", "").removeprefix("door:")
            opening = opening if opening in b.openings else None
            asset = _landmark(b, point, {leaving, entered})
            entered_space = b.spaces[entered]
            if kind:
                instruction = {"slight_left": "bear left", "slight_right": "bear right",
                               "turn_left": "turn left", "turn_right": "turn right",
                               "u_turn": "make a U-turn"}[kind]
                text = f"After the {asset}, {instruction}." if asset else f"{instruction.capitalize()} into {entered_space['name']}."
                emit(kind, following["floor_id"], point, pending, text, asset or entered_space["name"], opening)
                pending = 0.0
            elif entered == destination or entered_space.get("room_type") in {"hall", "corridor", "lobby", "circulation"}:
                emit("enter", following["floor_id"], point, pending,
                     f"Go through the door into {entered_space['name']}.", asset or entered_space["name"], opening)
                pending = 0.0
        index += 1
    emit("arrive", b.spaces[destination]["floor_id"], route["destination_position"], pending,
         f"You have arrived at {b.spaces[destination]['name']}.")
    return result

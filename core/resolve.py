"""Exact-first entity resolution with number-safe fuzzy candidates."""

import re
import unicodedata
from rapidfuzz.fuzz import token_set_ratio

_SYNONYMS = {"wc": "toilet", "toiletten": "toilet", "elevator": "lift",
              "aufzug": "lift", "treppe": "stairs", "treppen": "stairs",
              "büro": "office", "drucker": "printer", "erdgeschoss": "ground floor"}


def normalized(text):
    value = unicodedata.normalize("NFKC", str(text)).casefold().replace("_", " ")
    for old, new in _SYNONYMS.items():
        value = re.sub(r"\b" + re.escape(old) + r"\b", new, value)
    value = re.sub(r"\d+", lambda m: str(int(m[0])), value)
    return " ".join(re.findall(r"\w+(?:\.\w+)*", value))


def _entities(b, kind):
    result = []
    groups = [("space", b.spaces), ("asset", b.assets), ("floor", b.floors),
              ("connector", b.connectors), ("opening", b.openings)]
    for entity_kind, items in groups:
        if kind != "any" and kind != entity_kind:
            continue
        for entity_id, item in items.items():
            name = item.get("name") or item.get("ref") or entity_id
            floor = b.floors.get(item.get("floor_id"), {})
            label = f"{name} ({floor['name']})" if floor.get("name") else name
            aliases = [name, item.get("ref", ""), label]
            if entity_kind == "floor":
                aliases += [str(item["level"]), f"floor {item['level']}"]
            if entity_kind == "asset":
                aliases.append(item.get("type", "").replace("_", " "))
            result.append({"kind": entity_kind, "id": entity_id, "label": label,
                           "aliases": [a for a in aliases if a]})
    if kind in {"asset_type", "room_type"}:
        source, field = (b.assets, "type") if kind == "asset_type" else (b.spaces, "room_type")
        for entity_id in sorted({v[field] for v in source.values()}):
            result.append({"kind": kind, "id": entity_id,
                           "label": entity_id.replace("_", " "),
                           "aliases": [entity_id, entity_id.replace("_", " ")]})
    return result


def resolve(b, text, kind="any"):
    if kind not in {"any", "space", "asset", "asset_type", "room_type", "floor", "connector", "opening"}:
        from .errors import CoreError
        raise CoreError("invalid_args", f"Unsupported entity kind: {kind}")
    if not isinstance(text, str) or not text.strip():
        return {"status": "none", "candidates": []}
    query = text.strip()
    items = _entities(b, kind)
    stages = [
        ("exact ID", lambda e: query == e["id"], 1.0),
        ("exact name/ref", lambda e: query.casefold() in [a.casefold() for a in e["aliases"]], 1.0),
        ("normalized", lambda e: normalized(query) in [normalized(a) for a in e["aliases"]], .98),
    ]
    for why, predicate, score in stages:
        matches = [e for e in items if predicate(e)]
        if matches:
            return {"status": "unique" if len(matches) == 1 else "ambiguous",
                    "candidates": [{k: e[k] for k in ("kind", "id", "label")} |
                                   {"score": score, "why": why} for e in matches[:8]]}
    nq = normalized(query)
    numbers = set(re.findall(r"\d+", nq))
    scores = []
    for e in items:
        aliases = [normalized(a) for a in e["aliases"]]
        scores_for_alias = [token_set_ratio(nq, a) for a in aliases
                            if numbers <= set(re.findall(r"\d+", a))]
        score = max(scores_for_alias, default=0)
        if score >= 85:
            scores.append((score, e))
    if not scores:
        return {"status": "none", "candidates": []}
    best = max(score for score, _ in scores)
    matches = [e for score, e in scores if abs(score-best) < 1e-9]
    return {"status": "unique" if len(matches) == 1 else "ambiguous",
            "candidates": [{k: e[k] for k in ("kind", "id", "label")} |
                           {"score": best / 100, "why": "fuzzy"} for e in matches[:8]]}

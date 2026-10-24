"""Fresh materialisations with immutable source data and reusable walking caches."""

import copy
import hashlib
import json
from pathlib import Path
from threading import RLock

from starter_agent.building_map import BuildingMap, outline
from .errors import CoreError
from .profiles import current_profile

_WALKS = {}
_CACHE_LOCK = RLock()


def content_hash(raw):
    payload = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def step_free_connector(connector):
    """Physical stairs remain stairs even if source accessibility data conflicts."""
    return connector["kind"] != "stairs" and connector["step_free"]


class Building(BuildingMap):
    def __init__(self, raw, *, version=0):
        super().__init__(copy.deepcopy(raw))
        self.id = self.data["building"]["id"]
        self.content_hash = content_hash(self.data)
        self.version = version
        self.profile = current_profile()
        self.warnings = []
        self.polygons = {}
        for sid, space in self.spaces.items():
            polygon = outline(space["polygon"])
            if polygon.is_empty or polygon.area <= 0:
                raise CoreError("invalid_args", f"Empty or degenerate polygon: {sid}")
            from shapely.geometry import Polygon
            if not Polygon(space["polygon"]).is_valid:
                self.warnings.append({"code": "polygon_repaired", "space_id": sid})
            self.polygons[sid] = polygon
        self._walk_cache_key = (self.content_hash, version, self.profile)
        with _CACHE_LOCK:
            self.walks = dict(_WALKS.get(self._walk_cache_key, {}))

    def space_walks(self, space_id):
        walks = super().space_walks(space_id)
        with _CACHE_LOCK:
            _WALKS.setdefault(self._walk_cache_key, {})[space_id] = walks
        return walks

    def graph(self, step_free=False):
        graph = super().graph(step_free)
        if step_free:
            blocked = {cid for cid, connector in self.connectors.items()
                       if not step_free_connector(connector)}
            graph.remove_edges_from([(first, second, key)
                                     for first, second, key, edge in graph.edges(keys=True, data=True)
                                     if edge.get("via") in blocked])
        return graph

    def anchor(self, space_id):
        p = self.polygons[space_id].representative_point()
        return p.x, p.y

    def add_door(self, *args, **kwargs):
        opening = super().add_door(*args, **kwargs)
        self.content_hash = content_hash(self.data)
        self._walk_cache_key = (self.content_hash, self.version, self.profile)
        return opening

    def resolve_space(self, reference):
        if isinstance(reference, dict):
            reference = reference.get("space_id")
        if reference in self.spaces:
            return reference
        if reference in self.assets:
            return self.assets[reference]["space_id"]
        # Compatibility for the starter and reference parser; no fuzzy guesses.
        if not isinstance(reference, str):
            raise CoreError("invalid_args", "A space ID or asset ID is required.")
        matches = [sid for sid, s in self.spaces.items()
                   if reference.casefold() == f"{s['name']} ({self.floor_name(s['floor_id'])})".casefold()]
        if len(matches) == 1:
            return matches[0]
        return super().resolve_space(reference)


def load_building(path_or_dict):
    if isinstance(path_or_dict, Building):
        clone = type(path_or_dict)(path_or_dict.data, version=path_or_dict.version)
        clone.closed = set(path_or_dict.closed)
        clone.walks = dict(path_or_dict.walks)
        return clone
    if isinstance(path_or_dict, dict):
        return Building(path_or_dict)
    path = Path(path_or_dict)
    if path.is_dir():
        path = path / "building.json"
    return Building(json.loads(path.read_text(encoding="utf-8")))

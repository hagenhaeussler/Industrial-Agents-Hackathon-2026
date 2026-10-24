"""Shared application operations for REST, voice tools and text chat."""

from copy import deepcopy
import json
import hashlib
import threading

from . import core_adapter as adapter
from .buildings import BuildingSnapshot, DerivedGeometry
from .errors import ServiceError
from .state import identifier, now
from starter_agent.building_map import MapError, outline


class PlatformService:
    def __init__(self, catalog, store, profile="kit_1_1_0", notify=None):
        self.catalog = catalog
        self.store = store
        self.profile = profile
        self.notify = notify or (lambda building_id, message: None)
        self.marker_generator = None
        self._cache = {}
        self._cache_lock = threading.RLock()

    def current(self, building_id, version=None):
        try:
            record = self.catalog.get(building_id)
        except KeyError as exc:
            raise ServiceError("not_found", str(exc.args[0]), status=404) from exc
        events = self.store.events(building_id)
        latest = len(events)
        if version is not None:
            if version < 0 or version > latest:
                raise ServiceError("version_conflict", "Requested building version is unavailable.", status=409, building_version=latest)
            events = events[:version]
        stat = record.path.stat()
        key = str(record.path), stat.st_mtime_ns, stat.st_size, json.dumps(events, sort_keys=True, separators=(",", ":")), self.profile
        with self._cache_lock:
            if key not in self._cache:
                raw = json.loads(record.path.read_text(encoding="utf-8"))
                self._cache[key] = adapter.materialize(raw, events)
                self._cache[key].cache_store = self.store
                self._cache[key].event_fingerprint = hashlib.sha256(key[3].encode()).hexdigest()
                if len(self._cache) > 64:
                    del self._cache[next(iter(self._cache))]
            return self._cache[key]

    def snapshot(self, building_id, version=None):
        building = self.current(building_id, version)
        anchors, areas = {}, {}
        for space in building.raw["spaces"]:
            polygon = outline(space["polygon"])
            point = polygon.representative_point()
            anchors[space["id"]] = [point.x, point.y]
            areas[space["id"]] = polygon.area
        return BuildingSnapshot(
            building=building.raw, building_version=building.version,
            content_hash=building.content_hash, closed=sorted(building.closed),
            derived=DerivedGeometry(anchors=anchors, areas_m2=areas),
        )

    @staticmethod
    def constraints(session, overrides=None):
        constraints = {"step_free": session["profile"] in {"wheelchair", "step_free", "pram", "trolley"}, "min_door_width_m": 0.0,
                       "closed": [], "no_transit_room_types": [], **session.get("constraints", {})}
        original_closed = set(constraints.get("closed", []))
        constraints.update({k: v for k, v in (overrides or {}).items() if v is not None})
        constraints["closed"] = sorted(original_closed | set(constraints.get("closed", [])))
        if session["profile"] in {"wheelchair", "pram", "trolley", "step_free"}:
            constraints["step_free"] = True
        return constraints

    def _stops(self, building, items):
        grouped = {}
        if not items:
            raise ServiceError("invalid_args", "Choose at least one item or place.")
        for item in items:
            target = adapter.require_id(building, item)
            position = adapter.position(building, target)
            sid = position["space_id"]
            space = building.kit.spaces[sid]
            if sid not in grouped:
                grouped[sid] = {"stop_id": identifier("stop"), "space_id": sid, "asset_ids": [], "label": space["name"], "status": "pending", "target": sid}
            if target in building.kit.assets:
                grouped[sid]["asset_ids"].append(target)
        for stop in grouped.values():
            assets = [building.kit.assets[a]["name"] for a in stop["asset_ids"]]
            if assets:
                stop["label"] = ", ".join(assets) + " · " + stop["label"]
        return list(grouped.values())

    def _plan(self, building, start, stops, constraints, keep_order=False, end=None, order=None):
        previous = {
            "stops": deepcopy(stops),
            "order": list(order) if order is not None else [stop["stop_id"] for stop in stops],
            "order_policy": "fixed" if keep_order else "optimized_exact",
            "constraints": constraints,
            "end": end,
        }
        result = adapter.replan_tour(building, previous, start)
        result["start"] = adapter.position(building, start)
        result["end"] = adapter.position(building, end) if end else None
        result["profile"] = self.profile
        result["constraints"] = constraints
        result["building_version"] = building.version
        if not any(stop["status"] == "pending" for stop in result["stops"]):
            result["status"] = "completed"
        return result

    def create_tour(self, session_id, items, start=None, keep_order=False, end=None, constraints=None):
        session = self.store.get_session(session_id)
        building = self.current(session["building_id"])
        start = session["position"] if start is None else start
        if start is None:
            raise ServiceError("invalid_args", "Where are you starting? Confirm your room first.")
        if isinstance(start, str):
            start = adapter.require_id(building, start)
        if isinstance(end, str):
            end = adapter.require_id(building, end)
        if end is not None:
            end = adapter.position(building, end)
        stops = self._stops(building, items)
        result = self._plan(building, start, stops, self.constraints(session, constraints), keep_order, end)
        result["keep_order"] = keep_order
        result["session_id"] = session_id
        result["mobility_profile"] = session["profile"]
        tour = self.store.save_tour(session_id, result)
        self.store.update_session(session_id, {"active_tour_id": tour["tour_id"]})
        return tour

    def replan_tour(self, tour_id, session_id, position, reason=None):
        session = self.store.get_session(session_id)
        tour = self.store.get_tour(tour_id)
        if session["building_id"] != tour["building_id"]:
            raise ServiceError("forbidden", "This tour belongs to another building.", status=403)
        building = self.current(tour["building_id"])
        start = session["position"] if position is None else position
        if not start:
            raise ServiceError("invalid_args", "Confirm your current room before replanning.")
        result = self._plan(building, start, tour["stops"], self.constraints(session, tour.get("constraints")), tour.get("keep_order", tour["order_policy"] == "fixed"), tour.get("end"), order=tour["order"])
        result.update(tour_id=tour_id, session_id=session_id, keep_order=tour.get("keep_order", False), mobility_profile=session["profile"])
        events = self.store.events(tour["building_id"])
        result["changed_because"] = ({"event_id": events[-1]["event_id"], "summary": events[-1]["summary"]} if events else {"event_id": None, "summary": reason}) if reason or events else None
        result = self.store.save_tour(session_id, result, expected_revision=tour["revision"])
        self.notify(tour["building_id"], {"type": "tour_updated", "tour_id": tour_id, "revision": result["revision"]})
        return result

    def progress_tour(self, tour_id, stop_id, status, session_id=None):
        if status not in {"collected", "pending"}:
            raise ServiceError("invalid_args", "Stop status must be collected or pending.")
        tour = self.store.get_tour(tour_id)
        caller = self.store.get_session(session_id) if session_id else None
        if caller and (caller["building_id"] != tour["building_id"] or (caller["active_tour_id"] != tour_id and tour["session_id"] != session_id)):
            raise ServiceError("forbidden", "Open this tour in your session before changing its progress.", status=403)
        stops = deepcopy(tour["stops"])
        stop = next((s for s in stops if s["stop_id"] == stop_id), None)
        if not stop:
            raise ServiceError("not_found", "Stop not found in this tour.", status=404)
        if stop["status"] == status:
            return tour
        stop["status"] = status
        session_id = session_id or tour["session_id"]
        session = caller or self.store.get_session(session_id)
        building = self.current(tour["building_id"])
        position = adapter.position(building, stop["space_id"]) if status == "collected" else session["position"] or tour["start"]
        result = self._plan(building, position, stops, self.constraints(session, tour.get("constraints")), tour.get("keep_order", False), tour.get("end"), order=tour["order"])
        result.update(tour_id=tour_id, session_id=session_id, keep_order=tour.get("keep_order", False), mobility_profile=session["profile"])
        result = self.store.save_tour(session_id, result, expected_revision=tour["revision"])
        if status == "collected":
            self.store.update_session(session_id, {"position": {**position, "source": "manual", "marker_id": None, "heading_deg": None, "confidence": "medium", "updated_at": now()}})
        self.notify(tour["building_id"], {"type": "tour_updated", "tour_id": tour_id, "revision": result["revision"]})
        return result

    def propose_edit(self, session_id, edit, op_id=None):
        session = self.store.get_session(session_id)
        self.store._require_admin(session)
        building = self.current(session["building_id"])
        resolved = adapter.resolve_edit(building, edit)
        preview = adapter.preview_edit(building, resolved, self.store.active_tours(building.id))
        return self.store.propose(session_id, resolved, building.version, preview.get("summary", f"{resolved['action']} {resolved['target']}"), preview["effects"], op_id)

    def commit_edit(self, session_id, proposal_id, expected_version=None, op_id=None):
        event, changed = self.store.commit(session_id, proposal_id, expected_version, op_id)
        if changed:
            self.notify(event["building_id"], {"type": "building_changed", "building_id": event["building_id"], "building_version": event["building_version"], "event": event, "at": now()})
        return event

    def undo(self, session_id, event_id=None, op_id=None):
        session = self.store.get_session(session_id)
        self.store._require_admin(session)
        events = self.store.events(session["building_id"])
        # Retry identity is checked before replay validation. A successful undo
        # remains the same operation even after newer edits have been committed.
        existing_operation = False
        if op_id:
            with self.store.connect() as db:
                existing_operation = db.execute("SELECT 1 FROM events WHERE op_id=?", (op_id,)).fetchone() is not None
        if existing_operation:
            event, changed = self.store.undo(session_id, event_id, op_id)
        else:
            undone = {item["undoes"] for item in events if item["kind"] == "undo"}
            if event_id:
                candidate = next((item for item in events if item["event_id"] == event_id), None)
            else:
                candidate = next((item for item in reversed(events) if item["session_id"] == session_id and item["kind"] != "undo" and item["event_id"] not in undone), None)
            if candidate is None or candidate["kind"] == "undo":
                raise ServiceError("not_found", "No change is available to undo.", status=404)
            if candidate["event_id"] in undone:
                raise ServiceError("invalid_args", "This change has already been undone.")
            simulated = {
                **candidate, "event_id": f"evt-{len(events) + 1}",
                "building_version": len(events) + 1, "kind": "undo",
                "undoes": candidate["event_id"], "op_id": op_id,
                "proposal_id": None, "session_id": session_id,
                "author_role": "admin", "summary": "Undo: " + candidate["summary"],
                "created_at": now(),
            }
            record = self.catalog.get(session["building_id"])
            raw = json.loads(record.path.read_text(encoding="utf-8"))
            try:
                adapter.materialize(raw, [*events, simulated])
            except (ServiceError, MapError, KeyError) as exc:
                raise ServiceError("invalid_args", "Undo later changes first.") from exc
            # The simulation is meaningful only for this exact event version.
            # A concurrent edit makes the transaction reject and request a retry.
            event, changed = self.store.undo(session_id, candidate["event_id"], op_id, expected_version=len(events))
        if changed:
            self.notify(event["building_id"], {"type": "building_changed", "building_id": event["building_id"], "building_version": event["building_version"], "event": event, "at": now()})
        return event

    def next_step(self, session_id):
        session = self.store.get_session(session_id)
        if not session["active_tour_id"]:
            raise ServiceError("invalid_args", "Plan or open a tour first.")
        tour = self.store.get_tour(session["active_tour_id"])
        pending = [sid for sid in tour["order"] if next(s for s in tour["stops"] if s["stop_id"] == sid)["status"] == "pending"]
        if not pending:
            if any(stop["status"] == "pending" for stop in tour["stops"]):
                raise ServiceError("no_route", "The remaining stops cannot currently be reached.")
            return {"complete": True, "text": "All planned stops have been collected."}
        stop = next(s for s in tour["stops"] if s["stop_id"] == pending[0])
        if not tour["legs"] or not tour["legs"][0].get("reachable"):
            raise ServiceError("no_route", "The next stop cannot currently be reached.")
        maneuvers = tour["legs"][0].get("maneuvers", [])
        index = tour.get("navigation_index", 0)
        if index >= len(maneuvers):
            return {"at_stop": True, "stop_id": stop["stop_id"], "text": f"At {stop['label']}, confirm collection with Got it."}
        instruction = maneuvers[index]
        tour["navigation_index"] = index + 1
        saved = self.store.save_tour(tour["session_id"], tour, expected_revision=tour["revision"])
        self.notify(tour["building_id"], {"type": "tour_updated", "tour_id": tour["tour_id"], "revision": saved["revision"]})
        return instruction

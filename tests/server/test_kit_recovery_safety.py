"""Core and the labelled kit fallback share progress and stair safety rules."""

from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import Settings


@pytest.fixture(params=["core", "kit"])
def recovery_api(tmp_path, monkeypatch, request):
    if request.param == "kit":
        from server import core_adapter
        monkeypatch.setattr(core_adapter, "core_function", lambda module, name: None)
    # Independent fixture: four adjacent rooms below an upstairs destination.
    # The contradictory source flag is deliberately retained, not sanitized.
    raw = {
        "building": {"id": "recovery-safety", "name": "Recovery safety fixture", "source": "test", "units": "m"},
        "floors": [{"id": "f0", "name": "Ground", "level": 0, "elevation_m": 0, "height_m": 3},
                   {"id": "f1", "name": "First", "level": 1, "elevation_m": 3, "height_m": 3}],
        "spaces": [{"id": sid, "name": sid, "floor_id": "f0", "room_type": "office", "type": "room",
                    "polygon": [[4 * index, 0], [4 * index + 4, 0], [4 * index + 4, 4], [4 * index, 4]]}
                   for index, sid in enumerate(["a", "b", "c", "d"])],
        "openings": [{"id": "entrance", "floor_id": "f0", "space_ids": ["outside", "a"],
                      "kind": "door", "position": [0, 2], "width_m": 1.2, "step_free": True}],
        "vertical_connectors": [{"id": kind, "name": kind, "kind": kind, "step_free": True,
                                 "floor_ids": ["f0", "f1"], "space_ids": ["d", "up"]}
                                for kind in ["stairs", "lift"]],
        "assets": [],
    }
    raw["spaces"].append({"id": "up", "name": "Upstairs", "floor_id": "f1", "room_type": "office", "type": "room",
                          "polygon": [[12, 0], [16, 0], [16, 4], [12, 4]]})
    for index, (first, second) in enumerate([("a", "b"), ("b", "c"), ("c", "d")], start=1):
        raw["openings"].append({"id": first + second, "floor_id": "f0", "space_ids": [first, second],
                                "kind": "door", "position": [4 * index, 2], "width_m": 1.2, "step_free": True})
    hero = tmp_path / "hero"
    hero.mkdir()
    (hero / "fixture.json").write_text(json.dumps(raw))
    settings = Settings(data_dir=tmp_path / "data", hero_dir=hero,
                        state_dir=tmp_path / "state", static_dir=tmp_path / "web")
    with TestClient(create_app(settings)) as client:
        assert client.app.state.service.current(raw["building"]["id"]).adapter == request.param
        yield client, raw


def session(client, building_id, start, role="navigator", profile="walk"):
    response = client.post("/api/sessions", json={"building_id": building_id, "role": role, "profile": profile})
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]
    response = client.patch("/api/sessions/" + session_id, json={"position": {"space_id": start, "source": "desk"}})
    assert response.status_code == 200, response.text
    return session_id


def tool(client, session_id, name, args):
    response = client.post("/api/tools/" + name, json={"session_id": session_id, "args": args})
    assert response.status_code == 200, response.text
    return response.json()


def test_restoring_middle_stop_preserves_fixed_sequence_and_collected_snapshot(recovery_api):
    client, raw = recovery_api
    session_id = session(client, raw["building"]["id"], "a")
    response = client.post("/api/tours", json={
        "session_id": session_id, "items": ["b", "c", "d"], "keep_order": True,
    })
    assert response.status_code == 200, response.text
    original = response.json()
    prescribed = original["order"]
    assert [stop["space_id"] for stop in original["stops"]] == ["b", "c", "d"]
    middle_id = prescribed[1]
    path = "/api/tours/" + original["tour_id"]
    response = client.post(path + "/progress", json={"stop_id": middle_id, "status": "collected"},
                           headers={"X-Session-ID": session_id})
    assert response.status_code == 200, response.text
    collected = response.json()
    snapshot = deepcopy(next(stop for stop in collected["stops"] if stop["stop_id"] == middle_id))
    assert snapshot["status"] == "collected"
    response = client.post(path + "/replan", json={"session_id": session_id, "from": {"space_id": "a"}})
    assert response.status_code == 200, response.text
    replanned = response.json()
    response = client.post(path + "/progress", json={"stop_id": middle_id, "status": "pending"},
                           headers={"X-Session-ID": session_id})
    assert response.status_code == 200, response.text
    restored = response.json()

    assert [stop["stop_id"] for stop in collected["stops"]] == prescribed
    assert [stop["stop_id"] for stop in replanned["stops"]] == prescribed
    assert next(stop for stop in replanned["stops"] if stop["stop_id"] == middle_id) == snapshot
    assert replanned["order"] == [stop_id for stop_id in prescribed if stop_id != middle_id]
    assert restored["order_policy"] == "fixed"
    assert restored["order"] == prescribed
    assert [stop["stop_id"] for stop in restored["stops"]] == prescribed
    assert all(stop["status"] == "pending" for stop in restored["stops"])
    assert client.get(path).json() == restored


def test_step_free_route_excludes_physical_stairs_despite_accessibility_flag(recovery_api):
    client, raw = recovery_api
    building_id = raw["building"]["id"]
    wheelchair = session(client, building_id, "d", profile="wheelchair")
    walker = session(client, building_id, "d")
    admin = session(client, building_id, "d", role="admin")
    before = tool(client, wheelchair, "route", {"destination": "up"})
    assert before["ok"], before
    preview = tool(client, admin, "propose_edit", {"action": "close", "target": "lift"})
    assert preview["ok"], preview
    committed = tool(client, admin, "commit_edit", {"proposal_id": preview["result"]["proposal_id"]})
    assert committed["ok"], committed

    blocked = tool(client, wheelchair, "route", {"destination": "up", "step_free": True})
    walking = tool(client, walker, "route", {"destination": "up"})
    assert walking["ok"] and walking["result"]["element_path"] == ["stairs"], walking
    assert not blocked["ok"] and blocked["error"]["code"] == "no_route", blocked
    assert blocked["error"]["route"]["reachable"] is False
    assert blocked["error"]["route"].get("element_path", []) == []
    assert before["result"]["element_path"] == ["lift"]
    snapshot = client.get("/api/buildings/" + building_id).json()
    assert snapshot["closed"] == ["lift"]
    assert next(connector for connector in snapshot["building"]["vertical_connectors"]
                if connector["kind"] == "stairs")["step_free"] is True

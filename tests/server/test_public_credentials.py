"""Public building activity must not disclose private session capabilities."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings
from server.schemas import TourResult


CODE = "privacy-test-admin-code"


@pytest.fixture
def api(tmp_path):
    settings = Settings(admin_token=CODE, state_dir=tmp_path / "state",
                        hero_dir=tmp_path / "hero", static_dir=tmp_path / "web")
    assert settings.admin_requires_code is True
    raw = json.loads((REPO_ROOT / "data/dev/proc-factory-dev-003/building.json").read_text())
    with TestClient(create_app(settings)) as client:
        yield client, raw


def session(client, raw, *, role="navigator", device="desk", profile="walk"):
    headers = {"X-Admin-Token": CODE} if role == "admin" else {}
    response = client.post("/api/sessions", json={
        "building_id": raw["building"]["id"], "role": role, "device": device, "profile": profile,
    }, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def tool(client, session_id, name, args):
    response = client.post("/api/tools/" + name, json={"session_id": session_id, "args": args})
    assert response.status_code == 200, response.text
    return response.json()


def assert_public(value, *credentials):
    if isinstance(value, dict):
        assert "session_id" not in value, value
        for child in value.values():
            assert_public(child, *credentials)
    elif isinstance(value, list):
        for child in value:
            assert_public(child, *credentials)
    encoded = json.dumps(value)
    assert all(credential not in encoded for credential in credentials)
    assert CODE not in encoded


def create_tour(client, raw, owner):
    rooms = [space["id"] for space in raw["spaces"][:2]]
    response = client.patch("/api/sessions/" + owner, json={"position": {"space_id": rooms[0]}})
    assert response.status_code == 200, response.text
    response = client.post("/api/tours", json={"session_id": owner, "items": rooms, "keep_order": True})
    assert response.status_code == 200, response.text
    return response.json()


def validate_tour(payload):
    # These REST routes intentionally omit null values. Restore the two nullable
    # members when validating their domain model; all routing fields stay intact.
    return TourResult.model_validate({"end": None, "changed_because": None, **payload})


def test_public_event_and_broadcast_hide_admin_owner_without_losing_audit(api):
    client, raw = api
    bid = raw["building"]["id"]
    admin = session(client, raw, role="admin")
    navigator = session(client, raw)
    lift = next(connector["id"] for connector in raw["vertical_connectors"] if connector["kind"] == "lift")
    with client.websocket_connect("/ws/buildings/" + bid) as ws:
        assert ws.receive_json()["type"] == "hello"
        preview = tool(client, admin, "propose_edit", {"action": "close", "target": lift})
        assert preview["ok"], preview
        args = {"proposal_id": preview["result"]["proposal_id"], "op_id": "privacy-close"}
        committed = tool(client, admin, "commit_edit", args)
        assert committed["ok"], committed
        event = committed["result"]
        assert event["session_id"] == admin  # Private caller response retains ownership.
        internal = deepcopy(client.app.state.store.events(bid))
        message = ws.receive_json()
        public = client.get("/api/buildings/" + bid + "/events").json()
        assert message["type"] == "building_changed"
        assert message["event"]["event_id"] == public[0]["event_id"] == event["event_id"]
        assert message["building_version"] == public[0]["building_version"] == 1
        assert public[0]["edit"] == event["edit"] and public[0]["summary"] == event["summary"]
        assert_public(message, admin)
        assert_public(public, admin)
        assert client.app.state.store.events(bid) == internal == [event]
        assert tool(client, admin, "commit_edit", args)["result"] == event
        assert len(client.app.state.store.events(bid)) == 1
        refused = tool(client, navigator, "propose_edit", {"action": "open", "target": lift})
        assert not refused["ok"] and refused["error"]["code"] == "forbidden"

        undo_args = {"event_id": event["event_id"], "op_id": "privacy-undo"}
        undone = tool(client, admin, "undo", undo_args)
        assert undone["ok"] and undone["result"]["session_id"] == admin
        undo_message = ws.receive_json()
        assert undo_message["event"]["undoes"] == event["event_id"]
        assert_public(undo_message, admin)
        assert tool(client, admin, "undo", undo_args)["result"] == undone["result"]
        internal = client.app.state.store.events(bid)
        assert len(internal) == 2 and all(row["session_id"] == admin for row in internal)
        assert client.get("/api/buildings/" + bid).json()["closed"] == []
        assert_public(client.get("/api/buildings/" + bid + "/events?since=1").json(), admin)


def test_public_tour_responses_keep_normal_phone_handoff_without_owner_bearers(api):
    client, raw = api
    admin = session(client, raw, role="admin", profile="wheelchair")
    tour = create_tour(client, raw, admin)
    assert_public(tour, admin)
    validate_tour(tour)
    path = "/api/tours/" + tour["tour_id"]
    assert_public(client.get(path).json(), admin)
    assert client.app.state.store.get_tour(tour["tour_id"])["session_id"] == admin
    phone = session(client, raw, device="phone")
    with client.websocket_connect("/ws/buildings/" + raw["building"]["id"]) as ws:
        assert ws.receive_json()["type"] == "hello"
        response = client.patch("/api/sessions/" + phone, json={"active_tour_id": tour["tour_id"]})
        assert response.status_code == 200, response.text
        handoff = response.json()
        assert handoff["session_id"] == phone  # A session's own response stays private.
        assert handoff["profile"] == "wheelchair" and handoff["constraints"] == tour["constraints"]
        assert handoff["position"]["source"] == "tour_start"
        opened = ws.receive_json()
        assert opened["type"] == "tour_opened" and opened["tour_id"] == tour["tour_id"]
        assert opened["device"] == "phone"
        assert_public(opened, admin, phone)
        response = client.post(path + "/progress", json={
            "stop_id": tour["order"][0], "status": "collected",
        }, headers={"X-Session-ID": phone})
        assert response.status_code == 200, response.text
        progressed = response.json()
        validate_tour(progressed)
        assert_public(progressed, admin, phone)
        assert next(stop for stop in progressed["stops"] if stop["stop_id"] == tour["order"][0])["status"] == "collected"
        updated = ws.receive_json()
        assert updated["type"] == "tour_updated"
        assert_public(updated, admin, phone)
        position = client.get("/api/sessions/" + phone).json()["position"]
        response = client.post(path + "/replan", json={"session_id": phone, "from": position})
        assert response.status_code == 200, response.text
        replanned = response.json()
        validate_tour(replanned)
        assert_public(replanned, admin, phone)
        assert {stop["stop_id"] for stop in replanned["stops"]} == {stop["stop_id"] for stop in tour["stops"]}
        assert client.get(path).json() == replanned


def test_admin_phone_open_and_nested_tour_metadata_never_publish_session_capabilities(api):
    client, raw = api
    owner = session(client, raw, role="admin")
    admin_phone = session(client, raw, role="admin", device="phone")
    tour = create_tour(client, raw, owner)
    path = "/api/tours/" + tour["tour_id"]
    reason = {"session_id": owner, "details": [{"session_id": admin_phone, "message": "Refresh route"}]}
    response = client.post(path + "/replan", json={"session_id": owner, "from": tour["start"], "reason": reason})
    assert response.status_code == 200, response.text
    public = response.json()
    assert_public(public, owner, admin_phone)
    assert public["changed_because"]["summary"]["details"] == [{"message": "Refresh route"}]
    validate_tour(public)
    stored = deepcopy(client.app.state.store.get_tour(tour["tour_id"]))
    assert stored["session_id"] == owner and stored["changed_because"]["summary"] == reason
    assert_public(client.get(path).json(), owner, admin_phone)
    with client.websocket_connect("/ws/buildings/" + raw["building"]["id"]) as ws:
        assert ws.receive_json()["type"] == "hello"
        response = client.patch("/api/sessions/" + admin_phone, json={"active_tour_id": tour["tour_id"]})
        assert response.status_code == 200, response.text
        assert response.json()["session_id"] == admin_phone
        opened = ws.receive_json()
        assert opened["type"] == "tour_opened" and opened["tour_id"] == tour["tour_id"]
        assert_public(opened, owner, admin_phone)
    assert client.app.state.store.get_tour(tour["tour_id"]) == stored

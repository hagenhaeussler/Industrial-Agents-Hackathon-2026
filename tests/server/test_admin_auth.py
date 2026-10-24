"""The public role field grants no authority, including after a database upgrade."""

from dataclasses import replace
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings
from server.state import now


BUILDING_ID = "proc-factory-dev-003"
ADMIN_CODE = "offline-test-admin-code-9b733802"


@pytest.fixture
def settings(tmp_path):
    return Settings(state_dir=tmp_path / "state", static_dir=tmp_path / "dist",
                    hero_dir=tmp_path / "hero", admin_token=ADMIN_CODE)


def create_session(client, role="navigator", token=None):
    return client.post("/api/sessions", json={"building_id": BUILDING_ID, "role": role},
                       headers={"X-Admin-Token": token} if token is not None else {})


def tool(client, session_id, name, args=None):
    return client.post("/api/tools/" + name, json={"session_id": session_id, "args": args or {}})


def assert_forbidden(response):
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"
    assert ADMIN_CODE not in response.text


@pytest.mark.parametrize("demo_mode", [False, True])
@pytest.mark.parametrize("allow_open", [False, True])
@pytest.mark.parametrize("token", [None, "wrong-admin-code", ""])
def test_configured_code_is_required_even_in_demo_mode(settings, demo_mode, allow_open, token):
    with TestClient(create_app(replace(settings, demo_mode=demo_mode,
                                      allow_unauthenticated_demo_admin=allow_open))) as client:
        assert_forbidden(create_session(client, "admin", token))
        assert create_session(client).status_code == 200
        with client.app.state.store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM sessions WHERE role='admin'").fetchone()[0] == 0


def test_unconfigured_public_app_fails_closed_but_navigators_work(settings):
    with TestClient(create_app(replace(settings, admin_token=""))) as client:
        assert_forbidden(create_session(client, "admin"))
        assert_forbidden(create_session(client, "admin", "arbitrary-code"))
        session = create_session(client).json()
        assert session["role"] == "navigator"
        assert client.get("/api/sessions/" + session["session_id"]).status_code == 200


def test_explicit_code_free_demo_is_available_only_without_configured_secret(settings):
    with TestClient(create_app(replace(settings, admin_token="", demo_mode=True, allow_unauthenticated_demo_admin=True))) as client:
        response = create_session(client, "admin")
        assert response.status_code == 200, response.text
        assert response.json()["role"] == "admin"
        session_id = response.json()["session_id"]
    with TestClient(create_app(replace(settings, admin_token="", demo_mode=False))) as client:
        assert_forbidden(client.get("/api/sessions/" + session_id))


@pytest.mark.parametrize("demo_mode,allow_open", [(True, False), (False, True), (False, False)])
def test_code_free_admin_requires_both_explicit_demo_flags(settings, demo_mode, allow_open):
    with TestClient(create_app(replace(settings, admin_token="", demo_mode=demo_mode,
                                      allow_unauthenticated_demo_admin=allow_open))) as client:
        assert_forbidden(create_session(client, "admin"))
        assert create_session(client).status_code == 200


def test_admin_authority_never_appears_in_session_responses_or_settings_repr(settings):
    with TestClient(create_app(settings)) as client:
        response = create_session(client, "admin", ADMIN_CODE)
        assert response.status_code == 200, response.text
        sid = response.json()["session_id"]
        for response in [response, client.get("/api/sessions/" + sid),
                         client.patch("/api/sessions/" + sid, json={"profile": "walk"})]:
            assert response.status_code == 200, response.text
            assert ADMIN_CODE not in response.text
            assert "authority" not in response.text and "_admin_authorized" not in response.text
        with client.app.state.store.connect() as db:
            proof = db.execute("SELECT admin_authority FROM sessions WHERE session_id=?", (sid,)).fetchone()[0]
        assert proof.startswith("token-v1:") and ADMIN_CODE not in proof
    assert ADMIN_CODE not in repr(settings)


def test_authenticated_admin_can_preview_commit_undo_upload_mark_and_reset(settings):
    with TestClient(create_app(replace(settings, demo_mode=True))) as client:
        admin = create_session(client, "admin", ADMIN_CODE).json()["session_id"]
        raw = json.loads((REPO_ROOT / "data/dev" / BUILDING_ID / "building.json").read_text())
        lift = next(c["id"] for c in raw["vertical_connectors"] if c["kind"] == "lift")
        proposal = tool(client, admin, "propose_edit", {"action": "close", "target": lift}).json()
        assert proposal["ok"], proposal
        committed = tool(client, admin, "commit_edit", {"proposal_id": proposal["result"]["proposal_id"]}).json()
        assert committed["ok"] and committed["result"]["building_version"] == 1
        undone = tool(client, admin, "undo").json()
        assert undone["ok"] and undone["result"]["building_version"] == 2
        uploaded = client.post("/api/buildings", json=raw, headers={"X-Session-ID": admin})
        assert uploaded.status_code == 200, uploaded.text
        sid = raw["spaces"][0]["id"]
        point = list(client.app.state.service.current(BUILDING_ID).kit.anchor(sid))
        marked = client.post(f"/api/buildings/{BUILDING_ID}/markers", json={"markers": [
            {"space_id": sid, "point": point, "heading_deg": 0, "label": "Authenticated marker"}]},
            headers={"X-Session-ID": admin})
        assert marked.status_code == 200, marked.text
        reset = client.post("/api/demo/reset", json={"building_id": BUILDING_ID}, headers={"X-Session-ID": admin})
        assert reset.status_code == 200 and reset.json()["building_version"] == 0


def test_navigator_cannot_edit_upload_mark_or_reset(settings):
    with TestClient(create_app(replace(settings, demo_mode=True))) as client:
        nav = create_session(client).json()["session_id"]
        for name, args in [("propose_edit", {"action": "close", "target": "any"}),
                           ("commit_edit", {"proposal_id": "not-a-proposal"}), ("undo", {}),
                           ("what_if", {"action": "close", "target": "any"}), ("generate_markers", {})]:
            response = tool(client, nav, name, args)
            assert response.status_code == 200
            assert not response.json()["ok"] and response.json()["error"]["code"] == "forbidden"
        assert_forbidden(client.post("/api/buildings", json={}, headers={"X-Session-ID": nav}))
        assert_forbidden(client.post(f"/api/buildings/{BUILDING_ID}/markers", json={"markers": [
            {"space_id": "any", "point": [0, 0], "heading_deg": 0, "label": "bad"}]}, headers={"X-Session-ID": nav}))
        assert_forbidden(client.post("/api/demo/reset", json={"building_id": BUILDING_ID}, headers={"X-Session-ID": nav}))
        assert_forbidden(client.post("/api/buildings", json={}))


def test_migration_revokes_old_role_only_admin_without_revoking_navigator(settings):
    settings.state_dir.mkdir(parents=True)
    # An actual pre-auth schema: no authority column, publicly minted admin.
    with sqlite3.connect(settings.state_dir / "tyb.sqlite3") as db:
        db.execute("""CREATE TABLE sessions(session_id TEXT PRIMARY KEY,building_id TEXT NOT NULL,
                   device TEXT NOT NULL,role TEXT NOT NULL,profile TEXT NOT NULL,constraints_json TEXT NOT NULL,
                   position_json TEXT,active_tour_id TEXT,updated_at TEXT NOT NULL)""")
        for sid, role in [("legacy-admin", "admin"), ("legacy-navigator", "navigator")]:
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                       (sid, BUILDING_ID, "desk", role, "walk", "{}", None, None, now()))
    with TestClient(create_app(replace(settings, demo_mode=True))) as client:
        assert_forbidden(client.get("/api/sessions/legacy-admin"))
        assert client.get("/api/sessions/legacy-navigator").status_code == 200
        response = tool(client, "legacy-admin", "propose_edit", {"action": "close", "target": "any"})
        assert not response.json()["ok"] and response.json()["error"]["code"] == "forbidden"
        assert_forbidden(client.post("/api/buildings", json={}, headers={"X-Session-ID": "legacy-admin"}))
        assert_forbidden(client.post("/api/demo/reset", json={"building_id": BUILDING_ID}, headers={"X-Session-ID": "legacy-admin"}))
        assert create_session(client, "admin", ADMIN_CODE).status_code == 200


def test_rotating_secret_revokes_prior_admin_but_restarts_keep_current_proof(settings):
    with TestClient(create_app(settings)) as client:
        admin = create_session(client, "admin", ADMIN_CODE).json()["session_id"]
        navigator = create_session(client).json()["session_id"]
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/sessions/" + admin).status_code == 200
    with TestClient(create_app(replace(settings, admin_token="rotated-test-code"))) as client:
        assert_forbidden(client.get("/api/sessions/" + admin))
        assert client.get("/api/sessions/" + navigator).status_code == 200
        assert_forbidden(create_session(client, "admin", ADMIN_CODE))
        assert create_session(client, "admin", "rotated-test-code").status_code == 200


def test_authority_is_bound_to_one_session_identity(settings):
    with TestClient(create_app(settings)) as client:
        admin = create_session(client, "admin", ADMIN_CODE).json()["session_id"]
        navigator = create_session(client).json()["session_id"]
        with client.app.state.store.connect(write=True) as db:
            proof = db.execute("SELECT admin_authority FROM sessions WHERE session_id=?", (admin,)).fetchone()[0]
            db.execute("UPDATE sessions SET role='admin',admin_authority=? WHERE session_id=?", (proof, navigator))
        assert_forbidden(client.get("/api/sessions/" + navigator))


def test_public_events_websockets_tours_and_tools_never_publish_bearer_sessions(settings):
    with TestClient(create_app(settings)) as client:
        admin = create_session(client, "admin", ADMIN_CODE).json()["session_id"]
        building = client.app.state.service.current(BUILDING_ID)
        start = next(iter(building.kit.spaces))
        lift = next(c["id"] for c in building.kit.connectors.values() if c["kind"] == "lift")
        response = client.patch("/api/sessions/" + admin, json={"position": {"space_id": start}})
        assert response.status_code == 200
        tour = client.post("/api/tours", json={"session_id": admin, "items": [start]}).json()
        assert "session_id" not in tour
        assert admin not in client.get("/api/tours/" + tour["tour_id"]).text
        # Ownership stays private and continues to support operations correctly.
        assert client.app.state.store.get_tour(tour["tour_id"])["session_id"] == admin
        with client.websocket_connect("/ws/buildings/" + BUILDING_ID) as socket:
            assert socket.receive_json()["type"] == "hello"
            proposed = tool(client, admin, "propose_edit", {"action": "close", "target": lift}).json()
            committed = tool(client, admin, "commit_edit", {"proposal_id": proposed["result"]["proposal_id"]})
            assert committed.json()["ok"]
            assert admin not in committed.text and "session_id" not in committed.json()["result"]
            broadcast = socket.receive_json()
            assert broadcast["type"] == "building_changed"
            assert "session_id" not in broadcast["event"] and admin not in json.dumps(broadcast)
            events = client.get(f"/api/buildings/{BUILDING_ID}/events")
            assert "session_id" not in events.json()[0] and admin not in events.text
            assert client.app.state.store.events(BUILDING_ID)[0]["session_id"] == admin
            phone = client.post("/api/sessions", json={"building_id": BUILDING_ID, "device": "phone"}).json()
            handoff = client.patch("/api/sessions/" + phone["session_id"], json={"active_tour_id": tour["tour_id"]})
            assert handoff.status_code == 200
            opened = socket.receive_json()
            assert opened["type"] == "tour_opened"
            assert "session_id" not in opened and phone["session_id"] not in json.dumps(opened)
        undone = tool(client, admin, "undo").json()
        assert undone["ok"] and "session_id" not in undone["result"]


def test_from_env_loads_private_secret_without_a_testing_bypass(monkeypatch):
    monkeypatch.setenv("TYB_ADMIN_TOKEN", ADMIN_CODE)
    monkeypatch.setenv("TYB_DEMO_MODE", "false")
    settings = Settings.from_env()
    assert settings.admin_token == ADMIN_CODE and not settings.demo_mode
    assert ADMIN_CODE not in repr(settings)

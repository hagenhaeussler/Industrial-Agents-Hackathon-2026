"""Server contracts against real kit data, persistent startup, and SPA routing."""

from dataclasses import replace
import csv
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from shapely.geometry import Point
from starter_agent.building_map import outline

from server.app import create_app
from server.config import REPO_ROOT, Settings


def kit_building_count():
    with (REPO_ROOT / "data/manifest.csv").open(newline="") as stream:
        return len(list(csv.DictReader(stream)))


@pytest.fixture
def settings(tmp_path):
    return Settings(state_dir=tmp_path / "state", hero_dir=tmp_path / "hero", static_dir=tmp_path / "dist")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_identifies_commit_profile_real_catalog_and_writable_state(client, settings, monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "deployed-sha")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "ok": True, "commit": "deployed-sha", "profile": "kit_1_1_0",
        "state_dir_writable": True, "buildings": kit_building_count(),
    }
    assert (settings.state_dir / "uploads").is_dir()
    with sqlite3.connect(settings.state_dir / "tyb.sqlite3") as connection:
        assert connection.execute("SELECT version FROM schema_version").fetchone()[0] >= 1


def test_health_reports_unusable_state_without_hiding_catalog(settings):
    settings.state_dir.write_text("A file occupies the state directory path")
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["state_dir_writable"] is False
        assert response.json()["ok"] is False
        assert len(client.get("/api/buildings").json()) == kit_building_count()


def test_real_snapshot_geometry_and_hash_are_stable(client):
    listed = client.get("/api/buildings").json()
    target = next(row for row in listed if row["id"] == "proc-factory-dev-003")
    assert target["floors"] == 2
    assert target["has_lift"] is True
    assert target["has_stairs"] is True
    first = client.get("/api/buildings/" + target["id"])
    second = client.get("/api/buildings/" + target["id"] + "?version=0")
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.headers["content-encoding"] == "gzip"
    snapshot = first.json()
    assert snapshot["building_version"] == 0
    assert snapshot["content_hash"].startswith("sha256:")
    assert len(snapshot["content_hash"]) == 23
    assert snapshot["closed"] == []
    for space in snapshot["building"]["spaces"]:
        polygon = outline(space["polygon"])
        assert polygon.covers(Point(snapshot["derived"]["anchors"][space["id"]]))
        assert snapshot["derived"]["areas_m2"][space["id"]] == pytest.approx(polygon.area)


def test_catalog_discovers_hero_and_uploads_without_overriding_kit(client, settings):
    base = json.loads((REPO_ROOT / "data/dev/proc-factory-dev-003/building.json").read_text())
    settings.hero_dir.mkdir()
    hero = json.loads(json.dumps(base))
    hero["building"]["id"] = "hero-test"
    (settings.hero_dir / "building.json").write_text(json.dumps(hero))
    upload = json.loads(json.dumps(base))
    upload["building"]["id"] = "upload-test"
    (settings.state_dir / "uploads" / "uploaded.json").write_text(json.dumps(upload))
    base["building"]["name"] = "Do not override kit data"
    (settings.state_dir / "uploads" / "duplicate.json").write_text(json.dumps(base))
    (settings.state_dir / "uploads" / "not-a-building.json").write_text("{}")
    catalog = client.get("/api/buildings").json()
    assert len(catalog) == kit_building_count() + 2
    assert {"hero-test", "upload-test"} <= {b["id"] for b in catalog}
    assert next(b for b in catalog if b["id"] == "proc-factory-dev-003")["name"] != "Do not override kit data"
    assert client.get("/api/buildings/hero-test").json()["building"]["building"]["id"] == "hero-test"


def test_snapshot_uses_core_loader_when_published(settings, monkeypatch):
    import server.buildings
    calls = []
    original_import = server.buildings.importlib.import_module

    def load(path):
        calls.append(path)
        return SimpleNamespace(content_hash="core-hash", version=0, closed=[])

    def import_module(name):
        return SimpleNamespace(load_building=load) if name == "core.building" else original_import(name)

    monkeypatch.setattr(server.buildings.importlib, "import_module", import_module)
    snapshot = server.buildings.BuildingCatalog(settings).snapshot("proc-factory-dev-003").model_dump()
    assert snapshot["content_hash"] == "core-hash"
    assert len(calls) == 1
    assert calls[0]["building"]["id"] == "proc-factory-dev-003"


def test_transport_errors_have_contract_envelope_and_versions_are_explicit(client):
    response = client.get("/api/buildings/unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["detail"]
    response = client.get("/api/buildings/proc-factory-dev-003?version=1")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "version_conflict"
    response = client.get("/api/buildings/proc-factory-dev-003?version=-1")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_args"


def test_spa_history_routing_preserves_api_ws_health_and_static_bounds(client, settings):
    settings.static_dir.mkdir()
    (settings.static_dir / "index.html").write_text("<html>SPA shell</html>")
    (settings.static_dir / "assets").mkdir()
    (settings.static_dir / "assets" / "app.js").write_text("console.log('ok')")
    for path in ("/", "/desk", "/admin", "/go/tour-id", "/m/marker-id"):
        response = client.get(path)
        assert response.status_code == 200
        assert "SPA shell" in response.text
    assert client.get("/assets/app.js").text == "console.log('ok')"
    for path in ("/api/missing", "/ws/buildings/test", "/health/nope", "/assets/missing.js", "/missing.css", "/%2e%2e/secret.txt"):
        response = client.get(path)
        assert response.status_code == 404
        assert "SPA shell" not in response.text
    assert client.get("/health").json()["ok"] is True


def test_manifest_cannot_escape_data_root(settings, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "building.json").write_text("{}")
    (data / "manifest.csv").write_text(
        "building_id,name,source,split,floors,has_lift,has_stairs,path\n"
        "escape,Escape,upload,dev,1,False,False,..\n"
    )
    with TestClient(create_app(replace(settings, data_dir=data))) as client:
        assert client.get("/api/buildings").json() == []
        assert client.get("/api/buildings/escape").status_code == 404


def test_dev_cors_accepts_local_frontend(client):
    response = client.options("/api/buildings", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
    })
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/buildings", headers={
        "Origin": "https://unrelated.example", "Access-Control-Request-Method": "GET",
    })
    assert "access-control-allow-origin" not in response.headers


def test_openapi_includes_typed_contract_models(client):
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("HealthResponse")
    assert "BuildingSnapshot" in schema["components"]["schemas"]
    assert "BuildingSummary" in schema["components"]["schemas"]


def test_live_and_exported_openapi_expose_reset_safe_state_identity(client):
    """Generated clients must discover C9 even though old fixture/tour IDs are optional."""
    live = client.get('/openapi.json').json()
    exported = json.loads((REPO_ROOT / 'server/openapi.json').read_text())
    for name in ('BuildingSnapshot', 'TourResult', 'RouteResult'):
        live_model = live['components']['schemas'][name]
        exported_model = exported['components']['schemas'][name]
        identity = live_model['properties']['building_state_id']
        assert identity == exported_model['properties']['building_state_id']
        assert identity['anyOf'] == [{'type': 'string'}, {'type': 'null'}]
        assert 'reset' in identity['description']
        assert 'building_state_id' not in live_model.get('required', [])

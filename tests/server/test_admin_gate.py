"""CR-C-2: the admin role is never granted from the request body alone."""
from dataclasses import replace
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import Settings
from server.routes_live import admin_allowed

BID = 'proc-factory-dev-003'
CODE = 'test-admin-code-7f3a'


@pytest.fixture
def settings(tmp_path, monkeypatch):
    # Neither a developer's .env nor inherited local opt-ins may open this gate.
    monkeypatch.setattr('server.config.load_dotenv', lambda *args, **kwargs: None)
    monkeypatch.delenv('TYB_ADMIN_TOKEN', raising=False)
    monkeypatch.delenv('TYB_ADMIN_OPEN_INSECURE', raising=False)
    monkeypatch.delenv('TYB_DEMO_MODE', raising=False)
    monkeypatch.delenv('TYB_ALLOW_UNAUTHENTICATED_DEMO_ADMIN', raising=False)
    return Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist')


def create(client, role, code=None):
    headers = {'X-Admin-Token': code} if code is not None else {}
    return client.post('/api/sessions', json={'building_id': BID, 'role': role, 'device': 'desk', 'profile': 'walk'}, headers=headers)


def test_direct_constructor_fails_closed_without_affecting_navigators(settings):
    assert settings.allow_unauthenticated_demo_admin is False
    assert settings.admin_token == ''
    with TestClient(create_app(settings)) as client:
        for code in (None, '', 'anything'):
            response = create(client, 'admin', code)
            assert response.status_code == 403
            assert response.json()['error']['code'] == 'forbidden'
        response = create(client, 'navigator')
        assert response.status_code == 200 and response.json()['role'] == 'navigator'


def test_admin_needs_the_exact_configured_code_with_constructor_defaults(settings):
    locked = replace(settings, admin_token=CODE)
    with TestClient(create_app(locked)) as client:
        for code in (None, '', 'wrong', CODE + 'x', CODE[:-1], CODE.upper()):
            response = create(client, 'admin', code)
            assert response.status_code == 403, code
            assert response.json()['error']['code'] == 'forbidden'
        admin = create(client, 'admin', CODE)
        assert admin.status_code == 200 and admin.json()['role'] == 'admin'
        navigator = create(client, 'navigator')
        assert navigator.status_code == 200 and navigator.json()['role'] == 'navigator'
        # a refused admin request created nothing that could act as admin
        refused_tool = client.post('/api/tools/propose_edit', json={'session_id': navigator.json()['session_id'], 'args': {'action': 'close', 'target': 'Office lift'}})
        assert refused_tool.json()['ok'] is False and refused_tool.json()['error']['code'] == 'forbidden'


def test_constructor_requires_both_explicit_code_free_demo_opt_ins(settings):
    insecure = replace(settings, demo_mode=True, allow_unauthenticated_demo_admin=True)
    with TestClient(create_app(insecure)) as client:
        response = create(client, 'admin')
        assert response.status_code == 200 and response.json()['role'] == 'admin'
        assert create(client, 'navigator').status_code == 200


def test_without_a_code_nobody_is_admin(settings):
    locked = replace(settings, admin_token=None)
    with TestClient(create_app(locked)) as client:
        assert create(client, 'admin').status_code == 403
        assert create(client, 'admin', 'anything').status_code == 403
        assert create(client, 'navigator').status_code == 200

    def request(host):
        return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=locked)), client=SimpleNamespace(host=host))
    # the client address is never an authentication factor, loopback included (same-host proxies)
    for host in ('127.0.0.1', '::1', 'localhost', '203.0.113.9'):
        assert admin_allowed(request(host), None) is False


def test_environment_locks_admin_by_default(settings, monkeypatch):
    configured = replace(Settings.from_env(), state_dir=settings.state_dir,
                         hero_dir=settings.hero_dir, static_dir=settings.static_dir)
    assert configured.allow_unauthenticated_demo_admin is False
    assert configured.admin_token == ''
    with TestClient(create_app(configured)) as client:
        assert create(client, 'admin').status_code == 403
        assert create(client, 'navigator').status_code == 200
    monkeypatch.setenv('TYB_ADMIN_TOKEN', '  ' + CODE + '  ')
    assert Settings.from_env().admin_token == CODE
    monkeypatch.setenv('TYB_ADMIN_TOKEN', '   ')
    assert Settings.from_env().admin_token == ''
    monkeypatch.setenv('TYB_ADMIN_OPEN_INSECURE', '1')
    assert Settings.from_env().allow_unauthenticated_demo_admin is False
    monkeypatch.setenv('TYB_ADMIN_OPEN_INSECURE', '')
    assert Settings.from_env().allow_unauthenticated_demo_admin is False


def test_environment_code_free_admin_requires_both_explicit_demo_opt_ins(settings, monkeypatch):
    monkeypatch.setenv('TYB_ALLOW_UNAUTHENTICATED_DEMO_ADMIN', 'true')
    monkeypatch.setenv('TYB_DEMO_MODE', 'true')
    configured = replace(Settings.from_env(), state_dir=settings.state_dir,
                         hero_dir=settings.hero_dir, static_dir=settings.static_dir)
    assert configured.allow_unauthenticated_demo_admin is True and configured.demo_mode is True
    with TestClient(create_app(configured)) as client:
        response = create(client, 'admin')
        assert response.status_code == 200 and response.json()['role'] == 'admin'

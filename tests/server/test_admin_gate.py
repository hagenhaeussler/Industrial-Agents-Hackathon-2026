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
def settings(tmp_path):
    return Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist')


def create(client, role, code=None):
    headers = {'X-Admin-Token': code} if code is not None else {}
    return client.post('/api/sessions', json={'building_id': BID, 'role': role, 'device': 'desk', 'profile': 'walk'}, headers=headers)


def test_admin_needs_the_configured_code(settings):
    locked = replace(settings, admin_token=CODE)
    with TestClient(create_app(locked)) as client:
        for code in (None, '', 'wrong', CODE + 'x', CODE[:-1]):
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


def test_environment_locks_admin_by_default(monkeypatch):
    monkeypatch.setattr('server.config.load_dotenv', lambda *args, **kwargs: None)  # a developer's .env must not leak in
    monkeypatch.delenv('TYB_ADMIN_TOKEN', raising=False)
    monkeypatch.delenv('TYB_ALLOW_UNAUTHENTICATED_DEMO_ADMIN', raising=False)
    monkeypatch.delenv('TYB_DEMO_MODE', raising=False)
    assert Settings.from_env().allow_unauthenticated_demo_admin is False
    assert Settings.from_env().admin_token == ''
    monkeypatch.setenv('TYB_ADMIN_TOKEN', '  ' + CODE + '  ')
    assert Settings.from_env().admin_token == CODE
    monkeypatch.setenv('TYB_ADMIN_TOKEN', '   ')
    assert Settings.from_env().admin_token == ''
    # The removed insecure setting cannot reopen public admin access.
    monkeypatch.setenv('TYB_ADMIN_OPEN_INSECURE', '1')
    assert Settings.from_env().allow_unauthenticated_demo_admin is False
    monkeypatch.setenv('TYB_ALLOW_UNAUTHENTICATED_DEMO_ADMIN', '1')
    assert Settings.from_env().allow_unauthenticated_demo_admin is True
    assert Settings.from_env().demo_mode is False
    monkeypatch.setenv('TYB_DEMO_MODE', 'true')
    assert Settings.from_env().demo_mode is True

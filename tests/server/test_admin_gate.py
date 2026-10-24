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
    locked = replace(settings, admin_requires_code=True, admin_token=CODE)
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


def test_without_a_code_only_this_machine_may_be_admin(settings):
    locked = replace(settings, admin_requires_code=True, admin_token=None)
    with TestClient(create_app(locked)) as client:  # the test client is not a loopback peer
        assert create(client, 'admin').status_code == 403
        assert create(client, 'admin', 'anything').status_code == 403
        assert create(client, 'navigator').status_code == 200

    def request(host):
        return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=locked)), client=SimpleNamespace(host=host) if host else None)
    assert admin_allowed(request('127.0.0.1'), None) is True
    assert admin_allowed(request('::1'), None) is True
    assert admin_allowed(request('203.0.113.9'), None) is False
    assert admin_allowed(request('10.0.0.4'), None) is False
    assert admin_allowed(request(None), None) is False


def test_environment_locks_admin_by_default(monkeypatch):
    monkeypatch.setattr('server.config.load_dotenv', lambda *args, **kwargs: None)  # a developer's .env must not leak in
    monkeypatch.delenv('TYB_ADMIN_TOKEN', raising=False)
    assert Settings.from_env().admin_requires_code is True
    assert Settings.from_env().admin_token is None
    monkeypatch.setenv('TYB_ADMIN_TOKEN', '  ' + CODE + '  ')
    assert Settings.from_env().admin_token == CODE
    monkeypatch.setenv('TYB_ADMIN_TOKEN', '   ')
    assert Settings.from_env().admin_token is None

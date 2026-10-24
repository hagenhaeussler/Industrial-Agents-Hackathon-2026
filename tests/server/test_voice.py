"""Voice provider contract checks with an in-process HTTP transport, never a paid call."""

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from server import voice


@pytest.fixture
def client(monkeypatch):
    for key in ("ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID_NAVIGATOR", "ELEVENLABS_AGENT_ID_ADMIN"):
        monkeypatch.delenv(key, raising=False)
    app = FastAPI()
    app.include_router(voice.router)
    with TestClient(app) as client:
        yield client


def provider(monkeypatch, handler):
    real_client = httpx.Client
    monkeypatch.setattr(voice.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))


def test_unconfigured_voice_returns_actionable_503(client):
    response = client.get("/api/voice/token")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "voice_unavailable"
    assert "text chat" in response.json()["detail"]
    assert response.headers["Cache-Control"] == "no-store"


def test_missing_agent_does_not_contact_provider(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "server-test-secret")
    monkeypatch.setattr(voice.httpx, "Client", lambda **kwargs: pytest.fail("Provider must not be contacted without agent ID"))
    assert client.get("/api/voice/token?agent=admin").status_code == 503


def test_token_exchange_uses_correct_agent_and_keeps_key_server_side(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "server-test-secret")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID_ADMIN", "agent_admin_test")
    def handle(request):
        assert str(request.url).startswith(voice.TOKEN_URL)
        assert request.url.params["agent_id"] == "agent_admin_test"
        assert request.headers["xi-api-key"] == "server-test-secret"
        return httpx.Response(200, json={"token": "short-lived-token", "conversation_id": "not-needed"})
    provider(monkeypatch, handle)
    response = client.get("/api/voice/token?agent=admin")
    assert response.status_code == 200
    assert response.json() == {"token": "short-lived-token", "agent_id": "agent_admin_test"}
    assert "server-test-secret" not in response.text
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("status, body", [(401, {"detail": "server-test-secret"}), (200, {"token": None}), (200, ["bad-token"])])
def test_provider_error_and_malformed_token_never_leak_provider_details(client, monkeypatch, status, body):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "server-test-secret")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID_NAVIGATOR", "agent_navigator_test")
    provider(monkeypatch, lambda request: httpx.Response(status, json=body))
    response = client.get("/api/voice/token")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "voice_unavailable"
    assert "server-test-secret" not in response.text


def test_invalid_agent_is_rejected_before_provider_call(client):
    assert client.get("/api/voice/token?agent=anything").status_code == 422

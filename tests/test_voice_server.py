"""Voice server tests: the token route passes the token through and hides upstream failures. No paid calls."""

import logging
import os
import unittest
from unittest import mock

from starlette.testclient import TestClient

from voice_agent.server import create_app
from voice_agent.settings import MissingSetting, VoiceSettings, load_settings, require_agent_id


class TokenRouteTest(unittest.TestCase):
    def test_returns_token_without_caching(self) -> None:
        client = TestClient(create_app(lambda: "token-123"))
        response = client.get("/api/voice/token")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"token": "token-123"})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_upstream_failure_returns_plain_error(self) -> None:
        def failing_source() -> str:
            raise RuntimeError("401 invalid xi-api-key sk_secret")

        client = TestClient(create_app(failing_source))
        with self.assertLogs("voice_agent.server", logging.ERROR):
            response = client.get("/api/voice/token")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("sk_secret", response.text)


class SettingsTest(unittest.TestCase):
    def test_missing_api_key_is_explicit(self) -> None:
        with (
            mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": " "}),
            mock.patch("voice_agent.settings.load_dotenv"),
            self.assertRaises(MissingSetting),
        ):
            load_settings()

    def test_token_needs_synced_agent(self) -> None:
        with self.assertRaises(MissingSetting):
            require_agent_id(VoiceSettings(api_key="key", agent_id=None))


if __name__ == "__main__":
    unittest.main()

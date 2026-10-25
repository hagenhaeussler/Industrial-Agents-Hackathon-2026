"""Voice server tests: the token route, the protected MCP endpoint and settings. No paid calls."""

import asyncio
import json
import logging
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from starlette.testclient import TestClient

from voice_agent.agent import CONTEXT_VARIABLES, system_prompt
from voice_agent.server import create_app
from voice_agent.settings import MissingSetting, VoiceSettings, load_settings, require_agent_id, require_mcp_token
from voice_agent.tools import MCP_PATH, building_files, load_buildings, mcp_app, voice_tools

REPO = Path(__file__).resolve().parents[1]
FACTORY, CAMPUS = "proc-factory-dev-003", "proc-campus-dev-000"
DEV_BUILDINGS = [REPO / "data" / "dev" / building_id / "building.json" for building_id in (FACTORY, CAMPUS)]
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def rpc_result(response_text: str) -> dict:
    """The JSON-RPC result from a streamable HTTP response, which arrives as one server-sent event."""
    data = next(line for line in response_text.splitlines() if line.startswith("data: "))
    return json.loads(data.removeprefix("data: "))["result"]


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

    def test_cors_allows_only_configured_origins(self) -> None:
        client = TestClient(create_app(lambda: "token-123", cors_origins=["https://ui.example.com"]))
        allowed = client.get("/api/voice/token", headers={"Origin": "https://ui.example.com"})
        self.assertEqual(allowed.headers["access-control-allow-origin"], "https://ui.example.com")
        other = client.get("/api/voice/token", headers={"Origin": "https://evil.example.com"})
        self.assertNotIn("access-control-allow-origin", other.headers)


class McpEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        buildings = load_buildings(DEV_BUILDINGS)
        tools = mcp_app(asyncio.run(voice_tools(buildings)), token="mcp-secret")
        cls.client = TestClient(create_app(lambda: "token-123", tools, buildings.values()))
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def call(
        self, method: str, params: dict | None = None, token: str | None = "mcp-secret", building: str | None = FACTORY
    ):
        headers = MCP_HEADERS | ({"Authorization": f"Bearer {token}"} if token else {})
        headers |= {"X-Building-Id": building} if building else {}
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        return self.client.post(MCP_PATH, headers=headers, json=body)

    def test_rejects_missing_or_wrong_token(self) -> None:
        self.assertEqual(self.call("tools/list", token=None).status_code, 401)
        self.assertEqual(self.call("tools/list", token="guess").status_code, 401)

    def tool_result(self, name: str, arguments: dict | None = None, building: str | None = FACTORY) -> dict:
        response = self.call("tools/call", {"name": name, "arguments": arguments or {}}, building=building)
        self.assertEqual(response.status_code, 200)
        return rpc_result(response.text)

    def test_each_call_answers_for_the_selected_building(self) -> None:
        for building_id in (FACTORY, CAMPUS, FACTORY):
            overview = json.loads(self.tool_result("building_overview", building=building_id)["content"][0]["text"])
            self.assertEqual(overview["building_id"], building_id)

    def test_missing_or_unknown_building_is_a_tool_error(self) -> None:
        for building in (None, "no-such-building"):
            result = self.tool_result("building_overview", building=building)
            self.assertTrue(result["isError"], building)

    def test_lists_the_served_buildings(self) -> None:
        listed = self.client.get("/api/voice/buildings").json()
        self.assertEqual({building["id"] for building in listed}, {FACTORY, CAMPUS})
        self.assertTrue(all(building.keys() == {"id", "name"} for building in listed))

    def test_tool_parameters_have_no_nested_objects(self) -> None:
        # ElevenLabs silently drops tools whose parameters contain objects.
        tools = rpc_result(self.call("tools/list").text)["tools"]
        self.assertIn("route", [tool["name"] for tool in tools])
        for tool in tools:
            parameters = json.dumps(tool["inputSchema"]["properties"])
            self.assertNotIn('"object"', parameters, tool["name"])
            self.assertNotIn("prefixItems", parameters, tool["name"])

    def test_route_takes_flat_conditions(self) -> None:
        lobby, printers = f"{FACTORY}-F0-S019", f"{FACTORY}-F0-S003"
        arguments = {"stops": [lobby, printers], "step_free": True, "closed": [printers]}
        response = self.call("tools/call", {"name": "route", "arguments": arguments})
        route = json.loads(rpc_result(response.text)["content"][0]["text"])
        self.assertFalse(route["reachable"])

    def test_token_route_still_works_next_to_tools(self) -> None:
        self.assertEqual(self.client.get("/api/voice/token").json(), {"token": "token-123"})


class AgentConfigTest(unittest.TestCase):
    def test_every_prompt_variable_has_a_default(self) -> None:
        # ElevenLabs refuses to start a conversation when a prompt variable has neither a value nor a default.
        used = set(re.findall(r"\{\{(\w+)\}\}", system_prompt()))
        self.assertTrue(used)
        self.assertLessEqual(used, set(CONTEXT_VARIABLES))


class SettingsTest(unittest.TestCase):
    def test_missing_api_key_is_explicit(self) -> None:
        with (
            mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": " "}),
            mock.patch("voice_agent.settings.load_dotenv"),
            self.assertRaises(MissingSetting),
        ):
            load_settings()

    def test_token_and_tools_need_their_settings(self) -> None:
        settings = VoiceSettings(api_key="key", agent_id=None, mcp_token=None)
        with self.assertRaises(MissingSetting):
            require_agent_id(settings)
        with self.assertRaises(MissingSetting):
            require_mcp_token(settings)

    def test_invalid_or_missing_buildings_fail_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                building_files(Path(directory))
            path = Path(directory) / "building.json"
            path.write_text("{}")
            with self.assertRaises(ValueError):
                load_buildings(building_files(Path(directory)))


if __name__ == "__main__":
    unittest.main()

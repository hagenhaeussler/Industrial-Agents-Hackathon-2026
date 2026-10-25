"""Exercise the real conversational harness and MCP tools with an offline model."""

import json
import unittest
import warnings
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx2 as httpx
from anthropic import AsyncAnthropic
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.usage import RequestUsage
from shapely.geometry import Polygon

from building_api.coworker_chat import ChatContext, CoworkerChat
from building_api.coworker_models import ChatMessage, Coworker, Position
from building_db.source import BuildingDocument
from building_tools.building import Building
from tests.test_building_db import fixture_building


class CoworkerHarnessTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        document = BuildingDocument.model_validate_json(json.dumps(fixture_building()))
        self.building = Building(document, {space.id: Polygon(space.polygon).area for space in document.spaces})
        self.member = Coworker(
            id="maya",
            name="Maya Chen",
            role="Facility manager",
            color="#b56843",
            position=Position(floor_id="F0", x=0.5, y=0.5, space_id="S-office", space_name="Office 0.01"),
            activity="Reviewing building operations",
            journey=None,
        )
        self.context = ChatContext(
            building=self.building,
            member=self.member,
            history=[ChatMessage(id="user-1", member_id="maya", role="user", text="Where are you?", created_at=0)],
            location=lambda: self.member,
        )

    async def test_reply_uses_authoritative_location_through_the_real_tool_loop(self):
        locations = []
        tool_names = set()

        def model(messages, info):
            tool_names.update(tool.name for tool in info.function_tools)
            results = [
                part
                for message in messages
                for part in message.parts
                if isinstance(part, ToolReturnPart) and part.tool_name == "current_location"
            ]
            if not results:
                return ModelResponse(parts=[ToolCallPart("current_location", {})])
            locations.append(json.loads(results[-1].content))
            return ModelResponse(parts=[TextPart("I'm in Office 0.01.")])

        with (
            patch.object(FunctionModel, "count_tokens", new=AsyncMock(return_value=RequestUsage(input_tokens=1000))),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", UserWarning)  # Offline model has no provider price.
            reply = await CoworkerChat(FunctionModel(model)).reply(self.context)
        self.assertEqual(reply.text, "I'm in Office 0.01.")
        self.assertEqual(locations[0]["coworker"]["position"], self.member.position.model_dump(by_alias=True))
        self.assertIn("find_spaces", tool_names)
        self.assertIn("route", tool_names)
        self.assertFalse(tool_names & {"shell", "read_file", "sql", "http"})

    async def test_oversized_context_is_rejected_before_a_model_request(self):
        calls = []

        def model(messages, info):
            calls.append(messages)
            return ModelResponse(parts=[TextPart("This must not be called.")])

        with patch.object(FunctionModel, "count_tokens", new=AsyncMock(return_value=RequestUsage(input_tokens=15000))):
            reply = await CoworkerChat(FunctionModel(model)).reply(self.context)
        self.assertEqual(calls, [])
        self.assertIsNone(reply.text)
        self.assertIn("UsageLimitExceeded", reply.error)

    async def test_provider_failure_is_explicit_and_keeps_uncertain_spend(self):
        def model(messages, info):
            raise RuntimeError("offline provider failure")

        with patch.object(FunctionModel, "count_tokens", new=AsyncMock(return_value=RequestUsage(input_tokens=1000))):
            reply = await CoworkerChat(FunctionModel(model)).reply(self.context)
        self.assertIsNone(reply.text)
        self.assertIsNone(reply.cost)
        self.assertIn("RuntimeError", reply.error)

    async def test_follow_up_bills_only_new_responses(self):
        self.context.history.extend(
            [
                ChatMessage(id="reply-1", member_id="maya", role="assistant", text="Office 0.01.", created_at=1),
                ChatMessage(id="user-2", member_id="maya", role="user", text="Thank you.", created_at=2),
            ]
        )
        billed = []

        def price(response):
            self.assertIsNotNone(response.model_name)
            billed.append(response)
            return SimpleNamespace(total_price=Decimal("0.003"))

        with (
            patch.object(FunctionModel, "count_tokens", new=AsyncMock(return_value=RequestUsage(input_tokens=1000))),
            patch.object(ModelResponse, "cost", new=price),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", UserWarning)
            reply = await CoworkerChat(
                FunctionModel(lambda messages, info: ModelResponse(parts=[TextPart("Welcome.")]))
            ).reply(self.context)
        self.assertEqual(reply.text, "Welcome.")
        self.assertEqual(reply.cost, 0.003)
        self.assertEqual(len(billed), 1)

    async def test_later_provider_failure_keeps_full_reservation_despite_prior_response(self):
        calls = 0

        def model(messages, info):
            nonlocal calls
            calls += 1
            if calls == 1:
                return ModelResponse(parts=[ToolCallPart("current_location", {})])
            raise RuntimeError("uncertain second request")

        with (
            patch.object(FunctionModel, "count_tokens", new=AsyncMock(return_value=RequestUsage(input_tokens=1000))),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", UserWarning)
            reply = await CoworkerChat(FunctionModel(model)).reply(self.context)
        self.assertEqual(calls, 2)
        self.assertIsNone(reply.cost)
        self.assertIsNone(reply.text)

    async def test_usage_limit_after_responses_keeps_full_reservation(self):
        def model(messages, info):
            return ModelResponse(
                parts=[ToolCallPart("current_location", {})],
                usage=RequestUsage(input_tokens=6000, output_tokens=900),
            )

        with (
            patch.object(FunctionModel, "count_tokens", new=AsyncMock(return_value=RequestUsage(input_tokens=1000))),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", UserWarning)
            reply = await CoworkerChat(FunctionModel(model)).reply(self.context)
        self.assertIn("UsageLimitExceeded", reply.error)
        self.assertIsNone(reply.cost)

    async def test_real_anthropic_client_does_not_retry_uncertain_message_requests(self):
        requests = []

        def transport(request):
            if request.url.path.endswith("count_tokens"):
                return httpx.Response(200, json={"input_tokens": 1000})
            requests.append(request)
            raise httpx.ReadTimeout("uncertain provider response", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            provider = AnthropicProvider(anthropic_client=AsyncAnthropic(api_key="offline-test", http_client=client))
            reply = await CoworkerChat(AnthropicModel("claude-sonnet-5-5", provider=provider)).reply(self.context)
        self.assertEqual(len(requests), 1)
        self.assertIsNone(reply.cost)
        self.assertIsNone(reply.text)

"""AI coworker sessions, real walking geometry, isolation and paid-call controls. No provider calls."""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from shapely.geometry import LineString, Polygon

from building_api.app import create_app
from building_api.coworker_chat import CoworkerChat, Reply
from building_api.coworker_movement import PERSONAS, WalkPoint, inside_path
from building_api.coworker_store import CoworkerStore
from building_api.coworkers import CoworkerService
from building_db.store import connect, import_building
from tests.test_building_db import DEV_BUILDING


class OfflineChat(CoworkerChat):
    def __init__(self):
        self.contexts = []
        self.failure = False

    @property
    def available(self):
        return True

    async def reply(self, context):
        self.contexts.append(context)
        return (
            Reply(None, 0.02, "Provider unavailable. Retry.")
            if self.failure
            else Reply(f"I am {context.member.name}, in {context.location().position.space_name}.", 0.01)
        )


class CoworkerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.database = root / "buildings.sqlite3"
        db = connect(self.database)
        result = import_building(db, DEV_BUILDING / "building.json")
        db.close()
        self.building_id = result.building_id
        self.chat = OfflineChat()
        self.store = CoworkerStore(root / "coworkers.sqlite3")
        self.service = CoworkerService(self.database, store=self.store, chat=self.chat, budget=5)
        self.client = TestClient(create_app(self.database, coworkers=self.service))
        self.base = f"/api/buildings/{self.building_id}/coworkers/sessions"
        self.state = self.client.post(self.base).json()
        self.url = f"{self.base}/{self.state['sessionId']}"

    def send(self, member="maya", text="Where are you?", request_id="request-number-0001"):
        return self.client.post(
            self.url + "/messages", json={"memberId": member, "text": text, "requestId": request_id}
        )

    def test_session_has_real_building_positions_without_model_calls(self):
        self.assertEqual(len(self.state["members"]), 4)
        day = self.service.workday(self.building_id)
        for member in self.state["members"]:
            position = member["position"]
            self.assertIn(position["spaceId"], day.building.space_by_id)
            self.assertEqual(position["floorId"], day.building.space(position["spaceId"]).floor_id)
        self.client.get(self.url)
        self.assertEqual(self.chat.contexts, [])

    def test_messages_and_model_history_are_private_to_member_and_session(self):
        self.assertEqual(self.send(text="Maya private message").status_code, 200)
        self.send("jonas", "Jonas private message", "request-number-0002")
        self.assertEqual([message.text for message in self.chat.contexts[-1].history], ["Jonas private message"])
        other = self.client.post(self.base).json()
        self.assertNotEqual(other["sessionId"], self.state["sessionId"])
        self.assertEqual(other["messages"], [])
        self.assertEqual(len(self.client.get(self.url).json()["messages"]), 4)

    def test_repeated_send_is_idempotent_even_after_budget_is_exhausted(self):
        self.send()
        self.service.budget = 0
        duplicate = self.send()
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(len(duplicate.json()["messages"]), 2)
        self.assertEqual(len(self.chat.contexts), 1)

    def test_request_id_cannot_be_reused_for_another_recipient(self):
        self.send()
        self.assertEqual(self.send(member="jonas").status_code, 409)
        self.assertEqual(len(self.chat.contexts), 1)

    def test_failure_retry_keeps_one_user_message_and_retains_spend(self):
        self.chat.failure = True
        self.assertEqual(self.send().status_code, 502)
        self.chat.failure = False
        retried = self.send()
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(len(retried.json()["messages"]), 2)
        self.assertAlmostEqual(self.store.spent(), 0.03)

    def test_disabled_budget_rejects_paid_calls_and_keeps_state_available(self):
        self.service.budget = 0
        self.assertEqual(self.send().status_code, 503)
        state = self.client.get(self.url)
        self.assertEqual(state.status_code, 200)
        self.assertFalse(state.json()["chatAvailable"])
        self.assertEqual(self.chat.contexts, [])

    def test_unknown_member_blank_message_and_oversized_message_do_not_call_model(self):
        self.assertEqual(self.send(member="someone-else").status_code, 404)
        self.assertEqual(self.send(text="  ").status_code, 422)
        self.assertEqual(self.send(text="x" * 2001).status_code, 422)
        self.assertEqual(self.chat.contexts, [])

    def test_session_cannot_be_opened_in_another_building(self):
        response = self.client.get(f"/api/buildings/another/coworkers/sessions/{self.state['sessionId']}")
        self.assertEqual(response.status_code, 404)

    def test_expired_session_is_rejected(self):
        with patch("building_api.coworker_store.time.time", return_value=time.time() + 86401):
            self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_restart_keeps_messages_and_global_budget(self):
        self.send()
        restarted = CoworkerService(self.database, store=CoworkerStore(self.store.path), chat=OfflineChat(), budget=5)
        self.assertEqual(len(restarted.state(self.building_id, self.state["sessionId"]).messages), 2)
        self.assertAlmostEqual(restarted.store.spent(), 0.01)

    def test_interrupted_turn_reservation_cannot_be_reclaimed_by_a_new_session(self):
        from building_api.coworker_models import SendMessage

        self.store.begin(
            self.state["sessionId"], SendMessage(member_id="maya", text="Hi", request_id="request-number-0001"), 5
        )
        self.assertAlmostEqual(CoworkerStore(self.store.path).spent(), 0.50)
        self.client.post(self.base)
        self.assertAlmostEqual(self.store.spent(), 0.50)

    def test_hidden_time_does_not_freeze_the_workday(self):
        day = self.service.workday(self.building_id)
        started = self.store.session(self.building_id, self.state["sessionId"])
        before = day.state(started, started + 1000)[0]
        after = day.state(started, started + 5000)[0]
        self.assertNotEqual(before.position, after.position)
        self.assertEqual(after, day.state(started, started + 5000)[0])

    def test_abandoned_attempt_can_retry_without_releasing_spend_or_accepting_a_late_reply(self):
        from building_api.coworker_models import SendMessage

        message = SendMessage(member_id="maya", text="Hi", request_id="request-number-0001")
        session_id = self.state["sessionId"]
        attempt = self.store.begin(session_id, message, 5)
        with patch("building_api.coworker_store.time.time", return_value=time.time() + 121):
            next_attempt = CoworkerStore(self.store.path).begin(session_id, message, 5)
        self.assertAlmostEqual(self.store.spent(), 1)
        self.store.finish(session_id, message.request_id, attempt_id=attempt, reply="Late reply", cost=0.01)
        self.assertEqual(len(self.store.messages(session_id)), 1)
        self.store.finish(session_id, message.request_id, attempt_id=next_attempt, reply="Retry reply", cost=0.01)
        self.assertAlmostEqual(self.store.spent(), 0.51)
        self.assertEqual(self.store.messages(session_id)[-1].text, "Retry reply")

    def test_cancelled_reply_can_retry_with_a_new_reservation(self):
        import asyncio

        from building_api.coworker_models import SendMessage

        async def cancelled(context):
            raise asyncio.CancelledError

        self.chat.reply = cancelled
        message = SendMessage(member_id="maya", text="Hi", request_id="request-number-0001")
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(self.service.send(self.building_id, self.state["sessionId"], message))
        self.assertAlmostEqual(self.store.spent(), 0.50)
        self.chat.reply = OfflineChat().reply
        self.assertEqual(self.send(text="Hi").status_code, 200)
        self.assertAlmostEqual(self.store.spent(), 0.51)

    def test_floor_change_holds_position_until_arrival(self):
        day = self.service.workday(self.building_id)
        floors = day.building.floors[:2]
        spaces = [day.building.spaces_on(floor.id)[0] for floor in floors]
        if len(spaces) != 2:
            self.fail("Fixture must have two floors")
        from building_tools.walks import anchor

        points = [
            WalkPoint(space.floor_id, *anchor(day.building.polygon_by_id[space.id]), space.id) for space in spaces
        ]
        day.paths["maya"] = points
        midway = day.member(PERSONAS[0], 0, 4000, 0)
        arrived = day.member(PERSONAS[0], 0, 8000, 0)
        self.assertEqual(midway.position.floor_id, spaces[0].floor_id)
        self.assertEqual(arrived.position.floor_id, spaces[1].floor_id)


class WalkingGeometryTest(unittest.TestCase):
    def test_concave_room_walk_goes_around_the_corner(self):
        polygon = Polygon([(0, 0), (3, 0), (3, 1), (1, 1), (1, 3), (0, 3)])
        path = inside_path(polygon, (0.5, 2.5), (2.5, 0.5))
        self.assertGreater(len(path), 2)
        self.assertTrue(polygon.buffer(0.02).covers(LineString(path)))

    def test_disconnected_geometry_never_becomes_a_straight_line(self):
        import networkx as nx

        polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        with self.assertRaises(nx.NetworkXNoPath):
            inside_path(polygon, (0.5, 0.5), (4, 4))

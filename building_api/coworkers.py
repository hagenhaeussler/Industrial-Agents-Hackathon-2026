"""Session-scoped AI coworkers. Building data stays read-only; messages use a separate SQLite store."""

import asyncio
import os
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParameter
from starlette.concurrency import run_in_threadpool

from building_api.coworker_chat import ChatContext, CoworkerChat, Reply
from building_api.coworker_models import SendMessage, SessionState
from building_api.coworker_movement import Workday
from building_api.coworker_store import TURN_RESERVATION_USD, CoworkerStore
from building_db.store import connect_readonly
from building_tools.building import ToolInputError, load

SessionId = Annotated[str, PathParameter(min_length=32, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")]


class CoworkerService:
    def __init__(
        self,
        database: Path,
        *,
        store: CoworkerStore | None = None,
        chat: CoworkerChat | None = None,
        budget: float | None = None,
    ):
        self.database = database
        self.store = store or CoworkerStore(
            Path(os.getenv("COWORKER_DATABASE", str(database.with_suffix(".coworkers.sqlite3"))))
        )
        self.chat = chat or CoworkerChat()
        self.budget = float(os.getenv("COWORKER_BUDGET_USD", "0")) if budget is None else budget
        self.preparation_lock = Lock()
        self.days: OrderedDict[str, Workday] = OrderedDict()
        self.reply_lock = asyncio.Lock()

    def workday(self, building_id: str) -> Workday:
        with self.preparation_lock:
            if building_id in self.days:
                self.days.move_to_end(building_id)
                return self.days[building_id]
            db = connect_readonly(self.database)
            try:
                day = Workday(load(db, building_id))
            except ToolInputError:
                raise HTTPException(404, "This building is not stored.") from None
            finally:
                db.close()
            self.days[building_id] = day
            if len(self.days) > 8:
                self.days.popitem(last=False)
            return day

    def state(self, building_id: str, session_id: str) -> SessionState:
        started_at = self.store.session(building_id, session_id)
        now = time.time() * 1000
        total = self.store.spent()
        reason = None
        if not self.chat.available:
            reason = "AI coworker replies are not configured on this server."
        elif total + TURN_RESERVATION_USD > self.budget:
            reason = "The coworker model budget is used up. Walking and existing chats still work."
        return SessionState(
            session_id=session_id,
            server_time=now,
            members=self.workday(building_id).state(started_at, now),
            messages=self.store.messages(session_id),
            chat_available=reason is None,
            unavailable_reason=reason,
            total_cost_usd=round(total, 6),
        )

    def create(self, building_id: str) -> SessionState:
        self.workday(building_id)
        return self.state(building_id, self.store.create(building_id))

    async def send(self, building_id: str, session_id: str, message: SendMessage) -> SessionState:
        message = message.model_copy(update={"text": message.text.strip()})
        if not message.text:
            raise HTTPException(422, "Write a message first.")
        state = await run_in_threadpool(self.state, building_id, session_id)
        member = next((member for member in state.members if member.id == message.member_id), None)
        if member is None:
            raise HTTPException(404, "This AI coworker is not in the building.")
        if self.store.completed(session_id, message):
            return state
        if not state.chat_available:
            raise HTTPException(503, state.unavailable_reason)
        if self.reply_lock.locked():
            raise HTTPException(429, "An AI coworker is answering another message. Please retry shortly.")
        async with self.reply_lock:
            attempt_id = self.store.begin(session_id, message, self.budget)
            if attempt_id is None:
                return await run_in_threadpool(self.state, building_id, session_id)
            workday = self.workday(building_id)
            started_at = self.store.session(building_id, session_id)

            def location():
                return next(
                    member for member in workday.state(started_at, time.time() * 1000) if member.id == message.member_id
                )

            messages = [item for item in self.store.messages(session_id) if item.member_id == member.id]
            current_message = next(item for item in messages if item.id == message.request_id)
            context = ChatContext(
                building=workday.building,
                member=member,
                history=[item for item in messages if item.id != message.request_id] + [current_message],
                location=location,
            )
            try:
                reply = await asyncio.wait_for(self.chat.reply(context), timeout=60)
            except asyncio.CancelledError:
                self.store.finish(session_id, message.request_id, attempt_id=attempt_id, reply=None, cost=None)
                raise
            except Exception:  # noqa: BLE001 - keep uncertain provider spend reserved after timeout or setup failure
                reply = Reply(
                    None, None, "The AI reply stopped before it could be confirmed. You can retry this message."
                )
            self.store.finish(session_id, message.request_id, attempt_id=attempt_id, reply=reply.text, cost=reply.cost)
            if reply.error:
                raise HTTPException(502, reply.error)
        return await run_in_threadpool(self.state, building_id, session_id)


def coworker_router(service: CoworkerService) -> APIRouter:
    router = APIRouter(prefix="/api/buildings/{building_id}/coworkers/sessions", tags=["AI coworkers"])

    @router.post("", status_code=201, response_model=SessionState)
    def create_session(building_id: str):
        return service.create(building_id)

    @router.get("/{session_id}", response_model=SessionState)
    def get_session(building_id: str, session_id: SessionId):
        return service.state(building_id, session_id)

    @router.post("/{session_id}/messages", response_model=SessionState)
    async def send_message(building_id: str, session_id: SessionId, message: SendMessage):
        return await service.send(building_id, session_id, message)

    return router

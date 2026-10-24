"""One-process WebSocket fan-out; schedule only after database commit."""
import asyncio
import anyio
from collections import defaultdict
from contextlib import suppress
import logging

from fastapi import WebSocket, WebSocketDisconnect

from .public import public_payload

logger = logging.getLogger(__name__)


class BuildingHub:
    def __init__(self):
        self.subscribers = defaultdict(set)
        self.loop = None
        self.send_locks = {}
        self.pending = set()

    def start(self):
        self.loop = asyncio.get_running_loop()

    def notify(self, building_id, message):
        if self.loop and not self.loop.is_closed():
            # Calls originate in FastAPI's geometry/DB worker threads.
            future = asyncio.run_coroutine_threadsafe(self.broadcast(building_id, message), self.loop)
            self.pending.add(future)
            future.add_done_callback(self.pending.discard)

    async def broadcast(self, building_id, message):
        message = public_payload(message)
        async def send(socket):
            try:
                async with self.send_locks[socket]:
                    await asyncio.wait_for(socket.send_json(message), timeout=2)
            except Exception:
                self.subscribers[building_id].discard(socket)
        await asyncio.gather(*(send(socket) for socket in tuple(self.subscribers[building_id])))

    async def connection(self, socket: WebSocket, building_id, version_getter):
        await socket.accept()
        send_lock = asyncio.Lock()
        # Register before fetching the version; a concurrent commit is either
        # covered by hello or queued behind it, never lost in a subscribe gap.
        try:
            async with send_lock:
                self.send_locks[socket] = send_lock
                self.subscribers[building_id].add(socket)
                version = await anyio.to_thread.run_sync(version_getter)
                await socket.send_json({'type': 'hello', 'building_id': building_id, 'building_version': version})
            while True:
                try:
                    message = await asyncio.wait_for(socket.receive_text(), timeout=20)
                    if message == 'ping':
                        async with send_lock:
                            await socket.send_json({'type': 'pong'})
                except asyncio.TimeoutError:
                    async with send_lock:
                        await socket.send_json({'type': 'ping'})
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            self.subscribers[building_id].discard(socket)
            self.send_locks.pop(socket, None)

    async def close(self):
        for future in tuple(self.pending):
            with suppress(Exception):
                await asyncio.wrap_future(future)
        await asyncio.gather(*(socket.close(code=1001) for group in self.subscribers.values() for socket in tuple(group)), return_exceptions=True)
        self.subscribers.clear()
        self.loop = None

"""Private sessions and a persistent spend ledger, separate from the read-only building data."""

import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from building_api.coworker_models import ChatMessage, SendMessage

SESSION_SECONDS = 24 * 60 * 60
MAX_SESSIONS = 2000
MAX_MESSAGES_PER_MEMBER = 60
TURN_RESERVATION_USD = 0.50
ATTEMPT_SECONDS = 120


class CoworkerStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS coworker_sessions (
                    id TEXT PRIMARY KEY, building_id TEXT NOT NULL, started_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS coworker_turns (
                    session_id TEXT NOT NULL, request_id TEXT NOT NULL, member_id TEXT NOT NULL,
                    text TEXT NOT NULL, reply TEXT, created_at REAL NOT NULL, replied_at REAL,
                    status TEXT NOT NULL, cost REAL NOT NULL DEFAULT 0, reserved REAL NOT NULL DEFAULT 0,
                    attempt_id TEXT, attempted_at REAL,
                    PRIMARY KEY (session_id, request_id)
                );
            """)
            columns = {column[1] for column in db.execute("PRAGMA table_info(coworker_turns)")}
            for name, kind in (("attempt_id", "TEXT"), ("attempted_at", "REAL")):
                if name not in columns:
                    db.execute(f"ALTER TABLE coworker_turns ADD COLUMN {name} {kind}")
            yield db
        finally:
            db.close()

    def create(self, building_id: str) -> str:
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM coworker_sessions").fetchone()[0]
            if count >= MAX_SESSIONS:
                raise HTTPException(503, "The coworker preview has reached its session limit.")
            session_id = secrets.token_urlsafe(32)
            db.execute("INSERT INTO coworker_sessions VALUES (?, ?, ?)", (session_id, building_id, time.time() * 1000))
            return session_id

    def session(self, building_id: str, session_id: str) -> float:
        with self.connection() as db:
            found = db.execute(
                "SELECT started_at FROM coworker_sessions WHERE id = ? AND building_id = ?", (session_id, building_id)
            ).fetchone()
        if found is None or time.time() * 1000 - found[0] > SESSION_SECONDS * 1000:
            raise HTTPException(404, "This coworker session has expired. Start a new session.")
        return found[0]

    def messages(self, session_id: str) -> list[ChatMessage]:
        with self.connection() as db:
            turns = db.execute(
                "SELECT * FROM coworker_turns WHERE session_id = ? ORDER BY created_at, request_id", (session_id,)
            ).fetchall()
        messages = []
        for turn in turns:
            messages.append(
                ChatMessage(
                    id=turn["request_id"],
                    member_id=turn["member_id"],
                    role="user",
                    text=turn["text"],
                    created_at=turn["created_at"],
                )
            )
            if turn["reply"] is not None:
                messages.append(
                    ChatMessage(
                        id="reply:" + turn["request_id"],
                        member_id=turn["member_id"],
                        role="assistant",
                        text=turn["reply"],
                        created_at=turn["replied_at"],
                    )
                )
        return messages

    def spent(self) -> float:
        with self.connection() as db:
            return db.execute("SELECT COALESCE(SUM(cost + reserved), 0) FROM coworker_turns").fetchone()[0]

    def completed(self, session_id: str, message: SendMessage) -> bool:
        with self.connection() as db:
            turn = db.execute(
                "SELECT * FROM coworker_turns WHERE session_id = ? AND request_id = ?", (session_id, message.request_id)
            ).fetchone()
        if turn and (turn["member_id"] != message.member_id or turn["text"] != message.text):
            raise HTTPException(409, "This request ID belongs to a different message.")
        return bool(turn and turn["status"] == "done")

    def begin(self, session_id: str, message: SendMessage, budget: float) -> str | None:
        """Reserve a turn before calling a provider. Retries reuse the user message and retain prior spend."""
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT * FROM coworker_turns WHERE session_id = ? AND request_id = ?", (session_id, message.request_id)
            ).fetchone()
            if previous:
                if previous["member_id"] != message.member_id or previous["text"] != message.text:
                    raise HTTPException(409, "This request ID belongs to a different message.")
                if previous["status"] == "done":
                    return None
                if previous["status"] == "pending":
                    if previous["attempted_at"] and time.time() - previous["attempted_at"] < ATTEMPT_SECONDS:
                        raise HTTPException(409, "This message is still being answered.")
                    # Keep the full uncertain charge before reserving a separate retry.
                    db.execute(
                        "UPDATE coworker_turns SET cost = cost + reserved, reserved = 0, status = 'failed'"
                        " WHERE session_id = ? AND request_id = ?",
                        (session_id, message.request_id),
                    )
            count = db.execute(
                "SELECT COUNT(*) FROM coworker_turns WHERE session_id = ? AND member_id = ?",
                (session_id, message.member_id),
            ).fetchone()[0]
            if previous is None and count * 2 >= MAX_MESSAGES_PER_MEMBER:
                raise HTTPException(409, "This conversation is full. Start a new coworker session to continue.")
            total = db.execute("SELECT COALESCE(SUM(cost + reserved), 0) FROM coworker_turns").fetchone()[0]
            if total + TURN_RESERVATION_USD > budget:
                raise HTTPException(
                    429, "The coworker preview's model budget is used up. Walking and existing chats still work."
                )
            attempt_id = secrets.token_urlsafe(24)
            if previous:
                db.execute(
                    "UPDATE coworker_turns SET status = 'pending', reserved = ?, attempt_id = ?, attempted_at = ?"
                    " WHERE session_id = ? AND request_id = ?",
                    (TURN_RESERVATION_USD, attempt_id, time.time(), session_id, message.request_id),
                )
            else:
                db.execute(
                    "INSERT INTO coworker_turns"
                    " (session_id, request_id, member_id, text, created_at, status, reserved, attempt_id, attempted_at)"
                    " VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
                    (
                        session_id,
                        message.request_id,
                        message.member_id,
                        message.text,
                        time.time() * 1000,
                        TURN_RESERVATION_USD,
                        attempt_id,
                        time.time(),
                    ),
                )
            return attempt_id

    def finish(
        self, session_id: str, request_id: str, *, attempt_id: str, reply: str | None, cost: float | None
    ) -> None:
        # An interrupted or unpriced run keeps its full reservation. Never assume it was free.
        charge = TURN_RESERVATION_USD if cost is None else max(0, cost)
        with self.connection() as db, db:
            db.execute(
                "UPDATE coworker_turns SET reply = ?, replied_at = ?, status = ?, cost = cost + ?, reserved = 0"
                " WHERE session_id = ? AND request_id = ? AND status = 'pending' AND attempt_id = ?",
                (reply, time.time() * 1000, "done" if reply else "failed", charge, session_id, request_id, attempt_id),
            )

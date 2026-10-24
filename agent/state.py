"""Durable agent turns, whole-turn history and confirmation state in SQLite."""

from contextlib import contextmanager
from dataclasses import dataclass
import json
import re
import threading
import weakref

from server.errors import ServiceError
from server.state import StateStore, encode, identifier, now


CONFIRMATION = re.compile(r"\s*(?:yes(?: please)?|yes,? apply (?:it|the change)|confirm|apply it|go ahead|ja(?: bitte)?|bestätigen)\s*[.!]?\s*", re.I)
HISTORY_BYTES = 100_000
HISTORY_TURNS = 12


@dataclass(frozen=True)
class TurnState:
    turn_id: str
    session_id: str
    authorized_proposal: str | None


class AgentState:
    def __init__(self, store: StateStore):
        self.store = store
        self._locks = weakref.WeakValueDictionary()
        self._guard = threading.Lock()

    def initialize(self) -> None:
        with self.store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS agent_threads(
                    session_id TEXT PRIMARY KEY, active_turn_id TEXT,
                    pending_proposal TEXT);
                CREATE TABLE IF NOT EXISTS agent_turns(
                    turn_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                    message TEXT NOT NULL, channel TEXT NOT NULL,
                    authorized_proposal TEXT, messages_json TEXT NOT NULL DEFAULT '[]',
                    observations_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS agent_turn_session
                    ON agent_turns(session_id, created_at);
                CREATE TABLE IF NOT EXISTS agent_budgets(
                    allocation_id TEXT PRIMARY KEY, dollar_limit REAL NOT NULL,
                    spent REAL NOT NULL DEFAULT 0);
            """)

    @contextmanager
    def lock(self, session_id: str):
        with self._guard:
            lock = self._locks.setdefault(session_id, threading.RLock())
        with lock:
            yield

    def begin(self, session_id: str, message: str, channel: str) -> TurnState:
        turn_id = identifier("turn")
        with self.store.connect(write=True) as db:
            previous = db.execute("SELECT pending_proposal FROM agent_threads WHERE session_id=?", (session_id,)).fetchone()
            authorized = previous[0] if previous and CONFIRMATION.fullmatch(message) else None
            db.execute("INSERT INTO agent_threads VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET active_turn_id=excluded.active_turn_id,pending_proposal=excluded.pending_proposal",
                       (session_id, turn_id, authorized))
            db.execute("INSERT INTO agent_turns(turn_id,session_id,message,channel,authorized_proposal,created_at) VALUES(?,?,?,?,?,?)",
                       (turn_id, session_id, message, channel, authorized, now()))
            db.execute("DELETE FROM agent_turns WHERE session_id=? AND turn_id NOT IN (SELECT turn_id FROM agent_turns WHERE session_id=? ORDER BY created_at DESC LIMIT ?)",
                       (session_id, session_id, HISTORY_TURNS + 1))
        return TurnState(turn_id, session_id, authorized)

    def require_current(self, session_id: str, turn_id: str) -> TurnState:
        with self.store.connect() as db:
            row = db.execute("SELECT t.authorized_proposal FROM agent_turns t JOIN agent_threads h USING(session_id) WHERE t.turn_id=? AND t.session_id=? AND h.active_turn_id=t.turn_id",
                             (turn_id, session_id)).fetchone()
        if row is None:
            raise ServiceError("version_conflict", "This agent turn was superseded. Use the latest user message.", status=409)
        return TurnState(turn_id, session_id, row[0])

    def remember_proposal(self, turn: TurnState, proposal_id: str | None) -> None:
        with self.store.connect(write=True) as db:
            db.execute("UPDATE agent_threads SET pending_proposal=? WHERE session_id=? AND active_turn_id=?",
                       (proposal_id, turn.session_id, turn.turn_id))
            if proposal_id is not None:
                db.execute("UPDATE agent_turns SET authorized_proposal=NULL WHERE turn_id=?", (turn.turn_id,))

    def record_observation(self, turn: TurnState, observation: dict) -> None:
        with self.store.connect(write=True) as db:
            row = db.execute("SELECT observations_json FROM agent_turns WHERE turn_id=?", (turn.turn_id,)).fetchone()
            observations = json.loads(row[0])
            observations.append(observation)
            # Each history entry is a whole observation. Current responses are never sliced.
            while len(encode(observations).encode()) > HISTORY_BYTES and observations:
                observations.pop(0)
            db.execute("UPDATE agent_turns SET observations_json=? WHERE turn_id=?", (encode(observations), turn.turn_id))

    def save_messages(self, turn_id: str, messages: list[dict]) -> None:
        body = encode(messages)
        # An oversized turn stays available through tool/API results, without making
        # every later provider request exceed the context budget.
        if len(body.encode()) > HISTORY_BYTES:
            return
        with self.store.connect(write=True) as db:
            db.execute("UPDATE agent_turns SET messages_json=? WHERE turn_id=?", (body, turn_id))

    def history(self, turn: TurnState) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute("SELECT message,messages_json,observations_json FROM agent_turns WHERE session_id=? AND turn_id!=? ORDER BY created_at DESC LIMIT ?",
                              (turn.session_id, turn.turn_id, HISTORY_TURNS)).fetchall()
        groups, size = [], 0
        for row in rows:
            messages = json.loads(row["messages_json"])
            observations = json.loads(row["observations_json"])
            if not messages and observations:
                messages = [{"role": "user", "content": row["message"]},
                            {"role": "assistant", "content": "Previous voice tool results (data):\n" + encode(observations)}]
            amount = len(encode(messages).encode())
            if size + amount > HISTORY_BYTES:
                break
            size += amount
            groups.append(messages)
        return [message for group in reversed(groups) for message in group]

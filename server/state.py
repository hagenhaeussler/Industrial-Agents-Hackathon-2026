"""Durable, transactional state. Kit files and benchmark runs never write here."""
from contextlib import contextmanager
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import secrets
import uuid

from server.errors import ServiceError


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix):
    """Generate public IDs in the formats frozen in CONTRACTS C1 §1."""
    if prefix == "session":
        return uuid.uuid4().hex
    if prefix == "op":
        return str(uuid.uuid4())
    formats = {"tour": ("", 10), "proposal": ("prp_", 12), "req": ("req_", 12), "marker": ("mk_", 8)}
    if prefix in formats:
        label, length = formats[prefix]
        token = base64.b32encode(secrets.token_bytes(8)).decode("ascii").lower().rstrip("=")
        return label + token[:length]
    return f"{prefix}_{uuid.uuid4().hex}"


def encode(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


class StateStore:
    def __init__(self, state_dir: Path):
        self.directory = Path(state_dir)
        self.path = self.directory / "tyb.sqlite3"

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        for folder in ("uploads", "derived"):
            (self.directory / folder).mkdir(exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS buildings(
                    id TEXT PRIMARY KEY, source TEXT, path TEXT, content_hash TEXT,
                    name TEXT, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    building_id TEXT NOT NULL, building_version INTEGER NOT NULL,
                    event_id TEXT NOT NULL, kind TEXT NOT NULL, edit_json TEXT NOT NULL,
                    undoes TEXT, op_id TEXT UNIQUE, proposal_id TEXT UNIQUE, session_id TEXT NOT NULL,
                    author_role TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0);
                CREATE UNIQUE INDEX IF NOT EXISTS active_versions
                    ON events(building_id, building_version) WHERE archived=0;
                CREATE TABLE IF NOT EXISTS proposals(
                    proposal_id TEXT PRIMARY KEY, building_id TEXT NOT NULL, edit_json TEXT NOT NULL,
                    base_version INTEGER NOT NULL, op_id TEXT UNIQUE, session_id TEXT NOT NULL,
                    summary TEXT NOT NULL, effects_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL, committed_event_id TEXT);
                CREATE TABLE IF NOT EXISTS sessions(
                    session_id TEXT PRIMARY KEY, building_id TEXT NOT NULL, device TEXT NOT NULL,
                    role TEXT NOT NULL, profile TEXT NOT NULL, constraints_json TEXT NOT NULL,
                    position_json TEXT, active_tour_id TEXT, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tours(
                    tour_id TEXT NOT NULL, building_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    session_id TEXT NOT NULL, body_json TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(tour_id, revision));
                CREATE TABLE IF NOT EXISTS markers(
                    marker_id TEXT PRIMARY KEY, building_id TEXT NOT NULL, body_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS derived_cache(
                    content_hash TEXT NOT NULL, key TEXT NOT NULL, blob BLOB NOT NULL,
                    PRIMARY KEY(content_hash, key));
            """)
        self._migrate_events()

    def _migrate_events(self):
        """Schema 2 allows evt-1 in each building and again after a demo reset."""
        with self.connect(write=True) as db:
            columns = {row["name"]: row for row in db.execute("PRAGMA table_info(events)")}
            if "row_id" not in columns:
                db.execute("""CREATE TABLE events_v2(
                    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    building_id TEXT NOT NULL, building_version INTEGER NOT NULL,
                    event_id TEXT NOT NULL, kind TEXT NOT NULL, edit_json TEXT NOT NULL,
                    undoes TEXT, op_id TEXT UNIQUE, proposal_id TEXT UNIQUE, session_id TEXT NOT NULL,
                    author_role TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0)""")
                fields = "building_id,building_version,event_id,kind,edit_json,undoes,op_id,proposal_id,session_id,author_role,summary,created_at,archived"
                db.execute(f"INSERT INTO events_v2({fields}) SELECT {fields} FROM events")
                db.execute("DROP TABLE events")
                db.execute("ALTER TABLE events_v2 RENAME TO events")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS active_versions ON events(building_id, building_version) WHERE archived=0")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS active_event_ids ON events(building_id, event_id) WHERE archived=0")
            db.execute("DELETE FROM schema_version")
            db.execute("INSERT INTO schema_version VALUES(2)")

    @contextmanager
    def connect(self, *, write=False):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _session(row):
        if row is None:
            raise ServiceError("not_found", "Session not found.", status=404)
        body = dict(row)
        body["constraints"] = json.loads(body.pop("constraints_json"))
        body["position"] = json.loads(body.pop("position_json") or "null")
        return body

    def create_session(self, building_id, device, role, profile="walk", constraints=None):
        sid = identifier("session")
        with self.connect(write=True) as db:
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)", (
                sid, building_id, device, role, profile, encode(constraints or {}), None, None, now()))
        return self.get_session(sid)

    def get_session(self, session_id):
        with self.connect() as db:
            return self._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())

    def update_session(self, session_id, patch):
        allowed = {"profile", "constraints", "position", "active_tour_id"}
        if set(patch) - allowed:
            raise ServiceError("invalid_args", "Unsupported session fields.")
        with self.connect(write=True) as db:
            session = self._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())
            session.update(patch)
            db.execute("UPDATE sessions SET profile=?,constraints_json=?,position_json=?,active_tour_id=?,updated_at=? WHERE session_id=?", (
                session["profile"], encode(session["constraints"]), encode(session["position"]), session["active_tour_id"], now(), session_id))
        return self.get_session(session_id)

    @staticmethod
    def _event(row):
        if row is None:
            return None
        body = dict(row)
        body["edit"] = json.loads(body.pop("edit_json"))
        body.pop("archived", None)
        body.pop("row_id", None)
        return body

    def events(self, building_id, since=0):
        with self.connect() as db:
            return [self._event(row) for row in db.execute(
                "SELECT * FROM events WHERE building_id=? AND archived=0 AND building_version>? ORDER BY building_version", (building_id, since))]

    @staticmethod
    def _version(db, building_id):
        return db.execute("SELECT COALESCE(MAX(building_version),0) FROM events WHERE building_id=? AND archived=0", (building_id,)).fetchone()[0]

    def version(self, building_id):
        with self.connect() as db:
            return self._version(db, building_id)

    def propose(self, session_id, edit, base_version, summary, effects, op_id=None):
        pid = identifier("proposal")
        with self.connect(write=True) as db:
            session = self._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())
            self._require_admin(session)
            created = datetime.now(timezone.utc)
            if self._version(db, session["building_id"]) != base_version:
                raise ServiceError("version_conflict", "Building changed; request a fresh preview.", status=409)
            if op_id:
                previous = db.execute("SELECT * FROM proposals WHERE op_id=?", (op_id,)).fetchone()
                if previous:
                    if (previous["session_id"] != session_id or previous["base_version"] != base_version
                            or json.loads(previous["edit_json"]) != edit):
                        raise ServiceError("invalid_args", "Operation ID belongs to a different preview.")
                    if datetime.fromisoformat(previous["expires_at"]) <= created:
                        raise ServiceError("version_conflict", "Preview expired; request a fresh preview.", status=409)
                    return {"proposal_id": previous["proposal_id"], "edit": json.loads(previous["edit_json"]),
                            "summary": previous["summary"], "base_version": previous["base_version"],
                            "effects": json.loads(previous["effects_json"])}
            db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                pid, session["building_id"], encode(edit), base_version, op_id, session_id, summary,
                encode(effects), created.isoformat(), (created + timedelta(minutes=10)).isoformat(), None))
        return {"proposal_id": pid, "edit": edit, "summary": summary, "base_version": base_version, "effects": effects}

    @staticmethod
    def _require_admin(session):
        if session["role"] != "admin":
            raise ServiceError("forbidden", "Changes need an admin session.", status=403)

    def commit(self, session_id, proposal_id, expected_version=None, op_id=None):
        """Return (event, newly_committed); repeat requests return the original event."""
        with self.connect(write=True) as db:
            session = self._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())
            self._require_admin(session)
            proposal = db.execute("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not proposal or proposal["session_id"] != session_id or proposal["building_id"] != session["building_id"]:
                raise ServiceError("not_found", "Proposal not found in this session.", status=404)
            duplicate = db.execute("SELECT * FROM events WHERE proposal_id=? AND building_id=? AND archived=0", (proposal_id, session["building_id"])).fetchone()
            if duplicate:
                return self._event(duplicate), False
            operation = op_id or proposal["op_id"] or identifier("op")
            duplicate = db.execute("SELECT * FROM events WHERE op_id=? AND building_id=? AND archived=0", (operation, session["building_id"])).fetchone()
            if duplicate:
                if duplicate["proposal_id"] != proposal_id:
                    raise ServiceError("invalid_args", "Operation ID belongs to a different proposal.")
                return self._event(duplicate), False
            if db.execute("SELECT 1 FROM events WHERE op_id=?", (operation,)).fetchone():
                raise ServiceError("invalid_args", "Operation ID belongs to a different proposal or archived change.")
            version = self._version(db, session["building_id"])
            expected = proposal["base_version"] if expected_version is None else expected_version
            if expected != version or proposal["base_version"] != version:
                raise ServiceError("version_conflict", "Building changed; request a fresh preview.", status=409, building_version=version)
            if datetime.fromisoformat(proposal["expires_at"]) <= datetime.now(timezone.utc):
                raise ServiceError("version_conflict", "Preview expired; request a fresh preview.", status=409, building_version=version)
            edit = json.loads(proposal["edit_json"])
            event_id = f"evt-{version + 1}"
            db.execute("INSERT INTO events(building_id,building_version,event_id,kind,edit_json,undoes,op_id,proposal_id,session_id,author_role,summary,created_at,archived) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)", (
                session["building_id"], version + 1, event_id, edit["action"], encode(edit), None,
                operation, proposal_id, session_id, "admin", proposal["summary"], now()))
            db.execute("UPDATE proposals SET committed_event_id=? WHERE proposal_id=?", (event_id, proposal_id))
            return self._event(db.execute("SELECT * FROM events WHERE event_id=? AND building_id=? AND archived=0", (event_id, session["building_id"])).fetchone()), True

    def undo(self, session_id, event_id=None, op_id=None, expected_version=None):
        with self.connect(write=True) as db:
            session = self._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())
            self._require_admin(session)
            if op_id:
                existing = db.execute("SELECT * FROM events WHERE op_id=? AND building_id=? AND archived=0", (op_id, session["building_id"])).fetchone()
                if existing:
                    if existing["session_id"] != session_id or existing["kind"] != "undo":
                        raise ServiceError("invalid_args", "Operation ID belongs to a different change.")
                    return self._event(existing), False
                if db.execute("SELECT 1 FROM events WHERE op_id=?", (op_id,)).fetchone():
                    raise ServiceError("invalid_args", "Operation ID belongs to a different or archived change.")
            if event_id:
                event = db.execute("SELECT * FROM events WHERE event_id=? AND building_id=? AND archived=0", (event_id, session["building_id"])).fetchone()
            else:
                event = db.execute("""SELECT * FROM events e WHERE e.building_id=? AND e.session_id=? AND e.archived=0
                    AND e.kind!='undo' AND NOT EXISTS(SELECT 1 FROM events u WHERE u.undoes=e.event_id AND u.building_id=e.building_id AND u.archived=0)
                    ORDER BY e.building_version DESC LIMIT 1""", (session["building_id"], session_id)).fetchone()
            if not event or event["kind"] == "undo":
                raise ServiceError("not_found", "No change is available to undo.", status=404)
            if db.execute("SELECT 1 FROM events WHERE undoes=? AND building_id=? AND archived=0", (event["event_id"], session["building_id"])).fetchone():
                raise ServiceError("invalid_args", "This change has already been undone.")
            version = self._version(db, session["building_id"])
            if expected_version is not None and version != expected_version:
                raise ServiceError("version_conflict", "Building changed; review the undo again.", status=409, building_version=version)
            uid = f"evt-{version + 1}"
            db.execute("INSERT INTO events(building_id,building_version,event_id,kind,edit_json,undoes,op_id,proposal_id,session_id,author_role,summary,created_at,archived) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)", (
                session["building_id"], version + 1, uid, "undo", event["edit_json"], event["event_id"],
                op_id or identifier("op"), None, session_id, "admin", "Undo: " + event["summary"], now()))
            return self._event(db.execute("SELECT * FROM events WHERE event_id=? AND building_id=? AND archived=0", (uid, session["building_id"])).fetchone()), True

    def save_tour(self, session_id, tour, *, expected_revision=None):
        with self.connect(write=True) as db:
            session = self._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())
            tid = tour.get("tour_id") or identifier("tour")
            existing = db.execute("SELECT building_id, revision FROM tours WHERE tour_id=? ORDER BY revision DESC LIMIT 1", (tid,)).fetchone()
            if existing and existing["building_id"] != session["building_id"]:
                raise ServiceError("invalid_args", "Tour belongs to a different building.")
            latest = existing["revision"] if existing else None
            if expected_revision is not None and latest != expected_revision:
                raise ServiceError("version_conflict", "Tour changed; fetch its latest revision.", status=409)
            revision = 1 if latest is None else latest + 1
            body = {**tour, "tour_id": tid, "revision": revision, "building_id": session["building_id"]}
            db.execute("INSERT INTO tours VALUES(?,?,?,?,?,?)", (tid, session["building_id"], revision, session_id, encode(body), now()))
            return body

    def get_tour(self, tour_id):
        with self.connect() as db:
            row = db.execute("SELECT body_json FROM tours WHERE tour_id=? ORDER BY revision DESC LIMIT 1", (tour_id,)).fetchone()
            if not row:
                raise ServiceError("not_found", "Tour not found.", status=404)
            return json.loads(row[0])

    def active_tours(self, building_id):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("""SELECT t.body_json FROM tours t WHERE t.building_id=?
                AND t.revision=(SELECT MAX(n.revision) FROM tours n WHERE n.tour_id=t.tour_id)""", (building_id,))
                if json.loads(row[0]).get("status") != "completed"]

    def put_marker(self, marker):
        with self.connect(write=True) as db:
            existing = db.execute("SELECT building_id FROM markers WHERE marker_id=?", (marker["marker_id"],)).fetchone()
            if existing and existing["building_id"] != marker["building_id"]:
                raise ServiceError("invalid_args", "Marker belongs to a different building.")
            db.execute("INSERT INTO markers VALUES(?,?,?) ON CONFLICT(marker_id) DO UPDATE SET body_json=excluded.body_json", (
                marker["marker_id"], marker["building_id"], encode(marker)))
        return marker

    def get_marker(self, marker_id):
        with self.connect() as db:
            row = db.execute("SELECT body_json FROM markers WHERE marker_id=?", (marker_id,)).fetchone()
            if not row:
                raise ServiceError("not_found", "Position marker not found.", status=404)
            return json.loads(row[0])

    def markers(self, building_id):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body_json FROM markers WHERE building_id=? ORDER BY marker_id", (building_id,))]

    def reset(self, building_id):
        with self.connect(write=True) as db:
            db.execute("UPDATE events SET archived=1 WHERE building_id=?", (building_id,))
            db.execute("DELETE FROM proposals WHERE building_id=?", (building_id,))

    def cache_get(self, content_hash, key):
        with self.connect() as db:
            row = db.execute("SELECT blob FROM derived_cache WHERE content_hash=? AND key=?", (content_hash, key)).fetchone()
            return row[0] if row else None

    def cache_put(self, content_hash, key, blob):
        with self.connect(write=True) as db:
            db.execute("INSERT INTO derived_cache VALUES(?,?,?) ON CONFLICT(content_hash,key) DO UPDATE SET blob=excluded.blob", (content_hash, key, blob))

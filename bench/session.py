"""An isolated platform session built only from the supplied building."""

from contextlib import contextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.execution import AgentExecution
from agent.state import AgentState
from core.building import Building
from core.routing import normalize_constraints
from server.buildings import BuildingCatalog
from server.config import Settings
from server.service import PlatformService
from server.schemas import Constraints
from server.state import StateStore
from server.tools import ToolRegistry


@contextmanager
def submission_session(building: Building, constraints: dict | None = None):
    values = Constraints.model_validate({} if constraints is None else constraints, strict=True).model_dump()
    values = normalize_constraints(building, values)
    known_types = {room["room_type"] for room in building.spaces.values()}
    if set(values["no_transit_room_types"]) - known_types:
        raise ValueError("Unknown restricted room types.")
    with TemporaryDirectory(prefix="tyb-submission-") as directory:
        root = Path(directory)
        store = StateStore(root / "state")
        store.initialize()
        (store.directory / "uploads" / "building.json").write_text(json.dumps(building.data), encoding="utf-8")
        settings = Settings(data_dir=root / "empty", hero_dir=root / "empty", state_dir=store.directory)
        service = PlatformService(BuildingCatalog(settings), store)
        session = store.create_session(building.id, "desk", "navigator")
        session = store.update_session(session["session_id"], {"constraints": values})
        state = AgentState(store)
        state.initialize()
        execution = AgentExecution(ToolRegistry(service), store.get_session, state)
        yield execution, session["session_id"]

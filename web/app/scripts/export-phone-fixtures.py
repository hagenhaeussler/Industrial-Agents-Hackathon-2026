"""Generate the phone's C7 regression payloads through the actual HTTP API.

Run at repository root: .venv/bin/python web/app/scripts/export-phone-fixtures.py
Only temporary local state and navigator sessions are created; no providers run.
"""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from server.app import create_app
from server.config import Settings


def main():
    bid = "proc-factory-dev-003"
    start, end = f"{bid}-F0-S001", f"{bid}-F0-S002"
    with TemporaryDirectory(prefix="tyb-c7-phone-") as temporary:
        settings = Settings(state_dir=Path(temporary)/"state", hero_dir=Path(temporary)/"hero", static_dir=Path(temporary)/"dist")
        with TestClient(create_app(settings)) as client:
            def request(method, path, body, headers=None):
                response = client.request(method, path, json=body, headers=headers)
                response.raise_for_status()
                return response.json()

            session = request("POST", "/api/sessions", {"building_id": bid, "role": "navigator", "device": "phone"})
            sid = session["session_id"]
            position = {"space_id": start, "source": "manual", "confidence": "medium"}
            request("PATCH", f"/api/sessions/{sid}", {"position": position})
            before = request("POST", "/api/tours", {"session_id": sid, "items": [start], "end": end})
            path = f"/api/tours/{before['tour_id']}"
            headers = {"X-Session-ID": sid}
            final_leg = request("POST", path+"/progress", {"stop_id": before["stops"][0]["stop_id"], "status": "collected"}, headers)
            request("PATCH", f"/api/sessions/{sid}", {"constraints": {"closed": [end]}})
            blocked_end = request("POST", path+"/replan", {"session_id": sid, "from": position, "reason": "Final destination closed."})
            request("PATCH", f"/api/sessions/{sid}", {"constraints": {"closed": []}})
            reopened_end = request("POST", path+"/replan", {"session_id": sid, "from": position, "reason": "Final destination reopened.", "constraints": {"closed": []}})
            arrived = request("POST", path+"/progress", {"stop_id": "end", "status": "collected"}, headers)
            output = {"_fixture": {"producer": "actual FastAPI TestClient responses", "contract": "C7", "generated_by": ".venv/bin/python web/app/scripts/export-phone-fixtures.py"},
                      "before": before, "finalLeg": final_leg, "blockedEnd": blocked_end,
                      "reopenedEnd": reopened_end, "arrived": arrived}
            destination = ROOT/"web/app/src/phone/fixtures/final-destination-c7.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(output, indent=2)+"\n")
            print(destination)


if __name__ == "__main__":
    main()

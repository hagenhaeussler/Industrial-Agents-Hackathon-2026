# Add a building to a team

1. Open the preview root, click the orb, and select your team.
2. Choose **Create a new building**.
3. Choose the equipment CSV and structured floor-plan JSON in the two boxes.
4. Click **Upload and create building**. Enter the private building-access code if asked. The code is kept only in this browser tab's session storage; never put it in a URL or commit.
5. Review the validation notes and click **Open building**. The building also appears in your team's catalog and persists across service restarts.

Teams organize the shared preview catalog. They do not isolate access between coworkers. The existing server-side private code protects creation.

## Structured floor plan

Use the repository's kit-compatible building JSON format: `building`, `floors`, `spaces`, `doors` and other declared geometry. Coordinates are measured local metres, room outlines are polygons, room/floor IDs are stable, and doors/connections must represent actual traversable geometry. An existing kit or separately prepared draft can supply a valid example; do not overwrite the immutable kit data.

Maximum file size: 5 MB. Existing JSON `assets` are replaced by the separately supplied equipment list. The import never invents scale or routes from a photograph. This version accepts JSON rather than PDF/image drawings.

## Equipment CSV

Maximum size: 2 MB and 10,000 rows. UTF-8, with optional BOM. Required columns:

| Column | Meaning |
|---|---|
| `asset_id` | Unique equipment ID within this building |
| `name` | Human-readable name |
| `type` | Equipment type used by search |
| `space_id` | Exact existing room/space ID from the JSON |
| `x_m`, `y_m` | Finite measured coordinates inside that room, in the plan's coordinate system |

Optional columns: `floor_id` (must match the room), `category`, `width_m`, `depth_m`, `rotation_deg`. Positive dimensions default to 0.4 m when omitted; rotation defaults to zero. Empty lists, duplicate IDs, missing rooms, out-of-room positions and invalid geometry are rejected before any new building is saved. Each successful import gets a new upload ID and never overwrites a kit building.

The existing `demo/colab/equipment.csv` and building JSON provide a paired schematic example after the Colab integration. Its provenance and unmeasured dimensions remain explicit; use measured data for trusted navigation.

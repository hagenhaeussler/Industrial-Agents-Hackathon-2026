-- Building storage. Every row keeps its source ID from building.json.
-- Entity IDs are unique per building, so keys pair them with building_id.

CREATE TABLE buildings (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    source_ref TEXT NOT NULL,             -- JSON object, as in building.json
    license TEXT NOT NULL,
    attribution TEXT NOT NULL,
    split TEXT NOT NULL,
    units TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,         -- identity of the imported content
    source_path TEXT NOT NULL,
    calculation_version INTEGER NOT NULL  -- version of the derived-value functions
) STRICT;

CREATE TABLE floors (
    building_id TEXT NOT NULL REFERENCES buildings (id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    level INTEGER NOT NULL,
    name TEXT NOT NULL,
    elevation_m REAL NOT NULL,
    height_m REAL NOT NULL,
    PRIMARY KEY (building_id, id),
    UNIQUE (building_id, level)
) STRICT;

CREATE TABLE spaces (
    building_id TEXT NOT NULL,
    id TEXT NOT NULL,
    floor_id TEXT NOT NULL,
    type TEXT NOT NULL,
    room_type TEXT NOT NULL,
    name TEXT NOT NULL,
    ref TEXT NOT NULL,
    polygon TEXT NOT NULL,                -- JSON list of [x, y] points in metres
    synthetic INTEGER NOT NULL CHECK (synthetic IN (0, 1)),
    -- polygon_area is registered by building_db.store.connect. STORED computes it when the
    -- polygon is written, so readers without the function still see the value.
    area_m2 REAL GENERATED ALWAYS AS (polygon_area(polygon)) STORED,
    PRIMARY KEY (building_id, id),
    FOREIGN KEY (building_id, floor_id) REFERENCES floors (building_id, id) ON DELETE CASCADE
) STRICT;

CREATE INDEX spaces_by_floor ON spaces (building_id, floor_id);

-- An entrance's other side is the literal 'outside', so opening sides are checked on import
-- instead of by foreign keys.
CREATE TABLE openings (
    building_id TEXT NOT NULL,
    id TEXT NOT NULL,
    floor_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    space_a_id TEXT NOT NULL,
    space_b_id TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width_m REAL NOT NULL,
    step_free INTEGER NOT NULL CHECK (step_free IN (0, 1)),
    synthetic INTEGER NOT NULL CHECK (synthetic IN (0, 1)),
    PRIMARY KEY (building_id, id),
    FOREIGN KEY (building_id, floor_id) REFERENCES floors (building_id, id) ON DELETE CASCADE
) STRICT;

CREATE INDEX openings_by_floor ON openings (building_id, floor_id);

CREATE TABLE vertical_connectors (
    building_id TEXT NOT NULL REFERENCES buildings (id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    step_free INTEGER NOT NULL CHECK (step_free IN (0, 1)),
    synthetic INTEGER NOT NULL CHECK (synthetic IN (0, 1)),
    PRIMARY KEY (building_id, id)
) STRICT;

-- One row per floor a stair or lift serves, in source order.
CREATE TABLE connector_stops (
    building_id TEXT NOT NULL,
    connector_id TEXT NOT NULL,
    stop_index INTEGER NOT NULL,
    floor_id TEXT NOT NULL,
    space_id TEXT NOT NULL,
    PRIMARY KEY (building_id, connector_id, stop_index),
    FOREIGN KEY (building_id, connector_id) REFERENCES vertical_connectors (building_id, id) ON DELETE CASCADE,
    FOREIGN KEY (building_id, floor_id) REFERENCES floors (building_id, id) ON DELETE CASCADE,
    FOREIGN KEY (building_id, space_id) REFERENCES spaces (building_id, id) ON DELETE CASCADE
) STRICT;

CREATE TABLE assets (
    building_id TEXT NOT NULL,
    id TEXT NOT NULL,
    floor_id TEXT NOT NULL,
    space_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    type TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width_m REAL NOT NULL,
    depth_m REAL NOT NULL,
    rotation_deg REAL NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (building_id, id),
    FOREIGN KEY (building_id, floor_id) REFERENCES floors (building_id, id) ON DELETE CASCADE,
    FOREIGN KEY (building_id, space_id) REFERENCES spaces (building_id, id) ON DELETE CASCADE
) STRICT;

CREATE INDEX assets_by_space ON assets (building_id, space_id);

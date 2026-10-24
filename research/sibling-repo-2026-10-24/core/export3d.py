"""Export a building.json as a 3D model: OpenUSD (.usda, opens in NVIDIA Omniverse) and glTF (.glb, for the browser).

Rooms become thin floor slabs. Each floor gets one wall mesh with real gaps where the doors are; doors show as a
threshold plus a lintel, coloured by step_free. Stairs become flights of steps between floors, lifts translucent shafts,
and every asset a box with its real footprint. Floors sit at their elevation_m, so the model stacks like the building.
With --route, the shortest route (same cost model as the benchmark) is drawn as a tube with start and end markers.

Run:  uv run python -m core.export3d data/dev/proc-factory-dev-003 [--out agent_output/3d] [--explode 4]
      uv run python -m core.export3d data/dev/proc-factory-dev-003 --route "Lobby 0.01" "1.20" --step-free
"""

import argparse
import itertools
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
import trimesh
from pxr import Sdf, Usd, UsdGeom, Vt
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box

from starter_agent.building_map import DOOR_PREFIX, OUTSIDE, BuildingMap, RouteResult

DEFAULT_OUTPUT_DIRECTORY = Path("agent_output") / "3d"
SLAB_THICKNESS_M = 0.05
WALL_THICKNESS_M = 0.12
MAX_WALL_HEIGHT_M = 3.0
DOOR_HEIGHT_M = 2.1
DOOR_GAP_DEPTH_M = 1.0
THRESHOLD_DEPTH_M = 0.35
STAIR_STEPS = 12
ROUTE_RADIUS_M = 0.25
ROUTE_HEIGHT_M = 0.4
MARKER_RADIUS_M = 0.6
MARKER_HEIGHT_M = 2.5
LIFT_OPACITY = 0.35
ASSET_HEIGHT_M = {"machine": 2.0, "equipment": 1.2, "fixture": 1.0, "furniture": 0.8}

ROOM_COLORS = {
    "corridor": (0.85, 0.85, 0.82),
    "stair": (0.95, 0.60, 0.25),
    "lift": (0.60, 0.45, 0.85),
    "hall": (0.80, 0.86, 0.92),
    "outdoor": (0.65, 0.80, 0.55),
}
ROOM_TYPE_COLORS = {
    "production_zone": (0.55, 0.70, 0.90),
    "additive_zone": (0.50, 0.80, 0.85),
    "assembly_zone": (0.60, 0.75, 0.95),
    "warehouse_zone": (0.85, 0.78, 0.55),
    "logistics_zone": (0.90, 0.75, 0.50),
    "quality_lab": (0.70, 0.85, 0.65),
    "lab": (0.70, 0.85, 0.65),
    "office": (0.95, 0.92, 0.80),
    "meeting_room": (0.95, 0.85, 0.75),
    "toilet": (0.75, 0.85, 0.95),
    "bathroom": (0.75, 0.85, 0.95),
    "kitchen": (0.95, 0.80, 0.70),
    "lobby": (0.90, 0.90, 0.75),
}
DEFAULT_ROOM_COLOR = (0.92, 0.90, 0.86)
WALL_COLOR = (0.97, 0.97, 0.97)
DOOR_COLOR = (0.30, 0.65, 0.35)
STEP_DOOR_COLOR = (0.90, 0.45, 0.20)
STAIR_COLOR = (0.95, 0.60, 0.25)
LIFT_COLOR = (0.60, 0.45, 0.85)
ROUTE_COLOR = (0.90, 0.10, 0.45)
START_COLOR = (0.10, 0.70, 0.30)
END_COLOR = (0.90, 0.10, 0.20)
ASSET_COLORS = {
    "machine": (0.25, 0.45, 0.75),
    "equipment": (0.35, 0.60, 0.70),
    "fixture": (0.55, 0.55, 0.60),
    "furniture": (0.65, 0.50, 0.35),
}


@dataclass
class Part:
    """One mesh in the model: a room slab, a floor's walls, a door, a stair, a lift shaft, an asset or the route."""

    name: str
    group: str
    floor_id: str
    color: tuple[float, float, float]
    vertices: np.ndarray
    faces: np.ndarray
    attributes: dict = field(default_factory=dict)
    opacity: float = 1.0


def prism(polygon: Polygon, z_bottom: float, z_top: float) -> tuple[np.ndarray, np.ndarray]:
    """Extrude a polygon (holes allowed) between two heights into a closed triangle mesh."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for triangle in shapely.constrained_delaunay_triangles(polygon).geoms:
        corners = list(triangle.exterior.coords)[:3]
        start = len(vertices)
        vertices += [(x, y, z_top) for x, y in corners] + [(x, y, z_bottom) for x, y in corners]
        faces += [(start, start + 1, start + 2), (start + 5, start + 4, start + 3)]
    for ring in [polygon.exterior, *polygon.interiors]:
        coords = list(ring.coords)
        for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
            start = len(vertices)
            vertices += [(x0, y0, z_bottom), (x1, y1, z_bottom), (x1, y1, z_top), (x0, y0, z_top)]
            faces += [(start, start + 1, start + 2), (start, start + 2, start + 3)]
    return np.array(vertices, dtype=float).reshape(-1, 3), np.array(faces, dtype=np.int64).reshape(-1, 3)


def merge(meshes: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate several (vertices, faces) meshes into one."""
    vertices, faces, offset = [], [], 0
    for mesh_vertices, mesh_faces in meshes:
        vertices.append(mesh_vertices)
        faces.append(mesh_faces + offset)
        offset += len(mesh_vertices)
    if not vertices:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    return np.vstack(vertices), np.vstack(faces)


def polygons_of(geometry) -> list[Polygon]:
    """The non-empty polygons inside any shapely geometry."""
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry] if geometry.area > 1e-4 else []
    return [part for member in getattr(geometry, "geoms", []) for part in polygons_of(member)]


def extrude(geometry, z_bottom: float, z_top: float) -> tuple[np.ndarray, np.ndarray]:
    return merge([prism(polygon, z_bottom, z_top) for polygon in polygons_of(geometry)])


def oriented_box(center: tuple[float, float], width: float, depth: float, angle_deg: float) -> Polygon:
    footprint = box(-width / 2, -depth / 2, width / 2, depth / 2)
    return translate(rotate(footprint, angle_deg, origin=(0, 0)), *center)


def wall_angle_at(polygon: Polygon, position: tuple[float, float]) -> float:
    """Direction in degrees of the polygon edge closest to a point, so a door lines up with its wall."""
    point = Point(position)
    coords = list(polygon.exterior.coords)
    (x0, y0), (x1, y1) = min(zip(coords, coords[1:]), key=lambda edge: LineString(edge).distance(point))
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


def clean_polygon(points: list[list[float]]) -> Polygon | None:
    polygon = shapely.make_valid(Polygon(points))
    parts = polygons_of(polygon)
    if not parts:
        return None
    largest = max(parts, key=lambda part: part.area)
    return shapely.orient_polygons(largest) if largest.area >= 0.01 else None


def room_color(space: dict) -> tuple[float, float, float]:
    return ROOM_TYPE_COLORS.get(space.get("room_type"), ROOM_COLORS.get(space["type"], DEFAULT_ROOM_COLOR))


def stair_flight(polygon: Polygon, z_bottom: float, z_top: float) -> tuple[np.ndarray, np.ndarray]:
    """Steps rising along the long axis of the stair space's minimum rotated rectangle."""
    corners = list(polygon.minimum_rotated_rectangle.exterior.coords)[:4]
    edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    (ax, ay), (bx, by) = max(edges, key=lambda edge: math.dist(*edge))
    length = math.dist((ax, ay), (bx, by))
    ux, uy = (bx - ax) / length, (by - ay) / length
    span = max(polygon.bounds[2] - polygon.bounds[0], polygon.bounds[3] - polygon.bounds[1]) * 2
    meshes = []
    for step in range(STAIR_STEPS):
        t0, t1 = step / STAIR_STEPS * length, (step + 1) / STAIR_STEPS * length
        slab = Polygon([
            (ax + ux * t0 - uy * span, ay + uy * t0 + ux * span),
            (ax + ux * t1 - uy * span, ay + uy * t1 + ux * span),
            (ax + ux * t1 + uy * span, ay + uy * t1 - ux * span),
            (ax + ux * t0 + uy * span, ay + uy * t0 - ux * span),
        ])
        height = z_bottom + (step + 1) / STAIR_STEPS * (z_top - z_bottom)
        meshes.append(extrude(polygon.intersection(slab), z_bottom, height))
    return merge(meshes)


def circle(center: tuple[float, float], radius: float) -> Polygon:
    return Point(center).buffer(radius, quad_segs=8)


class Layout:
    """Floor heights shared by every part of the model."""

    def __init__(self, building: dict, explode_m: float) -> None:
        self.floors = {floor["id"]: floor for floor in building["floors"]}
        order = sorted(self.floors, key=lambda floor_id: self.floors[floor_id]["level"])
        self.index = {floor_id: position for position, floor_id in enumerate(order)}
        self.explode_m = explode_m

    def base_z(self, floor_id: str) -> float:
        return self.floors[floor_id]["elevation_m"] + self.index[floor_id] * self.explode_m

    def wall_height(self, floor_id: str) -> float:
        return min(MAX_WALL_HEIGHT_M, self.floors[floor_id].get("height_m", MAX_WALL_HEIGHT_M) - 0.2)


def build_parts(building: dict, explode_m: float = 0.0) -> list[Part]:
    layout = Layout(building, explode_m)
    parts: list[Part] = []
    polygons: dict[str, Polygon] = {}
    wall_rings: dict[str, list] = {}

    for space in building["spaces"]:
        polygon = clean_polygon(space["polygon"])
        if polygon is None:
            continue
        polygons[space["id"]] = polygon
        z = layout.base_z(space["floor_id"])
        attributes = {
            "id": space["id"],
            "name": space.get("name", ""),
            "type": space["type"],
            "room_type": space.get("room_type", ""),
            "ref": space.get("ref") or "",
            "area_m2": round(polygon.area, 2),
        }
        vertices, faces = prism(polygon, z, z + SLAB_THICKNESS_M)
        parts.append(Part(space["id"], "Spaces", space["floor_id"], room_color(space), vertices, faces, attributes))
        if space["type"] != "outdoor":
            ring = polygon.difference(polygon.buffer(-WALL_THICKNESS_M, join_style="mitre"))
            wall_rings.setdefault(space["floor_id"], []).append(ring)

    door_gaps: dict[str, list[Polygon]] = {}
    for opening in building["openings"]:
        anchor = next((polygons[s] for s in opening["space_ids"] if s in polygons), None)
        if anchor is None:
            continue
        position = tuple(opening["position"])
        angle = wall_angle_at(anchor, position)
        width = opening["width_m"]
        door_gaps.setdefault(opening["floor_id"], []).append(oriented_box(position, width, DOOR_GAP_DEPTH_M, angle))
        z = layout.base_z(opening["floor_id"]) + SLAB_THICKNESS_M
        pieces = [prism(oriented_box(position, width, THRESHOLD_DEPTH_M, angle), z, z + 0.03)]
        top = layout.base_z(opening["floor_id"]) + layout.wall_height(opening["floor_id"])
        if opening["kind"] != "opening" and top > z + DOOR_HEIGHT_M:
            lintel = oriented_box(position, width, WALL_THICKNESS_M * 2, angle)
            pieces.append(prism(lintel, z + DOOR_HEIGHT_M, top))
        vertices, faces = merge(pieces)
        attributes = {
            "id": opening["id"],
            "kind": opening["kind"],
            "width_m": width,
            "step_free": bool(opening.get("step_free", True)),
            "space_ids": ",".join(opening["space_ids"]),
        }
        color = DOOR_COLOR if opening.get("step_free", True) else STEP_DOOR_COLOR
        parts.append(Part(opening["id"], "Doors", opening["floor_id"], color, vertices, faces, attributes))

    for floor_id, rings in wall_rings.items():
        walls = shapely.union_all(rings).difference(shapely.union_all(door_gaps.get(floor_id, [])))
        z = layout.base_z(floor_id) + SLAB_THICKNESS_M
        vertices, faces = extrude(walls, z, layout.base_z(floor_id) + layout.wall_height(floor_id))
        parts.append(Part(f"{floor_id}-walls", "Walls", floor_id, WALL_COLOR, vertices, faces, {"floor_id": floor_id}))

    for connector in building["vertical_connectors"]:
        stops = sorted(
            ((floor_id, space_id) for floor_id, space_id in zip(connector["floor_ids"], connector["space_ids"])
             if space_id in polygons and floor_id in layout.floors),
            key=lambda stop: layout.floors[stop[0]]["level"],
        )
        if len(stops) < 2:
            continue
        attributes = {
            "id": connector["id"],
            "name": connector.get("name", ""),
            "kind": connector["kind"],
            "step_free": bool(connector.get("step_free", False)),
            "space_ids": ",".join(space_id for _, space_id in stops),
        }
        first_floor = stops[0][0]
        if connector["kind"] == "lift":
            shaft = polygons[stops[0][1]].buffer(-WALL_THICKNESS_M, join_style="mitre")
            z_top = layout.base_z(stops[-1][0]) + layout.wall_height(stops[-1][0])
            vertices, faces = extrude(shaft, layout.base_z(first_floor), z_top)
            parts.append(Part(connector["id"], "Connectors", first_floor, LIFT_COLOR, vertices, faces, attributes, LIFT_OPACITY))
        else:
            flights = [
                stair_flight(polygons[low_space].buffer(-WALL_THICKNESS_M, join_style="mitre"),
                             layout.base_z(low_floor) + SLAB_THICKNESS_M, layout.base_z(high_floor))
                for (low_floor, low_space), (high_floor, _) in itertools.pairwise(stops)
            ]
            vertices, faces = merge(flights)
            parts.append(Part(connector["id"], "Connectors", first_floor, STAIR_COLOR, vertices, faces, attributes))

    for asset in building["assets"]:
        footprint_info = asset.get("footprint") or {}
        width = max(footprint_info.get("width_m", 0.5), 0.05)
        depth = max(footprint_info.get("depth_m", 0.5), 0.05)
        footprint = oriented_box(tuple(asset["position"]), width, depth, footprint_info.get("rotation_deg", 0.0))
        z = layout.base_z(asset["floor_id"]) + SLAB_THICKNESS_M
        vertices, faces = prism(footprint, z, z + ASSET_HEIGHT_M.get(asset["category"], 1.0))
        attributes = {
            "id": asset["id"],
            "name": asset["name"],
            "category": asset["category"],
            "type": asset["type"],
            "space_id": asset["space_id"],
        }
        color = ASSET_COLORS.get(asset["category"], DEFAULT_ROOM_COLOR)
        parts.append(Part(asset["id"], "Assets", asset["floor_id"], color, vertices, faces, attributes))
    return parts


def route_parts(building_map: BuildingMap, route: RouteResult, explode_m: float = 0.0) -> list[Part]:
    """The route as a tube through anchors and door positions, a riser at each floor change, and two markers."""
    layout = Layout(building_map.data, explode_m)
    points: list[tuple[float, float, str]] = []
    for node in route.node_path:
        if node == OUTSIDE:
            continue
        if node.startswith(DOOR_PREFIX):
            opening = building_map.openings[node.removeprefix(DOOR_PREFIX)]
            points.append((*opening["position"], opening["floor_id"]))
        else:
            points.append((*building_map.anchor(node), building_map.spaces[node]["floor_id"]))

    z_offset = SLAB_THICKNESS_M + 0.1
    per_floor: dict[str, list] = {}
    risers = []
    for (x0, y0, floor0), (x1, y1, floor1) in itertools.pairwise(points):
        if floor0 == floor1:
            per_floor.setdefault(floor0, []).append(LineString([(x0, y0), (x1, y1)]).buffer(ROUTE_RADIUS_M, quad_segs=4))
        else:
            low, high = sorted([floor0, floor1], key=lambda floor_id: layout.base_z(floor_id))
            risers.append(prism(circle((x0, y0), ROUTE_RADIUS_M), layout.base_z(low) + z_offset,
                                layout.base_z(high) + z_offset + ROUTE_HEIGHT_M))
            if math.dist((x0, y0), (x1, y1)) > 0.01:
                per_floor.setdefault(floor1, []).append(
                    LineString([(x0, y0), (x1, y1)]).buffer(ROUTE_RADIUS_M, quad_segs=4))
    tube = [extrude(shapely.union_all(shapes), layout.base_z(floor_id) + z_offset,
                    layout.base_z(floor_id) + z_offset + ROUTE_HEIGHT_M)
            for floor_id, shapes in per_floor.items()]
    vertices, faces = merge(tube + risers)
    attributes = {
        "from": route.start_space_id,
        "to": route.destination_space_id,
        "length_m": route.length_m,
        "step_free": route.step_free,
        "space_path": ",".join(route.space_path),
    }
    start_floor, end_floor = points[0][2], points[-1][2]
    parts = [Part("route", "Route", start_floor, ROUTE_COLOR, vertices, faces, attributes)]
    for name, (x, y, floor_id), color in (("route_start", points[0], START_COLOR), ("route_end", points[-1], END_COLOR)):
        z = layout.base_z(floor_id) + SLAB_THICKNESS_M
        vertices, faces = prism(circle((x, y), MARKER_RADIUS_M), z, z + MARKER_HEIGHT_M)
        parts.append(Part(name, "Route", floor_id, color, vertices, faces))
    return parts


def usd_name(identifier: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", identifier)
    return name if name[0].isalpha() or name[0] == "_" else f"_{name}"


def write_usd(building: dict, parts: list[Part], path: Path) -> None:
    """Write a Z-up, metre-scale USD stage: /Building/<floor>/<group>/<element>, with the plan data as attributes."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/Building")
    stage.SetDefaultPrim(root.GetPrim())
    info = building["building"]
    root.GetPrim().SetCustomData({"id": info["id"], "name": info["name"], "source": info["source"], "license": info["license"]})

    for floor in building["floors"]:
        floor_prim = UsdGeom.Xform.Define(stage, f"/Building/{usd_name(floor['id'])}").GetPrim()
        floor_prim.CreateAttribute("building:level", Sdf.ValueTypeNames.Int).Set(floor["level"])
        floor_prim.CreateAttribute("building:name", Sdf.ValueTypeNames.String).Set(floor["name"])
        floor_prim.CreateAttribute("building:elevation_m", Sdf.ValueTypeNames.Double).Set(floor["elevation_m"])

    value_types = {str: Sdf.ValueTypeNames.String, bool: Sdf.ValueTypeNames.Bool, int: Sdf.ValueTypeNames.Int,
                   float: Sdf.ValueTypeNames.Double}
    for part in parts:
        if len(part.faces) == 0:
            continue
        mesh_path = f"/Building/{usd_name(part.floor_id)}/{part.group}/{usd_name(part.name)}"
        mesh = UsdGeom.Mesh.Define(stage, mesh_path)
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(part.vertices.astype(np.float32)))
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(part.faces)))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(part.faces.reshape(-1).astype(np.int32)))
        mesh.CreateDisplayColorAttr([part.color])
        if part.opacity < 1.0:
            mesh.CreateDisplayOpacityAttr([part.opacity])
        mesh.CreateDoubleSidedAttr(True)
        prim = mesh.GetPrim()
        for key, value in part.attributes.items():
            prim.CreateAttribute(f"building:{key}", value_types[type(value)]).Set(value)
    stage.GetRootLayer().Save()


def write_gltf(parts: list[Part], path: Path) -> None:
    """Write a binary glTF; glTF is Y-up, so (x, y, z) becomes (x, z, -y). Node names are the building.json ids."""
    scene = trimesh.Scene()
    materials: dict[tuple, trimesh.visual.material.PBRMaterial] = {}
    for part in parts:
        if len(part.faces) == 0:
            continue
        key = (*part.color, part.opacity)
        if key not in materials:
            materials[key] = trimesh.visual.material.PBRMaterial(
                baseColorFactor=[*part.color, part.opacity],
                metallicFactor=0.0,
                roughnessFactor=0.9,
                doubleSided=True,
                alphaMode="BLEND" if part.opacity < 1.0 else "OPAQUE",
            )
        x, y, z = part.vertices.T
        mesh = trimesh.Trimesh(np.column_stack([x, z, -y]), part.faces, process=False)
        mesh.visual = trimesh.visual.TextureVisuals(material=materials[key])
        mesh.metadata.update(part.attributes)
        scene.add_geometry(mesh, node_name=part.name, geom_name=part.name)
    scene.export(str(path), file_type="glb")


def export(
    building_directory: Path,
    output_directory: Path,
    explode_m: float = 0.0,
    route: tuple[str, str] | None = None,
    step_free: bool = False,
) -> tuple[Path, Path]:
    building_map = BuildingMap.load(building_directory)
    parts = build_parts(building_map.data, explode_m)
    if route:
        parts += route_parts(building_map, building_map.route(*route, step_free=step_free), explode_m)
    output_directory.mkdir(parents=True, exist_ok=True)
    building_id = building_map.data["building"]["id"]
    usd_path = output_directory / f"{building_id}.usda"
    gltf_path = output_directory / f"{building_id}.glb"
    write_usd(building_map.data, parts, usd_path)
    write_gltf(parts, gltf_path)
    return usd_path, gltf_path


def main() -> None:
    parser = argparse.ArgumentParser(prog="core.export3d", description="Export a building as OpenUSD and glTF.")
    parser.add_argument("building", type=Path, help="building directory (with building.json) or a building.json file")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_DIRECTORY, help="output directory")
    parser.add_argument("--explode", type=float, default=0.0, help="extra metres between floors, for a stacked view")
    parser.add_argument("--route", nargs=2, metavar=("FROM", "TO"), help="draw the shortest route between two rooms")
    parser.add_argument("--step-free", action="store_true", help="with --route: avoid stairs and steps")
    arguments = parser.parse_args()
    paths = export(arguments.building, arguments.out, arguments.explode, arguments.route, arguments.step_free)
    for path in paths:
        print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

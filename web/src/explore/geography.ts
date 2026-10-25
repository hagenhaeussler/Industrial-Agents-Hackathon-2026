import type { BuildingScene } from "@locora/view";
import type { FeatureCollection, Polygon, Position } from "geojson";

export interface LocalFrame {
  crs: "EPSG:3857";
  matrix: [number[], number[]];
  matchedSpaces: number;
  medianResidualM: number;
  p95ResidualM: number;
}

export interface CampusBuilding {
  id: string;
  name: string;
  label: string;
  address: string | null;
  city: string | null;
  postcode: string | null;
  center: [number, number];
  bounds: [number, number, number, number];
  outline: Polygon;
  levels: number[];
  floors: number;
  rooms: number;
  spaces: number;
  assets: number;
  height: number;
  osmUrl: string;
  localFrame?: LocalFrame;
  googleIndoorModel?: string;
}

export interface CampusCatalog {
  featuredBuildingId: string;
  buildings: CampusBuilding[];
}

const RADIUS = 6378137;

/** Convert source plan metres using the measured OSM alignment, never a guessed address offset. */
export function planToGeographic(frame: LocalFrame, x: number, y: number): [number, number] {
  const [a, b] = frame.matrix;
  const east = a[0]! * x + a[1]! * y + a[2]!;
  const north = b[0]! * x + b[1]! * y + b[2]!;
  return [(east / RADIUS) * (180 / Math.PI), (2 * Math.atan(Math.exp(north / RADIUS)) - Math.PI / 2) * (180 / Math.PI)];
}

export function buildingFeatures(buildings: CampusBuilding[]): FeatureCollection<Polygon> {
  return {
    type: "FeatureCollection",
    features: buildings.map((building) => ({
      type: "Feature", id: building.id, geometry: building.outline,
      properties: { id: building.id, name: building.label, height: building.height },
    })),
  };
}

/** An actual aerial crop of this footprint, rather than a fabricated building photograph. */
export function aerialPreview(building: CampusBuilding): string {
  const [west, south, east, north] = building.bounds;
  const pad = Math.max(east - west, (north - south) * 1.5) * 0.3;
  return "https://geoservices.bayern.de/od/wms/dop/v1/dop20?" + new URLSearchParams({
    SERVICE: "WMS", VERSION: "1.1.1", REQUEST: "GetMap", LAYERS: "by_dop20c", STYLES: "",
    SRS: "EPSG:4326", BBOX: [west - pad, south - pad, east + pad, north + pad].join(","),
    WIDTH: "420", HEIGHT: "200", FORMAT: "image/jpeg",
  });
}

export function levelName(level: number): string {
  return level === 0 ? "Ground" : level < 0 ? `B${Math.abs(level)}` : `Level ${level}`;
}

const roomColors: Record<string, string> = {
  corridor: "#e6e6dd", stairwell: "#e6c991", lift: "#a8c8dc", toilet: "#d9cce1",
  office: "#c8d8cf", lecture_hall: "#bdcbdc", lab: "#cededb", library: "#e2d6bf",
  generic_room: "#d9dfd0", storage: "#ddd5c7", seminar_room: "#c5d7df",
};

function closedRing(points: readonly (readonly number[])[]): Position[] {
  const result = points.map((p) => [p[0]!, p[1]!]);
  if (result.length) result.push([...result[0]!]);
  return result;
}

/** One geographic scene; floor separation is a paint expression, so moving the slider does not rebuild it. */
export function indoorFeatures(scene: BuildingScene, frame: LocalFrame): FeatureCollection<Polygon> {
  const features: FeatureCollection<Polygon>["features"] = [];
  const lowest = scene.floors[0]?.elevation ?? 0;
  scene.floors.forEach((floor, rank) => {
    const base = floor.elevation - lowest + 0.3;
    const point = ([x, y]: readonly number[]) => planToGeographic(frame, x!, y!);
    const add = (id: string, kind: string, polygon: readonly (readonly number[])[], bottom: number, height: number,
      color: string, properties: Record<string, string | number> = {}) => {
      features.push({ type: "Feature", geometry: { type: "Polygon", coordinates: [closedRing(polygon.map(point))] },
        properties: { id, kind, floorId: floor.id, level: floor.level, rank, base: base + bottom, height, color, ...properties } });
    };
    for (const space of floor.spaces) {
      add(space.id, "room", space.outline, 0, 0.15, roomColors[space.roomType] ?? "#dedfce",
        { name: space.name, ref: space.ref, roomType: space.roomType });
    }
    for (const [index, wall] of floor.walls.entries()) {
      const dx = wall.end[0] - wall.start[0], dy = wall.end[1] - wall.start[1];
      const length = Math.hypot(dx, dy);
      if (length < 0.05) continue;
      const nx = (-dy / length) * 0.06, ny = (dx / length) * 0.06;
      add(`${floor.id}-wall-${index}`, "wall", [
        [wall.start[0] + nx, wall.start[1] + ny], [wall.end[0] + nx, wall.end[1] + ny],
        [wall.end[0] - nx, wall.end[1] - ny], [wall.start[0] - nx, wall.start[1] - ny],
      ], 0.15, 1.15, "#f5f2e9");
    }
    for (const asset of floor.assets) {
      add(asset.id, "asset", asset.corners, 0.15, asset.category === "machine" ? 1.3 : 0.65,
        asset.category === "machine" ? "#748e89" : "#a8b6a3", { name: asset.name });
    }
  });
  return { type: "FeatureCollection", features };
}

/** Schematic facade bands follow the real footprint. They do not claim to reconstruct actual windows. */
export function facadeFeatures(building: CampusBuilding): FeatureCollection<Polygon> {
  const ring = building.outline.coordinates[0] ?? [];
  const latitudeScale = Math.cos((building.center[1] * Math.PI) / 180);
  const mx = (Math.PI * RADIUS * latitudeScale) / 180, my = (Math.PI * RADIUS) / 180;
  const features: FeatureCollection<Polygon>["features"] = [];
  for (let i = 1; i < ring.length; i++) {
    const a = ring[i - 1]!, b = ring[i]!;
    const dx = (b[0]! - a[0]!) * mx, dy = (b[1]! - a[1]!) * my, length = Math.hypot(dx, dy);
    if (length < 4) continue;
    const nx = (-dy / length) * 0.14 / mx, ny = (dx / length) * 0.14 / my;
    for (let floor = 0; floor < Math.round(building.height / 3); floor++) {
      for (let step = 1; step < length - 1; step += 3.2) {
        const t0 = step / length, t1 = Math.min(step + 1.8, length - 0.6) / length;
        const p = (t: number, sign: number): Position => [
          a[0]! + (b[0]! - a[0]!) * t + nx * sign,
          a[1]! + (b[1]! - a[1]!) * t + ny * sign,
        ];
        features.push({ type: "Feature", properties: { base: floor * 3 + 0.9, height: 1.4 },
          geometry: { type: "Polygon", coordinates: [[p(t0, 1), p(t1, 1), p(t1, -1), p(t0, -1), p(t0, 1)]] } });
      }
    }
  }
  return { type: "FeatureCollection", features };
}

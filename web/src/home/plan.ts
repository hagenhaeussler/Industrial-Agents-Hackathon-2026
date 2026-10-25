import type { Building, Space } from "@locora/view";

/** One space as an SVG path in the drawing's coordinates. */
export interface PlanShape {
  id: string;
  type: Space["type"];
  d: string;
}

/** Shapes and the view box that fits them. */
export interface PlanDrawing {
  shapes: PlanShape[];
  viewBox: string;
}

/** The floor a thumbnail shows: the one at level 0, else the lowest one. */
export function groundFloorId(document: Building): string | undefined {
  const floors = [...document.floors].sort((a, b) => a.level - b.level);
  return (floors.find((floor) => floor.level === 0) ?? floors[0])?.id;
}

/** The ground floor's spaces as paths. The y axis is flipped so north points up, as in building.json. */
export function groundPlan(document: Building, padding = 0.04): PlanDrawing {
  const floorId = groundFloorId(document);
  const spaces = document.spaces.filter((space) => space.floor_id === floorId && space.polygon.length >= 3);
  if (spaces.length === 0) return { shapes: [], viewBox: "0 0 1 1" };

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of spaces.flatMap((space) => space.polygon)) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, -y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, -y);
  }
  const pad = Math.max(maxX - minX, maxY - minY) * padding;
  const viewBox = [minX - pad, minY - pad, maxX - minX + 2 * pad, maxY - minY + 2 * pad]
    .map((value) => value.toFixed(2))
    .join(" ");
  const shapes = spaces.map((space) => ({
    id: space.id,
    type: space.type,
    d: `M${space.polygon.map(([x, y]) => `${x.toFixed(2)} ${(-y).toFixed(2)}`).join("L")}Z`,
  }));
  return { shapes, viewBox };
}

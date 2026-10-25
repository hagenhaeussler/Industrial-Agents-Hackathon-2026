import type { Building, Space } from "@locora/view";
import { describe, expect, it } from "vitest";
import { groundPlan } from "./plan";

function space(id: string, floor: string, type: Space["type"], polygon: [number, number][]): Space {
  return { id, floor_id: floor, type, polygon, name: id, ref: id, room_type: "", synthetic: false };
}

const square = (x: number, size: number): [number, number][] => [
  [x, 0],
  [x + size, 0],
  [x + size, size],
  [x, size],
];

// Floors are listed out of order and the basement comes first, as building.json allows.
const building = {
  building: { id: "b", name: "B", source: "test", attribution: "", license: "", split: "", units: "m" },
  floors: [
    { id: "f1", level: 1, name: "First", elevation_m: 3, height_m: 3 },
    { id: "f-1", level: -1, name: "Basement", elevation_m: -3, height_m: 3 },
    { id: "f0", level: 0, name: "Ground", elevation_m: 0, height_m: 3 },
  ],
  spaces: [
    space("basement", "f-1", "room", square(0, 20)),
    space("lobby", "f0", "hall", square(0, 10)),
    space("stair", "f0", "stair", square(10, 2)),
    space("office", "f1", "room", square(0, 4)),
  ],
  openings: [],
  vertical_connectors: [],
  assets: [],
} as unknown as Building;

describe("groundPlan", () => {
  it("draws the floor at level 0, not the lowest floor", () => {
    const plan = groundPlan(building, 0);
    expect(plan.shapes.map((shape) => shape.id)).toEqual(["lobby", "stair"]);
    expect(plan.viewBox).toBe("0.00 -10.00 12.00 10.00");
  });
});

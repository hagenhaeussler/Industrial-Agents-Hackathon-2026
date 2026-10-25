import type { RouteView } from "@building/view";
import { describe, expect, it } from "vitest";
import { directions, turnAt, type BuildingIndex } from "./directions";

// The Python route fixture: an office with a door to a lift that goes to floor 1.
const building = {
  floors: [
    { id: "F0", level: 0, name: "Ground floor", elevation_m: 0, height_m: 3 },
    { id: "F1", level: 1, name: "Floor 1", elevation_m: 3, height_m: 3 },
  ],
  spaces: [
    { id: "S-office", floor_id: "F0" },
    { id: "S-lift-0", floor_id: "F0" },
    { id: "S-lift-1", floor_id: "F1" },
  ],
  openings: [{ id: "O-door", position: [2, 0.5] }],
} as unknown as BuildingIndex;

const ref = (id: string, name: string, floor_name: string) => ({ id, name, floor_name });
const office = ref("S-office", "Office 0.01", "Ground floor");
const lift0 = ref("S-lift-0", "Lift 1", "Ground floor");
const lift1 = ref("S-lift-1", "Lift 1", "Floor 1");

const view: RouteView = {
  route: {
    reachable: true,
    length_m: 19.6,
    legs: [
      {
        start: office,
        end: lift1,
        reachable: true,
        length_m: 19.6,
        spaces: [office, lift0, lift1],
        elements: [
          { id: "O-door", kind: "door" },
          { id: "V-lift", kind: "lift", name: "Lift 1" },
        ],
        blocked_by: [],
      },
    ],
  },
  path: [
    { floor_id: "F0", x: 0.5, y: 0.5 },
    { floor_id: "F0", x: 2, y: 0.5 },
    { floor_id: "F0", x: 2.5, y: 0.5 },
    { floor_id: "F1", x: 2.5, y: 0.5 },
  ],
};

describe("directions", () => {
  it("names each space and element of the route in order", () => {
    expect(directions(view, building).map((step) => [step.instruction, step.turn, step.floorName])).toEqual([
      ["Start in Office 0.01", "start", "Ground floor"],
      ["Go through the door into Lift 1", "straight", "Ground floor"],
      ["Take Lift 1 to Floor 1", "up", "Ground floor"],
      ["Arrive at Lift 1", "arrive", "Floor 1"],
    ]);
  });

  it("places the lift step where the floor changes", () => {
    const lift = directions(view, building)[2]!;
    expect(lift.at).toEqual({ floor_id: "F0", x: 2.5, y: 0.5 });
  });

  it("gives no steps for an unreachable route", () => {
    const blocked = { ...view, route: { ...view.route, reachable: false, length_m: null }, path: [] };
    expect(directions(blocked, building)).toEqual([]);
  });
});

describe("turnAt", () => {
  const point = (x: number, y: number) => ({ floor_id: "F0", x, y });

  it("reads left and right with the plan's y axis pointing up", () => {
    expect(turnAt([point(0, 0), point(1, 0), point(1, 1)], 1)).toBe("left");
    expect(turnAt([point(0, 0), point(1, 0), point(1, -1)], 1)).toBe("right");
    expect(turnAt([point(0, 0), point(1, 0), point(2, 0.2)], 1)).toBe("straight");
  });

  it("does not turn across a floor change", () => {
    expect(turnAt([point(0, 0), point(1, 0), { floor_id: "F1", x: 1, y: 1 }], 1)).toBe("straight");
  });
});

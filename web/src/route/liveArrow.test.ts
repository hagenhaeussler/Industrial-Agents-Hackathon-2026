import type { PathPoint } from "@building/view";
import { describe, expect, it } from "vitest";
import { liveArrow, signedDeg } from "./liveArrow";

const point = (x: number, y: number, floor_id = "F0"): PathPoint => ({ x, y, floor_id });
// East for 10 m, then north for 10 m.
const path = [point(0, 0), point(10, 0), point(10, 10)];
const pose = (x: number, y: number, headingDeg: number, floorId = "F0") => ({ floorId, x, y, headingDeg });
const turn = (x: number, y: number, headingDeg: number) => {
  const arrow = liveArrow(path, pose(x, y, headingDeg));
  return arrow?.kind === "turn" ? arrow.turnDeg : arrow?.kind;
};

describe("liveArrow", () => {
  it("points along the route relative to where the camera looks", () => {
    expect(turn(2, 0, 0)).toBe(0);
    expect(turn(2, 0, 90)).toBe(-90); // looking north: turn right
    expect(turn(2, 0, 180)).toBe(180); // looking back: turn round
  });

  it("shows straight ahead while the walker keeps roughly on course", () => {
    expect(turn(2, 0, 15)).toBe(0);
    expect(turn(2, 0, -15)).toBe(0);
    expect(turn(2, 0, 30)).toBe(-30);
  });

  it("lets a walker beside the route walk parallel to it instead of back onto the line", () => {
    expect(turn(3, -1, 0)).toBe(0);
    expect(turn(3, 1.4, 0)).toBe(0);
  });

  it("leads a walker far from the route back to the edge of the band", () => {
    expect(turn(3, -3, 0)).toBeCloseTo(26.57, 2); // towards (6, -1.5)
  });

  it("leads to the line before a door or corner", () => {
    expect(turn(9, 0, 0)).toBeCloseTo(63.43, 2); // towards (10, 2)
    expect(turn(9, -1, 0)).toBeCloseTo(69.44, 2); // a third of the offset is left 1 m before the corner
  });

  it("reports arrival near the end of the route", () => {
    expect(turn(10, 9, 90)).toBe("arrive");
  });

  it("points to the stair where the route leaves the floor, and ignores other floors", () => {
    // The stair at (2, 0) is closer than the lookahead, so the arrow stops there and does not follow floor F1.
    const stairs = [point(0, 0), point(2, 0), point(2, 0, "F1"), point(2, 10, "F1")];
    const arrow = liveArrow(stairs, pose(0, 3, 0));

    expect(arrow?.kind === "turn" && arrow.turnDeg).toBeCloseTo(-45, 5); // towards (2, 1)
    expect(liveArrow(stairs, pose(0, 0, 0, "F2"))).toBeUndefined();
  });
});

describe("signedDeg", () => {
  it("keeps angles between -180 and 180", () => {
    expect([signedDeg(270), signedDeg(-270), signedDeg(180), signedDeg(-180), signedDeg(720)]).toEqual([-90, 90, 180, 180, 0]);
  });
});

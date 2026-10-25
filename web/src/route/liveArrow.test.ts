import type { PathPoint } from "@building/view";
import { describe, expect, it } from "vitest";
import { liveArrow, signedDeg } from "./liveArrow";

const point = (x: number, y: number, floor_id = "F0"): PathPoint => ({ x, y, floor_id });
// East for 10 m, then north for 10 m.
const path = [point(0, 0), point(10, 0), point(10, 10)];
const pose = (x: number, y: number, headingDeg: number, floorId = "F0") => ({ floorId, x, y, headingDeg });

describe("liveArrow", () => {
  it("points along the route relative to where the camera looks", () => {
    expect(liveArrow(path, pose(2, 0, 0))).toEqual({ kind: "turn", turnDeg: 0 });
    expect(liveArrow(path, pose(2, 0, 90))).toEqual({ kind: "turn", turnDeg: -90 }); // looking north: turn right
    expect(liveArrow(path, pose(2, 0, 180))).toEqual({ kind: "turn", turnDeg: 180 }); // looking back: turn round
  });

  it("shows the coming turn before the corner", () => {
    const arrow = liveArrow(path, pose(9, 0, 0));

    expect(arrow?.kind).toBe("turn");
    expect(arrow?.kind === "turn" && arrow.turnDeg).toBeCloseTo(63.4, 1); // towards (10, 2)
  });

  it("leads a walker beside the route back onto it", () => {
    const arrow = liveArrow(path, pose(3, -3, 0));

    expect(arrow?.kind === "turn" && arrow.turnDeg).toBeCloseTo(45, 5); // towards (6, 0)
  });

  it("reports arrival near the end of the route", () => {
    expect(liveArrow(path, pose(10, 9, 90))).toEqual({ kind: "arrive" });
  });

  it("points to the stair where the route leaves the floor, and ignores other floors", () => {
    // The stair at (2, 0) is closer than the lookahead, so the arrow stops there and does not follow floor F1.
    const stairs = [point(0, 0), point(2, 0), point(2, 0, "F1"), point(2, 10, "F1")];
    const arrow = liveArrow(stairs, pose(0, 1, 0));

    expect(arrow?.kind === "turn" && arrow.turnDeg).toBeCloseTo(-26.57, 2);
    expect(liveArrow(stairs, pose(0, 0, 0, "F2"))).toBeUndefined();
  });
});

describe("signedDeg", () => {
  it("keeps angles between -180 and 180", () => {
    expect([signedDeg(270), signedDeg(-270), signedDeg(180), signedDeg(-180), signedDeg(720)]).toEqual([-90, 90, 180, 180, 0]);
  });
});

import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { Building } from "../building";
import { fixture } from "../testing/fixture";
import { compileScene, SceneError } from "./compile";

const DEV = new URL("../../../../data/dev/", import.meta.url);

function devBuildings(): Building[] {
  return readdirSync(DEV).map((id) => JSON.parse(readFileSync(new URL(`${id}/building.json`, DEV), "utf8")));
}

describe("compileScene", () => {
  it("orders floors by level and keeps each entity on its own floor", () => {
    const scene = compileScene(fixture());
    expect(scene.floors.map((floor) => floor.id)).toEqual(["F0", "F1"]);
    expect(scene.floors[0]!.spaces.map((space) => space.id)).toEqual(["A", "B"]);
    expect(scene.floors[1]!.spaces.map((space) => space.id)).toEqual(["C"]);
    expect(scene.floors[0]!.assets.map((asset) => asset.id)).toEqual(["D1"]);
  });

  it("cuts a gap of each opening's width into the nearest wall", () => {
    const walls = compileScene(fixture()).floors[0]!.walls.filter((wall) => wall.spaceId === "A");
    expect(walls.map((wall) => [wall.start, wall.end])).toEqual([
      [[0, 0], [1.4, 0]], // entrance at x = 2, 1.2 m wide
      [[2.6, 0], [4, 0]],
      [[4, 0], [4, 1]], // door at y = 1.5, 1 m wide
      [[4, 2], [4, 3]],
      [[4, 3], [0, 3]],
      [[0, 3], [0, 0]],
    ]);
  });

  it("gives each opening the direction of the wall it cuts", () => {
    const openings = compileScene(fixture()).floors[0]!.openings;
    expect(openings.map((opening) => [opening.id, opening.direction])).toEqual([
      ["O1", [0, 1]],
      ["O2", [1, 0]],
    ]);
  });

  it("turns asset footprints counterclockwise", () => {
    const desk = compileScene(fixture()).floors[0]!.assets[0]!;
    // 2 m wide along x, turned by 90°, so it now spans 2 m along y.
    expect(desk.corners).toEqual([[1.5, 0.5], [1.5, 2.5], [0.5, 2.5], [0.5, 0.5]]);
  });

  it("places labels inside irregular rooms", () => {
    const lift = compileScene(fixture()).floors[1]!.spaces[0]!;
    const [x, y] = lift.labelPoint;
    const insideLeg = x >= 4 && x <= 5 && y >= 0 && y <= 3;
    const insideBase = x >= 4 && x <= 8 && y >= 0 && y <= 1;
    expect(insideLeg || insideBase).toBe(true);
  });

  it("joins connector stops at their spaces' label points", () => {
    const scene = compileScene(fixture());
    expect(scene.connectors[0]!.stops).toEqual([
      { floorId: "F0", spaceId: "B", point: scene.floors[0]!.spaces[1]!.labelPoint },
      { floorId: "F1", spaceId: "C", point: scene.floors[1]!.spaces[0]!.labelPoint },
    ]);
  });

  it("lists every broken reference", () => {
    const building = fixture();
    building.assets[0]!.space_id = "missing";
    building.openings[1]!.space_ids = ["A", "C"];
    let error: unknown;
    try {
      compileScene(building);
    } catch (caught) {
      error = caught;
    }
    expect(error).toBeInstanceOf(SceneError);
    expect((error as SceneError).problems).toEqual([
      "opening O1 refers to space C on another floor",
      "asset D1 refers to unknown space missing",
    ]);
  });

  it("gives the same scene for every order of the source lists", () => {
    for (const building of devBuildings().slice(0, 6)) {
      const reversed: Building = {
        ...building,
        floors: [...building.floors].reverse(),
        spaces: [...building.spaces].reverse(),
        openings: [...building.openings].reverse(),
        vertical_connectors: [...building.vertical_connectors].reverse(),
        assets: [...building.assets].reverse(),
      };
      expect(compileScene(reversed)).toEqual(compileScene(building));
    }
  });

  it("draws every dev building without losing entities", () => {
    for (const building of devBuildings()) {
      const scene = compileScene(building);
      const count = (key: "spaces" | "openings" | "assets") =>
        scene.floors.reduce((total, floor) => total + floor[key].length, 0);
      expect([count("spaces"), count("openings"), count("assets")]).toEqual([
        building.spaces.length,
        building.openings.length,
        building.assets.length,
      ]);
      expect(scene.floors.every((floor) => floor.walls.length > 0)).toBe(true);
    }
  });
});

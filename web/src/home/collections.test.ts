import type { BuildingSummary } from "@locora/view";
import { describe, expect, it } from "vitest";
import { floorLabel, groupBuildings } from "./collections";

const building = (id: string, source: string): BuildingSummary => ({ id, name: id, source, floors: 1 });

describe("groupBuildings", () => {
  it("keeps buildings from unknown sources in Other and drops empty collections", () => {
    const groups = groupBuildings([building("a", "resplan"), building("b", "new_source"), building("c", "scan")]);
    expect(groups.map((group) => [group.id, group.buildings.map((item) => item.id)])).toEqual([
      ["places", ["c"]],
      ["homes", ["a"]],
      ["other", ["b"]],
    ]);
  });
});

describe("floorLabel", () => {
  it("shows a single count or a range", () => {
    expect(floorLabel([1])).toBe("1 floor");
    expect(floorLabel([3, 1, 7])).toBe("1–7 floors");
  });
});

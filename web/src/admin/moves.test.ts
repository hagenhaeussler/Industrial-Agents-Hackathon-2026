import type { Building } from "@building/view";
import { describe, expect, it } from "vitest";
import { applyMoves } from "./moves";

const asset = (id: string) => ({ id, floor_id: "F0", space_id: "S1", position: [1, 1] as [number, number] });
const building = { assets: [asset("A"), asset("B")] } as unknown as Building;

describe("applyMoves", () => {
  it("places moved equipment at its latest place and leaves the rest", () => {
    const moved = applyMoves(building, [
      { assetId: "A", floorId: "F1", spaceId: "S9", x: 4, y: 5 },
      { assetId: "A", floorId: "F1", spaceId: "S9", x: 6, y: 7 },
    ]);
    expect(moved.assets[0]).toMatchObject({ floor_id: "F1", space_id: "S9", position: [6, 7] });
    expect(moved.assets[1]).toBe(building.assets[1]);
    expect(building.assets[0]!.position).toEqual([1, 1]);
  });
});

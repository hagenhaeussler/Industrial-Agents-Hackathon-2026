import { describe, expect, it } from "vitest";

import { floorOffsets } from "./layout";

describe("floorOffsets", () => {
  const floors = [
    { id: "B1", elevation: -3 },
    { id: "G", elevation: 0 },
    { id: "F1", elevation: 4.5 },
  ];

  it("keeps real elevations without a gap", () => {
    expect([...floorOffsets(floors, 0)]).toEqual([["B1", -3], ["G", 0], ["F1", 4.5]]);
  });

  it("adds the gap once per floor below", () => {
    expect([...floorOffsets(floors, 5)]).toEqual([["B1", -3], ["G", 5], ["F1", 14.5]]);
  });
});

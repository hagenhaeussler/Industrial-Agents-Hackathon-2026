import { describe, expect, it } from "vitest";

import { placeLabels } from "./labelPlacement";

const viewport = { width: 400, height: 300 };
const label = (key: string, x: number, y: number, priority: number) => ({ key, x, y, width: 80, height: 14, priority });

describe("placeLabels", () => {
  it("keeps the higher-priority label where two overlap", () => {
    expect(placeLabels([label("small", 100, 100, 1), label("large", 120, 105, 5)], viewport)).toEqual(new Set(["large"]));
  });

  it("keeps labels that do not overlap", () => {
    expect(placeLabels([label("a", 100, 100, 1), label("b", 300, 100, 1)], viewport)).toEqual(new Set(["a", "b"]));
  });

  it("hides labels that leave the viewport and breaks ties by key", () => {
    const shown = placeLabels([label("edge", 10, 100, 9), label("b", 200, 50, 1), label("a", 210, 52, 1)], viewport);
    expect(shown).toEqual(new Set(["a"]));
  });
});

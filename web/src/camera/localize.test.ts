import { afterEach, describe, expect, it, vi } from "vitest";
import { frameSize, postFrame, toFix, type LocalizeResult } from "./localize";

const result: LocalizeResult = {
  building_id: "b1",
  located: true,
  reliable: true,
  floor_id: "F0",
  space_id: "S1",
  position: [2, 3],
  height_m: 1.4,
  heading_deg: 45,
  num_inliers: 80,
};

describe("toFix", () => {
  it("uses reliable results only", () => {
    expect(toFix(result)).toEqual({ floorId: "F0", spaceId: "S1", x: 2, y: 3, headingDeg: 45 });
    expect(toFix({ ...result, reliable: false })).toBeUndefined();
    expect(toFix({ ...result, located: false, space_id: null })).toBeUndefined();
  });
});

describe("frameSize", () => {
  it("limits the long side to 1024 px and keeps small frames", () => {
    expect(frameSize(1920, 1080)).toEqual({ width: 1024, height: 576 });
    expect(frameSize(1080, 1920)).toEqual({ width: 576, height: 1024 });
    expect(frameSize(640, 480)).toEqual({ width: 640, height: 480 });
  });
});

describe("postFrame", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("tells the caller to stop when the building has no map or the server has no localization", async () => {
    for (const status of [404, 503]) {
      vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status })));
      expect(await postFrame("b1", new Blob(["x"]))).toEqual({ kind: "unavailable" });
    }
  });

  it("keeps trying after other failures, such as a timeout", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 502 })));
    expect(await postFrame("b1", new Blob(["x"]))).toEqual({ kind: "failed" });
  });
});

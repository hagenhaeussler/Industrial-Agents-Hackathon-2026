import { afterEach, describe, expect, it,vi } from "vitest";
import { currentGoogle3d,loadGoogle3d,exteriorCamera, isBuildingClick } from "./google3d";
import type { CampusBuilding } from "./geography";

const building = {
  center: [11, 48], bounds: [10.999, 47.999, 11.001, 48.001],
  outline: { type: "Polygon", coordinates: [
    [[10,47],[12,47],[12,49],[10,49],[10,47]],
    [[10.5,47.5],[10.8,47.5],[10.8,47.8],[10.5,47.8],[10.5,47.5]],
  ] },
} as CampusBuilding;

describe("photographic exterior handoff", () => {
  afterEach(()=>vi.unstubAllGlobals());
  it("reuses an already loaded public SDK after hot reload without reading a key or adding a script",async()=>{
    const sdk={Map3DElement:class extends HTMLElement {}};
    vi.stubGlobal("google",{maps:{maps3d:sdk}});
    const scripts=document.scripts.length;
    expect(currentGoogle3d()).toBe(sdk);
    expect(await loadGoogle3d("unused")).toBe(sdk);
    expect(document.scripts.length).toBe(scripts);
  });
  it("opens only clicks on the real building, excluding courtyards and neighbours", () => {
    expect(isBuildingClick(building, { lat: 48, lng: 11 })).toBe(true);
    expect(isBuildingClick(building, { lat: 48, lng: 13 })).toBe(false);
    expect(isBuildingClick(building, { lat: 47.6, lng: 10.6 })).toBe(false);
    expect(isBuildingClick(building)).toBe(false);
    expect(isBuildingClick(building, { lat: NaN, lng: 11 })).toBe(false);
  });
  it("uses terrain-relative altitude and fits the same building on a narrow viewport", () => {
    const desktop = exteriorCamera(building, 1.5), mobile = exteriorCamera(building, 0.7);
    expect(desktop.center).toEqual({ lat: 48, lng: 11, altitude: 0 });
    expect(desktop.altitudeMode).toBe("RELATIVE_TO_GROUND");
    expect(mobile.range).toBeGreaterThan(desktop.range);
    expect(desktop.range).toBeGreaterThan(220);
  });
});

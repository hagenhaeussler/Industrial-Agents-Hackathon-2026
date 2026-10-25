import { describe, expect, it } from "vitest";
import { compileScene } from "@building/view";
import { fixture } from "../../../packages/building-view/src/testing/fixture";
import { aerialPreview, indoorFeatures, planToGeographic, type CampusBuilding, type LocalFrame } from "./geography";

const frame: LocalFrame = { crs: "EPSG:3857", matrix: [[1, 0, 0], [0, 1, 0]], matchedSpaces: 10, medianResidualM: 0, p95ResidualM: 0 };

describe("geographic building placement", () => {
  it("preserves east, north and affine rotation instead of treating metres as longitude and latitude", () => {
    expect(planToGeographic(frame, 0, 0)).toEqual([0, 0]);
    expect(planToGeographic(frame, 111319.49079327357, 0)[0]).toBeCloseTo(1, 8);
    expect(planToGeographic(frame, 0, 111325.1428663851)[1]).toBeCloseTo(1, 8);
    const rotated = { ...frame, matrix: [[0, -1, 0], [1, 0, 0]] as [number[], number[]] };
    expect(planToGeographic(rotated, 100, 0)[0]).toBeCloseTo(0);
    expect(planToGeographic(rotated, 100, 0)[1]).toBeGreaterThan(0);
  });

  it("keeps rooms, cut wall openings and rotated equipment together on their source floor", () => {
    const document = fixture();
    const before = JSON.stringify(document);
    const result = indoorFeatures(compileScene(document), frame);
    const office = result.features.find((f) => f.properties?.id === "A")!;
    const desk = result.features.find((f) => f.properties?.id === "D1")!;
    expect(office.properties).toMatchObject({ kind: "room", floorId: "F0", rank: 0 });
    expect(desk.properties).toMatchObject({ kind: "asset", floorId: "F0", rank: 0 });
    // The rotated 2x1 desk is taller north/south than east/west.
    const ring = desk.geometry.coordinates[0]!;
    const xs = ring.map((p) => p[0]!), ys = ring.map((p) => p[1]!);
    expect(Math.max(...ys) - Math.min(...ys)).toBeCloseTo(2 * (Math.max(...xs) - Math.min(...xs)), 8);
    const upper = result.features.find((f) => f.properties?.id === "C")!;
    expect(upper.properties?.base - office.properties?.base).toBe(3);
    for (const feature of result.features) {
      const points = feature.geometry.coordinates[0]!;
      expect(points[0]).toEqual(points.at(-1));
      expect(points.flat().every(Number.isFinite)).toBe(true);
    }
    expect(JSON.stringify(document)).toBe(before);
  });

  it("requests an actual coordinate-bounded aerial image with the correct axis order", () => {
    const building = { bounds: [11.66, 48.26, 11.67, 48.27] } as CampusBuilding;
    const url = new URL(aerialPreview(building));
    expect(url.searchParams.get("SRS")).toBe("EPSG:4326");
    const [west, south, east, north] = url.searchParams.get("BBOX")!.split(",").map(Number);
    expect(west).toBeLessThan(11.66); expect(east).toBeGreaterThan(11.67);
    expect(south).toBeLessThan(48.26); expect(north).toBeGreaterThan(48.27);
  });
});

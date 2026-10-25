import { describe, expect, it } from "vitest";
import type { Polygon } from "geojson";
import type { StyleSpecification } from "maplibre-gl";
import { adaptEarthStyle, buildingBearing, earthOverviewZoom, EARTH_LAYER_ID, EARTH_SOURCE_ID } from "./earth-scene";

describe("photographic Earth style", () => {
  it("fits the whole globe above a phone sheet and keeps the desktop overview bounded", () => {
    const phone = earthOverviewZoom(390, 786, true), desktop = earthOverviewZoom(960, 785, false);
    expect(phone).toBeLessThan(desktop);
    expect(512 * 2 ** phone / Math.PI).toBeLessThanOrEqual(390 * .82);
    expect(desktop).toBeLessThanOrEqual(1.65);
    expect(Number.isFinite(earthOverviewZoom(0, 0, true))).toBe(true);
  });
  const base = (): StyleSpecification => ({ version: 8, sources: {
    vectors: { type: "vector", tiles: ["https://example.com/{z}/{x}/{y}.pbf"] },
    aerial: { type: "raster", tiles: ["https://example.com/aerial/{z}/{x}/{y}"] },
  }, layers: [
    { id: "background", type: "background", paint: { "background-color": "#fafafa", "background-opacity": 0.8 } },
    { id: "land", type: "fill", source: "vectors", "source-layer": "land", paint: { "fill-color": "#abcdef" } },
    { id: "water", type: "fill", source: "vectors", "source-layer": "water", paint: { "fill-opacity": 1 } },
    { id: "aerial", type: "raster", source: "aerial", minzoom: 12, layout: { visibility: "none" } },
    { id: "labels", type: "symbol", source: "vectors", "source-layer": "place", layout: { "text-field": ["get", "name"] } },
  ] });

  it("covers opaque vector geography and labels with a fading credited satellite overlay", () => {
    const result = adaptEarthStyle(base());
    expect(result.layers.at(-1)).toMatchObject({ id: EARTH_LAYER_ID, type: "raster", maxzoom: 12,
      paint: { "raster-opacity": ["interpolate", ["linear"], ["zoom"], 9.5, 1, 12, 0] } });
    expect(result.sources[EARTH_SOURCE_ID]).toMatchObject({ type: "raster", maxzoom: 13 });
    expect(JSON.stringify(result.sources[EARTH_SOURCE_ID])).toContain("creativecommons.org/licenses/by/4.0/");
    expect(result.projection).toEqual({ type: "globe" });
  });

  it("preserves city-scale paints, aerial state and caller data while exposing space outside the globe", () => {
    const original = base(), snapshot = structuredClone(original), result = adaptEarthStyle(original);
    expect(original).toEqual(snapshot);
    expect(result.layers[0]).toEqual({ ...snapshot.layers[0], minzoom: 9 });
    for (const layer of snapshot.layers) {
      const actual = result.layers.find(candidate => candidate.id === layer.id)!;
      expect(actual.paint).toEqual(layer.paint);
      expect(actual.layout).toEqual(layer.layout);
    }
    expect(result.layers.find(layer => layer.id === "aerial")?.minzoom).toBe(12);
    expect(result.sources.aerial).toEqual(snapshot.sources.aerial);
  });

  it("suppresses vector symbols and geometry around the low-zoom planet edge", () => {
    const result = adaptEarthStyle(base());
    for (const id of ["land", "water", "labels"]) {
      expect(result.layers.find(layer => layer.id === id)?.minzoom).toBe(9);
    }
  });

  it("is safe to apply again without accumulating overlays", () => {
    const result = adaptEarthStyle(adaptEarthStyle(base()));
    expect(result.layers.filter(layer => layer.id === EARTH_LAYER_ID)).toHaveLength(1);
  });
});

function rectangle(angle = 0, origin: [number, number] = [11.67, 48.26], holes = false): Polygon {
  const radians = angle * Math.PI / 180, k = Math.cos(origin[1] * Math.PI / 180);
  const ring = (width: number, height: number) => {
    const corners = [[-width/2, -height/2], [width/2, -height/2], [width/2, height/2], [-width/2, height/2]];
    const result = corners.map(([x, y]) => {
      const east = x! * Math.cos(radians) - y! * Math.sin(radians), north = x! * Math.sin(radians) + y! * Math.cos(radians);
      return [origin[0] + east / (111319.49079327358 * k), origin[1] + north / 111319.49079327358];
    });
    return [...result, result[0]!];
  };
  return { type: "Polygon", coordinates: holes ? [ring(200, 50), ring(80, 20)] : [ring(200, 50)] };
}

describe("building-derived view", () => {
  it("looks across a corner and follows a rotated footprint", () => {
    expect(buildingBearing(rectangle())).toBeCloseTo(55, 2);
    expect(buildingBearing(rectangle(30))).toBeCloseTo(25, 2);
    expect(buildingBearing(rectangle(90))).toBeCloseTo(-35, 2);
  });

  it("uses metres rather than raw longitude and does not depend on location or ring direction", () => {
    const shape = rectangle(30, [18, 60]);
    expect(buildingBearing(shape)).toBeCloseTo(buildingBearing(rectangle(30)), 2);
    expect(buildingBearing({ ...shape, coordinates: shape.coordinates.map(ring => [...ring].reverse()) })).toBeCloseTo(25, 2);
  });

  it("subtracts courtyard mass and leaves source rings intact", () => {
    const shape = rectangle(30, [11.67, 48.26], true), snapshot = structuredClone(shape);
    expect(buildingBearing(shape)).toBeCloseTo(25, 2);
    expect(shape).toEqual(snapshot);
  });

  it("returns a finite stable view for absent, degenerate or invalid outlines", () => {
    for (const coordinates of [[], [[[0, 0], [0, 0], [0, 0], [0, 0]]], [[[NaN, 0], [1, 0], [1, 1], [NaN, 0]]]]) {
      expect(buildingBearing({ type: "Polygon", coordinates })).toBe(-35);
    }
  });
});

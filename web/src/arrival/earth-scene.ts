import type { Polygon } from "geojson";
import type { StyleSpecification } from "maplibre-gl";

export const EARTH_SOURCE_ID = "earth-sentinel";
export const EARTH_LAYER_ID = "earth-sentinel";

/** MapLibre's globe diameter is approximately worldSize / π; fit the planet above the phone sheet. */
export function earthOverviewZoom(width: number, height: number, compact: boolean): number {
  const diameter = Math.max(180, Math.min(width * .82, Math.max(200, height - (compact ? 360 : 100)) * .85));
  return Math.max(.35, Math.min(1.65, Math.log2(diameter * Math.PI / 512)));
}

/** Add the photographic arrival surface without replacing the app's existing campus basemap. */
export function adaptEarthStyle(input: StyleSpecification): StyleSpecification {
  const style = structuredClone(input);
  style.projection = { type: "globe" };
  style.sky = {
    ...style.sky,
    "sky-color": "#a9cbe6",
    "horizon-color": "#eef3f2",
    "fog-color": "#f3f2ec",
    "sky-horizon-blend": 0.6,
    "horizon-fog-blend": 0.7,
    "fog-ground-blend": 0.85,
    "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 8, 0],
  };
  style.sources[EARTH_SOURCE_ID] = {
    type: "raster",
    tiles: ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"],
    tileSize: 256,
    maxzoom: 13,
    attribution: '<a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless</a> by EOX IT Services GmbH ' +
      '(contains modified Copernicus Sentinel data 2016), <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>',
  };
  style.layers = style.layers.filter(layer => layer.id !== EARTH_LAYER_ID);
  for (const layer of style.layers) {
    // MapLibre paints a background outside the planet as well. Let the app's space background
    // show there; once close to the ground this layer keeps its original paint unchanged.
    // Symbol layers may render beyond the globe's raster edge; suppress all low-zoom
    // basemap geometry/labels rather than relying on the opaque raster to cover them.
    layer.minzoom = Math.max(layer.minzoom ?? 0, 9);
  }
  // Above all basemap geometry and labels, so opaque land/water layers cannot hide the Earth.
  // At city scale the overlay disappears, revealing the existing style without repainting it.
  // Campus pins, buildings and indoor layers are appended by the controller above this overlay.
  style.layers.push({
    id: EARTH_LAYER_ID,
    source: EARTH_SOURCE_ID,
    type: "raster",
    maxzoom: 12,
    paint: {
      "raster-opacity": ["interpolate", ["linear"], ["zoom"], 9.5, 1, 12, 0],
      "raster-fade-duration": 200,
    },
  });
  return style;
}

const EARTH_RADIUS_M = 6378137;
const FALLBACK_BEARING = -35;

/** A stable corner view from the footprint's area principal axis; courtyard voids subtract mass. */
export function buildingBearing(outline: Polygon): number {
  const first = outline.coordinates[0]?.[0];
  if (!first || !Number.isFinite(first[0]) || !Number.isFinite(first[1]) || Math.abs(first[1]!) >= 89.9) return FALLBACK_BEARING;
  const rad = Math.PI / 180, k = Math.cos(first[1]! * rad);
  let area = 0, sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
  for (const [index, ring] of outline.coordinates.entries()) {
    if (ring.length < 4 || ring.some(point => !Number.isFinite(point[0]) || !Number.isFinite(point[1]))) return FALLBACK_BEARING;
    const points = ring.map(point => [(point[0]! - first[0]!) * rad * EARTH_RADIUS_M * k,
      (point[1]! - first[1]!) * rad * EARTH_RADIUS_M]);
    let a = 0, x = 0, y = 0, xx = 0, yy = 0, xy = 0;
    for (let i = 0; i < points.length; i++) {
      const [x1, y1] = points[i]!, [x2, y2] = points[(i + 1) % points.length]!;
      const cross = x1! * y2! - x2! * y1!;
      a += cross;
      x += (x1! + x2!) * cross;
      y += (y1! + y2!) * cross;
      xx += (x1! * x1! + x1! * x2! + x2! * x2!) * cross;
      yy += (y1! * y1! + y1! * y2! + y2! * y2!) * cross;
      xy += (2 * x1! * y1! + x1! * y2! + x2! * y1! + 2 * x2! * y2!) * cross;
    }
    if (Math.abs(a) < 1e-8) return FALLBACK_BEARING;
    const sign = Math.sign(a) * (index === 0 ? 1 : -1);
    area += sign * a / 2;
    sx += sign * x / 6; sy += sign * y / 6;
    sxx += sign * xx / 12; syy += sign * yy / 12; sxy += sign * xy / 24;
  }
  if (area <= 1e-6) return FALLBACK_BEARING;
  const vx = sxx / area - (sx / area) ** 2, vy = syy / area - (sy / area) ** 2;
  const cov = sxy / area - sx * sy / (area * area);
  if (Math.hypot(vx - vy, 2 * cov) <= Math.max(vx + vy, 1) * 1e-8) return FALLBACK_BEARING;
  const angleFromEast = Math.atan2(2 * cov, vx - vy) / 2 / rad;
  const axisBearing = ((90 - angleFromEast) % 180 + 180) % 180;
  return ((axisBearing - 35 + 540) % 360) - 180;
}

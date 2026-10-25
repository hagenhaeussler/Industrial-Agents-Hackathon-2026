import { Map, setWorkerUrl, type StyleSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { ArrivalBuilding } from "./catalogue";
import { adaptEarthStyle, buildingBearing, earthOverviewZoom } from "./earth-scene";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(workerUrl);

/** Earth, approach and tilt over roughly five seconds, including the final fade. */
export function startArrival(container: HTMLElement, building: ArrivalBuilding, done: () => void, signal: AbortSignal) {
  const map = new Map({
    container, interactive: false,
    style: adaptEarthStyle({ version: 8, sources: {}, layers: [] }),
    center: [building.center[0] - 25, 30],
    zoom: earthOverviewZoom(container.clientWidth, container.clientHeight, false),
    pitch: 0, maxPitch: 75, attributionControl: { compact: true },
    canvasContextAttributes: { antialias: true },
  });
  let hold: number | undefined;
  const resize = new ResizeObserver(() => map.resize());
  resize.observe(container);
  const cleanup = () => { window.clearTimeout(hold); resize.disconnect(); map.remove(); };
  signal.addEventListener("abort", cleanup, { once: true });
  map.on("error", done);

  // Use the branch's real vector campus at close range; the photographic Earth fades above it.
  void fetch("https://tiles.openfreemap.org/styles/bright", { signal }).then(async (response) => {
    if (!response.ok) throw new Error("Map unavailable");
    const style = await response.json() as StyleSpecification;
    if (signal.aborted) return;
    // No POI/road labels during this short entrance; keep the focus on the building footprint.
    style.layers = style.layers.filter((layer) => layer.type !== "symbol");
    map.once("style.load", () => {
      if (signal.aborted) return;
      const firstLabel = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
      if (map.getSource("openmaptiles")) {
        map.addLayer({ id: "arrival-context", type: "fill-extrusion", source: "openmaptiles", "source-layer": "building", minzoom: 14,
          filter: [">", ["distance", building.outline], .15],
          paint: { "fill-extrusion-color": "#e4e1d4", "fill-extrusion-height": ["coalesce", ["get", "render_height"], 8],
            "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0] } }, firstLabel);
      }
      map.addSource("arrival-building", { type: "geojson", data: { type: "Feature", geometry: building.outline, properties: {} } });
      map.addLayer({ id: "arrival-building", type: "fill-extrusion", source: "arrival-building", minzoom: 13,
        paint: { "fill-extrusion-color": "#afc0b8", "fill-extrusion-height": building.height } }, firstLabel);
      map.addLayer({ id: "arrival-outline", type: "line", source: "arrival-building", minzoom: 13,
        paint: { "line-color": "#dcff58", "line-width": 3 } });
      const target = map.cameraForBounds([[building.bounds[0], building.bounds[1]], [building.bounds[2], building.bounds[3]]],
        { padding: Math.min(container.clientWidth, container.clientHeight) * .2, maxZoom: 18.4 });
      const zoom = target?.zoom ?? 16;
      // A globe beat, a slower descent, then the footprint-derived corner view.
      hold = window.setTimeout(() => {
        if (signal.aborted) return;
        map.once("moveend", () => {
          if (signal.aborted) return;
          map.once("moveend", done);
          map.easeTo({ center: building.center, zoom, pitch: 56, bearing: buildingBearing(building.outline), duration: 1000 });
        });
        map.flyTo({ center: building.center, zoom: zoom - .7, pitch: 0, bearing: 0, duration: 3000, curve: 1.25 });
      }, 400);
    });
    map.setStyle(adaptEarthStyle(style));
  }).catch(() => { if (!signal.aborted) done(); });
}

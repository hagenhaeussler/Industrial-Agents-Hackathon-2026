import { Map, NavigationControl, ScaleControl, setWorkerUrl, type GeoJSONSource, type StyleSpecification, type ExpressionSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { BuildingScene } from "@locora/view";
import type { FeatureCollection, Point, Polygon } from "geojson";
import { buildingFeatures, facadeFeatures, indoorFeatures, type CampusBuilding, type CampusCatalog } from "./geography";
import type { ExteriorPose } from "./google3d";

export type JourneyStage = "globe" | "flying" | "arriving" | "campus" | "inside";
export interface RoomPick { id: string; name: string; ref: string; floorId: string; level: number; }
const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };
const STYLE_URL = "https://tiles.openfreemap.org/styles/bright";

// MapLibre 6 ships a separate worker; let Vite bundle and locate it in dev and production.
setWorkerUrl(workerUrl);

export class CampusMap {
  readonly map: Map;
  private flight?: AbortController;
  private selected?: CampusBuilding;
  private indoor?: { scene: BuildingScene; building: CampusBuilding };
  private ready = false;
  private alive = true;
  private aerial = false;
  private stage: JourneyStage = "globe";
  private movement = 0;
  private resizeObserver: ResizeObserver;

  constructor(container: HTMLElement, private catalog: CampusCatalog, private callbacks: {
    onStage: (stage: JourneyStage) => void;
    onSelect: (id: string) => void;
    onRoom: (room: RoomPick | undefined) => void;
    onError: (message: string) => void;
    onReady: () => void;
  }) {
    this.map = new Map({ container, style: { version: 8, sources: {}, layers: [
      { id: "background", type: "background", paint: { "background-color": "#e6edf0" } },
    ] }, center: [12, 30], zoom: 1.65, pitch: 0, attributionControl: { compact: true },
      maxPitch: 75, maxZoom: 22, canvasContextAttributes: { antialias: true } });
    this.resizeObserver = new ResizeObserver(() => {
      this.map.resize();
      const mobile = window.matchMedia("(max-width: 760px)").matches;
      this.map.setPadding({ top: 35, bottom: mobile ? 265 : 35, left: 0, right: 0 });
      if (this.selected && !this.flight && (this.stage === "campus" || this.stage === "inside")) {
        this.map.jumpTo({ center: this.selected.center, zoom: this.targetZoom(this.selected) });
      }
    });
    this.resizeObserver.observe(container);
    this.map.addControl(new NavigationControl({ visualizePitch: true }), "bottom-right");
    this.map.addControl(new ScaleControl({ maxWidth: 120 }), "bottom-left");
    this.map.on("dragstart", () => {
      if (!this.flight) return;
      this.flight.abort(); this.flight = undefined;
      this.changeStage(this.map.getZoom() < 8 ? "globe" : "campus");
    });
    this.map.on("click", (event) => {
      if (!this.ready) return;
      const rooms = this.map.queryRenderedFeatures(event.point, { layers: ["indoor-rooms"] });
      if (this.indoor && rooms[0]?.properties) {
        const p = rooms[0].properties;
        this.callbacks.onRoom({ id: p.id, name: p.name, ref: p.ref, floorId: p.floorId, level: p.level });
        return;
      }
      const features = this.map.queryRenderedFeatures(event.point, { layers: ["known-buildings", "building-pins", "building-names"] });
      if (features[0]?.properties?.id) this.callbacks.onSelect(features[0].properties.id);
      else this.callbacks.onRoom(undefined);
    });
    this.map.on("mousemove", (event) => {
      if (!this.ready) return;
      this.map.getCanvas().style.cursor = this.map.queryRenderedFeatures(event.point, {
        layers: ["known-buildings", "building-pins", "indoor-rooms"],
      }).length ? "pointer" : "";
    });
    this.map.on("error", (event) => {
      if ((event as { sourceId?: string }).sourceId === "bavaria-aerial" && this.aerial) {
        this.setAerial(false);
        callbacks.onError("Aerial imagery is temporarily unavailable. The campus map is still available.");
      } else if (!this.ready && this.alive) {
        callbacks.onError("The 3D map could not start. Please retry, or open the building list.");
      }
    });
    void this.load();
  }

  private changeStage(stage: JourneyStage) { this.stage = stage; this.callbacks.onStage(stage); }

  private async load() {
    try {
      const response = await fetch(STYLE_URL);
      if (!response.ok) throw new Error(`Map service returned ${response.status}`);
      const style = await response.json() as StyleSpecification;
      if (!this.alive) return;
      // The campus surface emphasises buildings and paths; dense POI symbols obscure both.
      style.layers = style.layers.filter((layer) => !(layer.type === "symbol" && layer["source-layer"] === "poi" && layer.id !== "poi_transit"));
      for (const layer of style.layers) {
        if (layer.type === "symbol" && /shield/.test(layer.id) && layer.filter) {
          layer.filter = ["all", ["has", "ref_length"], layer.filter as ExpressionSpecification];
        }
        if (layer.type === "background") layer.paint = { ...layer.paint, "background-color": "#edf0e6" };
        if (layer.type === "fill" && /park|wood|grass|landcover|landuse/i.test(layer.id)) {
          layer.paint = { ...layer.paint, "fill-color": /wood|forest/i.test(layer.id) ? "#a8bf91" : "#d3dfbd" };
        }
        if (layer.type === "fill" && /water/.test(layer.id)) layer.paint = { ...layer.paint, "fill-color": "#a9cbd9" };
        if (layer.type === "fill" && layer["source-layer"] === "building") layer.paint = { ...layer.paint, "fill-color": "#deddd1" };
      }
      this.map.once("style.load", () => {
        if (!this.alive) return;
        this.map.setProjection({ type: "globe" });
        this.addLayers(); this.ready = true; this.setAerial(this.aerial);
        void this.addTrees();
        if (this.selected) this.setSelected(this.selected);
        this.callbacks.onReady();
      });
      this.map.setStyle(style);
    } catch (error) {
      if (this.alive) this.callbacks.onError(`The map could not load. ${error instanceof Error ? error.message : "Please retry."}`);
    }
  }

  private addLayers() {
    const firstLabel = this.map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
    this.map.addSource("bavaria-aerial", { type: "raster", tileSize: 512, minzoom: 8, maxzoom: 22,
      bounds: [8.9, 47.2, 13.9, 50.7], attribution: '<a href="https://www.geodaten.bayern.de/">Bayerische Vermessungsverwaltung</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>',
      tiles: ["https://geoservices.bayern.de/od/wms/dop/v1/dop20?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=by_dop20c&STYLES=&FORMAT=image/jpeg&TRANSPARENT=false&SRS=EPSG:3857&WIDTH=512&HEIGHT=512&BBOX={bbox-epsg-3857}"] });
    this.map.addLayer({ id: "aerial", type: "raster", source: "bavaria-aerial", layout: { visibility: "none" },
      paint: { "raster-fade-duration": 350 } }, firstLabel);
    this.map.addLayer({ id: "context-buildings", type: "fill-extrusion", source: "openmaptiles", "source-layer": "building", minzoom: 14,
      paint: { "fill-extrusion-color": "#e4e1d4", "fill-extrusion-height": ["coalesce", ["get", "render_height"], 8],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0], "fill-extrusion-opacity": 0.97 } }, firstLabel);
    this.map.addSource("known", { type: "geojson", data: buildingFeatures(this.catalog.buildings) });
    this.map.addLayer({ id: "known-buildings", source: "known", type: "fill-extrusion", minzoom: 13,
      paint: { "fill-extrusion-color": "#aabfc3", "fill-extrusion-height": ["get", "height"], "fill-extrusion-opacity": 0.98 } }, firstLabel);
    this.map.addSource("selection", { type: "geojson", data: EMPTY });
    this.map.addLayer({ id: "selection-outline", source: "selection", type: "line", minzoom: 13,
      paint: { "line-color": "#c9f23e", "line-width": 4, "line-opacity": 0.95 } });
    this.map.addSource("facade", { type: "geojson", data: EMPTY });
    this.map.addLayer({ id: "facade-windows", source: "facade", type: "fill-extrusion", minzoom: 15,
      paint: { "fill-extrusion-color": "#617a7d", "fill-extrusion-base": ["get", "base"],
        "fill-extrusion-height": ["+", ["get", "base"], ["get", "height"]], "fill-extrusion-opacity": 0.85 } });
    this.map.addSource("pins", { type: "geojson", data: { type: "FeatureCollection", features: this.catalog.buildings.map((b) => ({
      type: "Feature", geometry: { type: "Point", coordinates: b.center }, properties: { id: b.id, name: b.label },
    })) } });
    this.map.addLayer({ id: "building-pins", type: "circle", source: "pins", maxzoom: 16,
      paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 2, 4, 14, 7], "circle-color": "#dcff58",
        "circle-stroke-color": "#27372d", "circle-stroke-width": 2 } });
    this.map.addLayer({ id: "building-names", type: "symbol", source: "pins", minzoom: 12,
      layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 12,
        "text-anchor": "top", "text-offset": [0, 1], "text-max-width": 18 },
      paint: { "text-color": "#253c36", "text-halo-color": "#ffffff", "text-halo-width": 2 } });
    this.map.addSource("indoor", { type: "geojson", data: EMPTY });
    for (const [id, kind, opacity] of [["indoor-rooms", "room", 0.96], ["indoor-walls", "wall", 1], ["indoor-assets", "asset", 1]] as const) {
      this.map.addLayer({ id, type: "fill-extrusion", source: "indoor", minzoom: 14, filter: ["==", ["get", "kind"], kind],
        paint: { "fill-extrusion-color": ["get", "color"], "fill-extrusion-base": ["get", "base"],
          "fill-extrusion-height": ["+", ["get", "base"], ["get", "height"]], "fill-extrusion-opacity": opacity } });
    }
    this.map.setLight({ anchor: "viewport", color: "#fff7e6", intensity: 0.42, position: [1.5, 210, 35] });
  }

  private async addTrees() {
    // Only OSM-mapped tree positions; heights and crowns are architectural display values.
    try {
      const response = await fetch("/maps/trees.json");
      if (!response.ok || !this.alive) return;
      const trees = await response.json() as FeatureCollection<Point>;
      if (!this.alive) return;
      const crowns: FeatureCollection<Polygon> = { type: "FeatureCollection", features: [] };
      for (const tree of trees.features) {
        const [lon, lat] = tree.geometry.coordinates;
        if (lon === undefined || lat === undefined) continue;
        for (const [radius, base, height] of [[1.3, 1.8, 1.1], [2.0, 2.9, 1.5], [1.4, 4.4, 1.1], [0.6, 5.5, 0.6]]) {
          const ring = Array.from({ length: 13 }, (_, i) => {
            const angle = i / 12 * Math.PI * 2;
            return [lon + Math.cos(angle) * radius! / (111320 * Math.cos(lat * Math.PI / 180)), lat + Math.sin(angle) * radius! / 111320];
          });
          crowns.features.push({ type: "Feature", geometry: { type: "Polygon", coordinates: [ring] },
            properties: { base, height: base! + height!, color: Number(tree.properties?.osmId) % 2 ? "#8aa66b" : "#9ab27e" } });
        }
      }
      this.map.addSource("campus-trees", { type: "geojson", data: crowns });
      this.map.addLayer({ id: "campus-trees", type: "fill-extrusion", source: "campus-trees", minzoom: 15,
        paint: { "fill-extrusion-color": ["get", "color"], "fill-extrusion-base": ["get", "base"],
          "fill-extrusion-height": ["get", "height"], "fill-extrusion-opacity": 0.96 } }, "known-buildings");
    } catch { /* Optional landscape detail must not block building navigation. */ }
  }

  setSelected(building: CampusBuilding) {
    this.selected = building;
    if (!this.ready) return;
    // `within` only evaluates point/line features. Distance also handles polygon overlap and
    // removes the basemap shell, including its building parts, before our own shell/interior draws.
    this.map.setFilter("context-buildings", [">", ["distance", building.outline], 0.15]);
    this.map.setPaintProperty("known-buildings", "fill-extrusion-color", ["case", ["==", ["get", "id"], building.id], "#afc0b8", "#aebfc7"]);
    this.source("selection").setData(buildingFeatures([building]));
    this.source("facade").setData(facadeFeatures(building));
    this.showExterior();
  }

  private source(id: string) { return this.map.getSource(id) as GeoJSONSource; }

  async flyTo(building: CampusBuilding) {
    if (!this.ready) return;
    this.flight?.abort(); this.map.stop();
    this.setSelected(building);
    const flight = new AbortController(); this.flight = flight;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      this.map.jumpTo({ center: building.center, zoom: this.targetZoom(building), pitch: 56, bearing: -24 });
      this.flight = undefined; this.changeStage("campus"); return;
    }
    this.map.jumpTo({ center: [building.center[0], 34], zoom: 1.8, pitch: 0, bearing: 0 });
    this.changeStage("flying");
    await this.move((step) => this.map.flyTo({ center: building.center, zoom: this.targetZoom(building) - 0.7,
      pitch: 0, bearing: 0, duration: 4200, curve: 1.25 }, { journeyStep: step }), flight.signal);
    if (flight.signal.aborted || !this.alive) return;
    this.changeStage("arriving");
    await this.move((step) => this.map.easeTo({ zoom: this.targetZoom(building), pitch: 56, bearing: -24, duration: 1500 }, { journeyStep: step }), flight.signal);
    if (flight.signal.aborted || !this.alive) return;
    this.flight = undefined; this.changeStage("campus");
  }

  private targetZoom(building: CampusBuilding) {
    const [w, s, e, n] = building.bounds;
    const diagonal = Math.hypot((e - w) * Math.cos(building.center[1] * Math.PI / 180), n - s) * 111320;
    const container = this.map.getContainer();
    const mobile = window.matchMedia("(max-width: 760px)").matches;
    const scale = Math.min(container.clientWidth / 960, Math.max(250, container.clientHeight - (mobile ? 265 : 0)) / 650);
    return Math.max(13.4, Math.min(18.4, 17.0 - Math.log2(diagonal / 260) + Math.log2(Math.max(0.25, scale))));
  }

  private move(action: (step: number) => void, signal: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
      const step = ++this.movement;
      const cleanup = () => { this.map.off("moveend", done); signal.removeEventListener("abort", cleanup); resolve(); };
      const done = (event: unknown) => { if ((event as { journeyStep?: number }).journeyStep === step) cleanup(); };
      signal.addEventListener("abort", cleanup, { once: true }); this.map.on("moveend", done); action(step);
    });
  }

  globe() {
    if (!this.ready) return;
    this.flight?.abort(); this.flight = undefined; this.map.stop(); this.showExterior();
    this.map.flyTo({ center: [12, 30], zoom: 1.65, pitch: 0, bearing: 0, duration: 2000 });
    this.changeStage("globe");
  }

  setAerial(enabled: boolean) {
    this.aerial = enabled;
    if (!this.ready) return;
    this.map.setLayoutProperty("aerial", "visibility", enabled ? "visible" : "none");
    this.map.setPaintProperty("context-buildings", "fill-extrusion-opacity", enabled ? 0.78 : 0.97);
  }

  showExterior() {
    this.indoor = undefined;
    if (!this.ready) return;
    this.source("indoor").setData(EMPTY);
    this.map.setLayoutProperty("facade-windows", "visibility", "visible");
    this.map.setFilter("known-buildings", null);
    this.map.setFilter("building-names", null);
    this.callbacks.onRoom(undefined);
    if (this.stage === "inside") this.changeStage("campus");
  }

  showIndoor(scene: BuildingScene, building: CampusBuilding, gap: number, floorId: string | null) {
    if (!this.ready || !building.localFrame) return;
    if (this.indoor?.scene !== scene || this.indoor?.building.id !== building.id) {
      this.source("indoor").setData(indoorFeatures(scene, building.localFrame));
      this.indoor = { scene, building };
    }
    this.map.setLayoutProperty("facade-windows", "visibility", "none");
    this.map.setFilter("known-buildings", ["!=", ["get", "id"], building.id]);
    this.map.setFilter("building-names", ["!=", ["get", "id"], building.id]);
    this.setIndoorLayout(gap, floorId);
    this.changeStage("inside");
  }

  focusForIndoor(pose?: ExteriorPose) {
    if (!this.ready || !this.selected) return;
    this.flight?.abort(); this.flight = undefined; this.map.stop();
    this.map.jumpTo({ center: this.selected.center, zoom: this.targetZoom(this.selected),
      pitch: Math.max(0, Math.min(75, pose?.tilt ?? this.map.getPitch())),
      bearing: pose?.heading ?? this.map.getBearing() });
  }

  setIndoorLayout(gap: number, floorId: string | null) {
    if (!this.indoor) return;
    const base: ExpressionSpecification = ["+", ["get", "base"], ["*", ["get", "rank"], gap]];
    for (const [id, kind] of [["indoor-rooms", "room"], ["indoor-walls", "wall"], ["indoor-assets", "asset"]] as const) {
      this.map.setPaintProperty(id, "fill-extrusion-base", base);
      this.map.setPaintProperty(id, "fill-extrusion-height", ["+", base, ["get", "height"]]);
      this.map.setFilter(id, floorId ? ["all", ["==", ["get", "kind"], kind], ["==", ["get", "floorId"], floorId]] : ["==", ["get", "kind"], kind]);
    }
  }

  topDown() {
    if (!this.ready) return;
    this.map.easeTo({ pitch: this.map.getPitch() > 20 ? 0 : 56, duration: 800 });
  }

  destroy() { this.alive = false; this.resizeObserver.disconnect(); this.flight?.abort(); this.map.remove(); }
}

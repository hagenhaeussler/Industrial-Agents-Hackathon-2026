import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CampusBuilding } from "./geography";
import { CampusMap } from "./map";
import { EARTH_LAYER_ID, EARTH_SOURCE_ID } from "./earth-scene";

type CameraOptions = { center?: [number, number]; zoom?: number; pitch?: number; bearing?: number; duration?: number };
type MapEvent = { journeyStep?: number; originalEvent?: Event; sourceId?: string };
type Handler = (event: MapEvent) => void;
type TestLayer = { id: string; type: string; minzoom?: number; maxzoom?: number; layout?: Record<string, unknown> };
interface TestMap {
  zoom: number;
  center: [number, number];
  pending?: { options: CameraOptions; event: MapEvent };
  state: Record<string, unknown>;
  flyTo: ReturnType<typeof vi.fn>;
  easeTo: ReturnType<typeof vi.fn>;
  jumpTo: ReturnType<typeof vi.fn>;
  remove: ReturnType<typeof vi.fn>;
  setLayerZoomRange: ReturnType<typeof vi.fn>;
  getStyle(): { sources: Record<string, unknown>; layers: TestLayer[] };
  getLayer(id: string): TestLayer | undefined;
  emit(name: string, event?: MapEvent): void;
  completeMove(): void;
}

vi.mock("maplibre-gl", () => ({
  NavigationControl: class {}, ScaleControl: class {}, setWorkerUrl: vi.fn(),
  Map: class {
    zoom: number; center: [number, number]; pitch = 0; bearing = 0;
    pending?: { options: CameraOptions; event: MapEvent };
    state: Record<string, unknown> = {};
    listeners = new globalThis.Map<string, Set<Handler>>();
    sources = new globalThis.Map<string, { setData: ReturnType<typeof vi.fn> }>();
    style = { sources: {} as Record<string, unknown>, layers: [] as TestLayer[] };
    constructor(private options: { zoom: number; center: [number, number]; container: HTMLElement }) {
      this.zoom = options.zoom; this.center = options.center;
    }
    on(name: string, handler: Handler) {
      if (!this.listeners.has(name)) this.listeners.set(name, new Set());
      this.listeners.get(name)!.add(handler);
    }
    off(name: string, handler: Handler) { this.listeners.get(name)?.delete(handler); }
    once(name: string, handler: Handler) {
      const once = (event: MapEvent) => { this.off(name, once); handler(event); };
      this.on(name, once);
    }
    emit(name: string, event: MapEvent = {}) { [...(this.listeners.get(name) ?? [])].forEach(handler => handler(event)); }
    move(options: CameraOptions, event: MapEvent = {}) { this.stop(); this.pending = { options, event }; this.emit("movestart", event); }
    flyTo = vi.fn((options: CameraOptions, event?: MapEvent) => this.move(options, event));
    easeTo = vi.fn((options: CameraOptions, event?: MapEvent) => this.move(options, event));
    jumpTo = vi.fn((options: CameraOptions) => { this.stop(); this.apply(options); });
    private apply(options: CameraOptions) {
      if (options.center) this.center = options.center;
      if (options.zoom !== undefined) this.zoom = options.zoom;
      if (options.pitch !== undefined) this.pitch = options.pitch;
      if (options.bearing !== undefined) this.bearing = options.bearing;
    }
    completeMove() {
      const pending = this.pending; this.pending = undefined;
      if (pending) { this.apply(pending.options); this.emit("moveend", pending.event); }
    }
    stop = vi.fn(() => {
      const pending = this.pending; this.pending = undefined;
      if (pending) this.emit("moveend", pending.event);
    });
    isMoving() { return !!this.pending; }
    getZoom() { return this.zoom; }
    getCenter() { return { lng: this.center[0], lat: this.center[1] }; }
    getPitch() { return this.pitch; }
    getBearing() { return this.bearing; }
    getContainer() { return this.options.container; }
    getCanvas() { return { style: {} }; }
    setStyle(style: { sources: Record<string, unknown>; layers: TestLayer[] }) { this.style = style; this.emit("style.load"); }
    getStyle() { return this.style; }
    getLayer(id: string) { return this.style.layers.find(layer => layer.id === id); }
    addSource(id: string) { this.sources.set(id, { setData: vi.fn() }); }
    getSource(id: string) { return this.sources.get(id); }
    addLayer(layer: TestLayer) { this.style.layers.push(layer); }
    setGlobalStateProperty(name: string, value: unknown) { this.state[name] = value; }
    addControl() {} setProjection() {} setLight() {} setFilter() {} setPadding() {} resize() {}
    setLayoutProperty(id: string, property: string, value: unknown) {
      const layer = this.getLayer(id);
      if (!layer) throw new Error(`Missing layer: ${id}`);
      layer.layout = { ...layer.layout, [property]: value };
    }
    setLayerZoomRange = vi.fn((id: string, minzoom: number, maxzoom: number) => {
      const layer = this.getLayer(id);
      if (!layer) throw new Error(`Missing layer: ${id}`);
      Object.assign(layer, { minzoom, maxzoom });
    });
    setPaintProperty() {} queryRenderedFeatures() { return []; }
    remove = vi.fn();
  },
}));

const building = (id: string, longitude: number): CampusBuilding => ({
  id, name: id, label: id, address: null, city: null, postcode: null,
  center: [longitude, 48], bounds: [longitude - .001, 47.999, longitude + .001, 48.001],
  outline: { type: "Polygon", coordinates: [[[longitude - .001, 47.999], [longitude + .001, 47.999],
    [longitude + .001, 48.001], [longitude - .001, 48.001], [longitude - .001, 47.999]]] },
  levels: [0, 1], floors: 2, rooms: 1, spaces: 1, assets: 0, height: 6, osmUrl: "https://example.com/building",
});
const first = building("first", 11), second = building("second", 12);
let frames: Map<number, FrameRequestCallback>, nextFrame: number;
let media: { matches: boolean; addEventListener: ReturnType<typeof vi.fn>; removeEventListener: ReturnType<typeof vi.fn> };
let disconnect: ReturnType<typeof vi.fn>;
const controllers: CampusMap[] = [];

beforeEach(() => {
  frames = new Map(); nextFrame = 0;
  media = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() };
  disconnect = vi.fn();
  vi.stubGlobal("matchMedia", (query: string) => query.includes("reduced-motion") ? media : { matches: false });
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect = disconnect; });
  vi.stubGlobal("requestAnimationFrame", vi.fn((callback: FrameRequestCallback) => { frames.set(++nextFrame, callback); return nextFrame; }));
  vi.stubGlobal("cancelAnimationFrame", vi.fn((id: number) => frames.delete(id)));
  vi.spyOn(performance, "now").mockReturnValue(0);
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ ok: true, json: async () => url.endsWith("trees.json")
    ? { type: "FeatureCollection", features: [] }
    : { version: 8, sources: { openmaptiles: { type: "vector", tiles: [] } }, layers: [
      { id: "background", type: "background" },
      { id: "land", type: "fill", source: "openmaptiles", "source-layer": "landcover", minzoom: 0, maxzoom: 22 },
      { id: "label", type: "symbol", source: "openmaptiles", "source-layer": "place", minzoom: 3 },
      { id: "detail", type: "line", source: "openmaptiles", "source-layer": "transportation", minzoom: 14, maxzoom: 20 },
    ] } })));
});
afterEach(() => {
  controllers.splice(0).forEach(controller => controller.destroy());
  vi.restoreAllMocks(); vi.unstubAllGlobals();
});

async function ready() {
  const host = document.createElement("div");
  Object.defineProperties(host, { clientWidth: { value: 960 }, clientHeight: { value: 650 } });
  const callbacks = { onStage: vi.fn(), onSelect: vi.fn(), onRoom: vi.fn(), onError: vi.fn(), onReady: vi.fn() };
  const controller = new CampusMap(host, { featuredBuildingId: first.id, buildings: [first, second] }, callbacks);
  controllers.push(controller);
  await vi.waitFor(() => expect(callbacks.onReady).toHaveBeenCalledOnce());
  expect(callbacks.onError).not.toHaveBeenCalled();
  return { controller, map: controller.map as unknown as TestMap, callbacks };
}
async function settle() { for (let i = 0; i < 6; i++) await Promise.resolve(); }
function frame(now: number) { const pending = [...frames.values()]; frames.clear(); pending.forEach(callback => callback(now)); }

describe("campus arrival controller", () => {
  it("restores visible vector geography after Earth tile failure and reports it once without changing sources", async () => {
    const { controller, map, callbacks } = await ready();
    const sources = structuredClone(map.getStyle().sources);
    expect(map.getLayer("land")?.minzoom).toBe(9);
    expect(map.getLayer("label")?.minzoom).toBe(9);

    map.emit("error", { sourceId: EARTH_SOURCE_ID });
    expect(map.getLayer(EARTH_LAYER_ID)?.layout?.visibility).toBe("none");
    expect(map.getLayer("background")).toMatchObject({ minzoom: 0, maxzoom: 24 });
    expect(map.getLayer("land")).toMatchObject({ minzoom: 0, maxzoom: 22 });
    expect(map.getLayer("label")).toMatchObject({ minzoom: 3, maxzoom: 24 });
    expect(map.getLayer("detail")).toMatchObject({ minzoom: 14, maxzoom: 20 });
    expect(map.getStyle().sources).toEqual(sources);
    expect(callbacks.onError).toHaveBeenCalledExactlyOnceWith(expect.stringContaining("Showing the map instead"));

    const restored = map.setLayerZoomRange.mock.calls.length;
    map.emit("error", { sourceId: EARTH_SOURCE_ID }); map.emit("error", { sourceId: EARTH_SOURCE_ID });
    expect(callbacks.onError).toHaveBeenCalledOnce();
    expect(map.setLayerZoomRange).toHaveBeenCalledTimes(restored);
    const arrival = controller.flyTo(first); controller.skipArrival(); await arrival;
    expect(map.jumpTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: first.center }));
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
  });

  it("stages the first globe arrival and takes the shorter path for subsequent building selections", async () => {
    const { controller, map, callbacks } = await ready();
    const arrival = controller.flyTo(first);
    expect(map.easeTo).toHaveBeenLastCalledWith(expect.objectContaining({ zoom: 2.2, pitch: 0 }), expect.anything());
    map.completeMove(); await settle();
    expect(map.flyTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: first.center, duration: 4200 }), expect.anything());
    map.completeMove(); await settle();
    expect(callbacks.onStage).toHaveBeenLastCalledWith("arriving");
    map.completeMove(); frame(1500); await arrival;
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
    expect(map.state["campus-rise"]).toBe(1);

    map.easeTo.mockClear(); map.flyTo.mockClear();
    const next = controller.flyTo(second);
    expect(map.flyTo).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ center: second.center, duration: 1600 }), expect.anything());
    expect(map.easeTo).not.toHaveBeenCalled();
    map.completeMove(); await settle(); map.completeMove(); frame(1500); await next;
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
  });

  it("skip lands at the newest selection and old move events cannot advance the superseded flight", async () => {
    const { controller, map, callbacks } = await ready();
    const older = controller.flyTo(first), staleEvent = map.pending!.event;
    const current = controller.flyTo(second);
    controller.skipArrival();
    await Promise.all([older, current]);
    const stages = callbacks.onStage.mock.calls.length, moves = map.easeTo.mock.calls.length + map.flyTo.mock.calls.length;
    map.emit("moveend", staleEvent); await settle(); frame(1000);
    expect(map.jumpTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: second.center, pitch: 56 }));
    expect(map.state["campus-rise"]).toBe(1);
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
    expect(callbacks.onStage).toHaveBeenCalledTimes(stages);
    expect(map.easeTo.mock.calls.length + map.flyTo.mock.calls.length).toBe(moves);
  });

  it("an already-dequeued rise frame cannot flatten or change the next building's completed view", async () => {
    const { controller, map, callbacks } = await ready();
    const older = controller.flyTo(first, { cinematic: false });
    map.completeMove(); await settle();
    expect(callbacks.onStage).toHaveBeenLastCalledWith("arriving");
    const dequeued = [...frames.values()]; frames.clear();
    const current = controller.flyTo(second);
    controller.skipArrival(); await Promise.all([older, current]);
    const stages = callbacks.onStage.mock.calls.length;
    dequeued.forEach(callback => callback(700)); await settle();
    expect(map.state["campus-rise"]).toBe(1);
    expect(map.jumpTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: second.center }));
    expect(callbacks.onStage).toHaveBeenCalledTimes(stages);
  });

  it("hands the camera to user input, stopping idle rotation and aborting an arrival", async () => {
    const { controller, map, callbacks } = await ready();
    frame(0);
    expect(map.easeTo).toHaveBeenCalledWith(expect.objectContaining({ duration: 6000 }));
    map.emit("movestart", { originalEvent: new Event("wheel") }); map.completeMove(); frame(10);
    expect(map.easeTo).toHaveBeenCalledOnce();

    const arrival = controller.flyTo(first);
    map.zoom = 10;
    map.emit("movestart", { originalEvent: new Event("pointerdown") });
    await arrival;
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
    expect(map.state["campus-rise"]).toBe(1);
    const moves = map.easeTo.mock.calls.length + map.flyTo.mock.calls.length;
    map.completeMove(); frame(2000); await settle();
    expect(map.easeTo.mock.calls.length + map.flyTo.mock.calls.length).toBe(moves);
  });

  it("reduced motion opens the selected building directly without rotation or camera flights", async () => {
    media.matches = true;
    const { controller, map, callbacks } = await ready();
    expect(frames.size).toBe(0);
    await controller.flyTo(first);
    expect(map.easeTo).not.toHaveBeenCalled(); expect(map.flyTo).not.toHaveBeenCalled();
    expect(map.jumpTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: first.center, pitch: 56 }));
    expect(map.state["campus-rise"]).toBe(1);
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
  });

  it("enabling reduced motion mid-flight finishes immediately at the selected building", async () => {
    const { controller, map, callbacks } = await ready();
    const arrival = controller.flyTo(second);
    media.matches = true;
    media.addEventListener.mock.calls[0]![1]();
    await arrival;
    expect(map.jumpTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: second.center }));
    expect(map.state["campus-rise"]).toBe(1);
    expect(callbacks.onStage).toHaveBeenLastCalledWith("campus");
  });

  it("teardown cancels pending rotation/rise work, removes the preference listener and destroys the map", async () => {
    const { controller, map, callbacks } = await ready();
    const arrival = controller.flyTo(first, { cinematic: false });
    map.completeMove(); await settle();
    expect(frames.size).toBeGreaterThan(0);
    const stages = callbacks.onStage.mock.calls.length;
    controller.destroy(); controllers.splice(controllers.indexOf(controller), 1);
    await arrival;
    expect(frames.size).toBe(0);
    expect(media.removeEventListener).toHaveBeenCalledWith("change", media.addEventListener.mock.calls[0]![1]);
    expect(disconnect).toHaveBeenCalledOnce(); expect(map.remove).toHaveBeenCalledOnce();
    expect(callbacks.onStage).toHaveBeenCalledTimes(stages);
  });
});

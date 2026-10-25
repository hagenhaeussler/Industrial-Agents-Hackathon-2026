import type { CampusBuilding } from "./geography";

export interface ExteriorPose { heading: number; tilt: number; }
export interface GoogleMapElement extends HTMLElement {
  heading: number;
  tilt: number;
  mode: "HYBRID" | "SATELLITE";
  stopCameraAnimation?(): void;
  flyCameraTo(options: { endCamera: Record<string, unknown>; durationMillis: number }): void;
}
export interface Google3dLibrary {
  Map3DElement: new (options: Record<string, unknown>) => GoogleMapElement;
  FlattenerElement?: new (options: Record<string, unknown>) => HTMLElement;
  Model3DInteractiveElement?: new (options: Record<string, unknown>) => GoogleModelElement;
  Model3DElement?: new (options:Record<string,unknown>)=>GoogleModelElement;
}
export interface GoogleModelElement extends HTMLElement {
  position: {lat:number;lng:number;altitude:number};
}
type GoogleWindow = Window & {
  google?: { maps: { maps3d?:Google3dLibrary;importLibrary(name: string): Promise<Google3dLibrary> } };
  __tybMapsLoaded?: () => void;
};

let library: Google3dLibrary | undefined;
let loading: Promise<Google3dLibrary> | undefined;
export function currentGoogle3d() {
  const cached=library ?? (window as GoogleWindow).google?.maps.maps3d;
  return cached?.Map3DElement ? cached : undefined;
}

/** A browser key is entered at runtime only. Never write it to storage, config, logs or a bundle. */
export function loadGoogle3d(key: string): Promise<Google3dLibrary> {
  const cached=currentGoogle3d();
  if (cached) return Promise.resolve(cached);
  if (loading) return loading;
  const scope = window as GoogleWindow;
  loading = new Promise<Google3dLibrary>((resolve, reject) => {
    const script = document.createElement("script");
    const fail = () => { cleanup(); script.remove(); reject(new Error("Google 3D could not load. Check your key and allowed websites.")); };
    const timeout = window.setTimeout(fail, 30000);
    const cleanup = () => { window.clearTimeout(timeout); delete scope.__tybMapsLoaded; };
    scope.__tybMapsLoaded = () => {
      if (!scope.google) return fail();
      void scope.google.maps.importLibrary("maps3d").then((result) => {
        cleanup(); library = result; resolve(result);
      }, fail);
    };
    script.async = true;
    script.onerror = fail;
    script.src = "https://maps.googleapis.com/maps/api/js?" + new URLSearchParams({
      key, v: "weekly", libraries: "maps3d", loading: "async", callback: "__tybMapsLoaded",
    });
    document.head.append(script);
  }).catch((error: unknown) => { loading = undefined; throw error; });
  return loading;
}

export function exteriorCamera(building: CampusBuilding, aspect = 1.5) {
  const [w, s, e, n] = building.bounds;
  const width = (e - w) * Math.cos(building.center[1] * Math.PI / 180) * 111320;
  const height = (n - s) * 111320;
  return {
    center: { lat: building.center[1], lng: building.center[0], altitude: 0 },
    altitudeMode: "RELATIVE_TO_GROUND", range: Math.max(220, Math.hypot(width, height) * 2.4 / Math.min(1, aspect)),
    tilt: 56, heading: 336,
  };
}

/** Hit-test the real footprint, including courtyards; neighbouring buildings must not open this plan. */
export function isBuildingClick(building: CampusBuilding, position?: { lat: number; lng: number }): boolean {
  if (!position || !Number.isFinite(position.lat) || !Number.isFinite(position.lng)) return false;
  const inRing = (ring: number[][]) => {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const a = ring[i]!, b = ring[j]!;
      if ((a[1]! > position.lat) !== (b[1]! > position.lat)
        && position.lng < (b[0]! - a[0]!) * (position.lat - a[1]!) / (b[1]! - a[1]!) + a[0]!) inside = !inside;
    }
    return inside;
  };
  const [outer, ...holes] = building.outline.coordinates;
  return !!outer && inRing(outer) && !holes.some(inRing);
}

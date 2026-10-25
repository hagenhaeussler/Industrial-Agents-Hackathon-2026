import type { BuildingScene } from "@locora/view";
import { planToGeographic, type CampusBuilding } from "./geography";
import { floorAltitude } from "./model-placement";

/** Fit the actual footprint and visible floor heights into the space between map controls. */
export function indoorCamera(building: CampusBuilding, scene: BuildingScene, gap: number,
  focus: string | null, aspect: number, roomId?: string) {
  const floors = scene.floors.filter(f => !focus || f.id === focus);
  if (!floors.length) return undefined;
  const room = roomId ? floors.flatMap(f => f.spaces).find(s => s.id === roomId) : undefined;
  const ring = room && building.localFrame ? room.outline.map(p => planToGeographic(building.localFrame!,...p))
    : building.outline.coordinates[0]!;
  if (!ring.length) return undefined;
  const center = room ? [
    (Math.min(...ring.map(p=>p[0]!))+Math.max(...ring.map(p=>p[0]!)))/2,
    (Math.min(...ring.map(p=>p[1]!))+Math.max(...ring.map(p=>p[1]!)))/2,
  ] : building.center;
  const lowest = Math.min(...scene.floors.map(f=>f.elevation));
  const heights = floors.map(f=>floorAltitude(f,scene.floors.indexOf(f),lowest,gap,focus));
  const bottom = Math.min(...heights), top = Math.max(...heights)+1.5;
  const altitude = (bottom+top)/2;
  const tilt = focus ? 16 : 60, heading = focus ? 0 : 336;
  const radians = Math.PI/180, pitch = tilt*radians, yaw = heading*radians;
  // Google's explicit 35-degree FOV. Leave space for the level rail and top/bottom controls.
  const tangent = Math.tan(17.5*radians), safeAspect = Math.max(.3,aspect);
  let range = room ? 32 : 100;
  for (const p of ring) {
    const east = (p[0]!-center[0]!)*111320*Math.cos(center[1]!*radians);
    const north = (p[1]!-center[1]!)*111320;
    const x = east*Math.cos(yaw)-north*Math.sin(yaw);
    const depth = east*Math.sin(yaw)+north*Math.cos(yaw);
    for (const height of [bottom,top]) {
      const z = height-altitude;
      const y = depth*Math.cos(pitch)+z*Math.sin(pitch);
      const towardCamera = -depth*Math.sin(pitch)+z*Math.cos(pitch);
      range = Math.max(range,towardCamera+Math.abs(x)/(tangent*safeAspect*.8),
        towardCamera+Math.abs(y)/(tangent*.7));
    }
  }
  return {center:{lat:center[1]!,lng:center[0]!,altitude},altitudeMode:"RELATIVE_TO_GROUND",range,tilt,heading};
}

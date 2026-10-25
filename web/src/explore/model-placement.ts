import type { CampusBuilding } from "./geography";
import { planToGeographic } from "./geography";
import type {Polygon} from "geojson";

export interface GoogleFloorModel { id: string; level: number; elevation: number; height: number; src: string; }
export interface GoogleIndoorManifest {
  buildingId: string; sourceSha256: string; frameSha256: string; anchor: [number,number];
  floors: GoogleFloorModel[];
  mask?:Polygon;
  maskPaddingM?:number;
  rooms?:Record<string,string>;
}

/** WGS84 ECEF -> local east/north. No guessed orientation, Mercator scale or building-specific offset. */
export function planToModel(building: CampusBuilding, point: readonly [number,number]): [number,number] {
  if (!building.localFrame) throw new Error("A calibrated geographic frame is required");
  const rad = Math.PI/180, a = 6378137, e2 = 6.6943799901413165e-3;
  const ecef = ([lon,lat]: readonly [number,number]) => {
    const l = lon*rad, p = lat*rad, n = a/Math.sqrt(1-e2*Math.sin(p)**2);
    return [n*Math.cos(p)*Math.cos(l),n*Math.cos(p)*Math.sin(l),n*(1-e2)*Math.sin(p)];
  };
  const origin = ecef(building.center), target = ecef(planToGeographic(building.localFrame,...point));
  const dx = target[0]! - origin[0]!, dy = target[1]! - origin[1]!, dz = target[2]! - origin[2]!;
  const l = building.center[0]*rad, p = building.center[1]*rad;
  return [-Math.sin(l)*dx+Math.cos(l)*dy,-Math.sin(p)*Math.cos(l)*dx-Math.sin(p)*Math.sin(l)*dy+Math.cos(p)*dz];
}

export function floorAltitude(floor: Pick<GoogleFloorModel,"id"|"elevation">, rank: number, lowest: number, gap: number, focus: string | null) {
  // The terrain masks basements. In inspection mode lift the stack (or a selected basement) above it.
  const lift = focus === floor.id && floor.elevation < 0 ? -floor.elevation : !focus && gap > 0 ? -Math.min(0,lowest) : 0;
  return floor.elevation + lift + (focus ? 0 : rank*gap) + .3;
}

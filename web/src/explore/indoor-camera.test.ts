import {describe,expect,it} from "vitest";
import {compileScene} from "@locora/view";
import {fixture} from "../../../packages/building-view/src/testing/fixture";
import type {CampusBuilding} from "./geography";
import {indoorCamera} from "./indoor-camera";
import {exteriorCamera} from "./google3d";

const scene=compileScene(fixture());
const building={center:[0,0],bounds:[-.001,-.001,.001,.001],
  outline:{type:"Polygon",coordinates:[[[-.001,-.001],[.001,-.001],[.001,.001],[-.001,.001],[-.001,-.001]]]},
  localFrame:{crs:"EPSG:3857",matrix:[[1,0,0],[0,1,0]]},
} as CampusBuilding;

describe("camera from exterior to floors and room detail",()=>{
  it("moves closer on entry, aims at the visible stack, and fits a narrow canvas",()=>{
    const overview=indoorCamera(building,scene,8,null,1)!;
    expect(overview.range).toBeLessThan(exteriorCamera(building,1).range);
    expect(overview.center.altitude).toBeGreaterThan(0);
    expect(overview.altitudeMode).toBe("RELATIVE_TO_GROUND");
    expect(indoorCamera(building,scene,8,null,.5)!.range).toBeGreaterThan(overview.range);
    expect(indoorCamera(building,scene,12,null,1)!.center.altitude).toBeGreaterThan(overview.center.altitude);
  });
  it("reveals one level from above and zooms to the actual selected room",()=>{
    const overview=indoorCamera(building,scene,8,null,1)!;
    const floor=indoorCamera(building,scene,8,"F0",1)!;
    const room=indoorCamera(building,scene,8,"F0",1,"A")!;
    expect(floor.tilt).toBeLessThan(overview.tilt);
    expect(room.range).toBeLessThan(floor.range);
    expect(room.center.lng).toBeCloseTo(2/111319.490793,8);
    expect(room.center.lat).toBeCloseTo(1.5/111319.490793,8);
    expect(room.center.altitude).toBeCloseTo(1.05);
    expect(indoorCamera(building,scene,8,"missing",1)).toBeUndefined();
  });
});

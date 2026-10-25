import {describe,expect,it} from "vitest";
import {floorAltitude,planToModel,type GoogleFloorModel} from "./model-placement";
import type {CampusBuilding} from "./geography";
const building={center:[0,0],localFrame:{crs:"EPSG:3857",matrix:[[1,0,0],[0,1,0]]}} as CampusBuilding;
describe("Google floor placement",()=>{
  it("uses east/north metres at the anchor, including the WGS84 ellipsoid instead of Mercator metres",()=>{
    expect(planToModel(building,[0,0])).toEqual([0,0]);
    const east=planToModel(building,[111319.49079327358,0]);
    expect(east[0]).toBeCloseTo(111313.83923667614,5);expect(east[1]).toBeCloseTo(0,8);
    const north=planToModel(building,[0,111325.1428663851]);
    expect(north[0]).toBeCloseTo(0,8);expect(north[1]).toBeCloseTo(110568.77482456664,5);
  });
  it("keeps source elevations, exposes the basement for inspection, and does not multiply floor gaps in focus mode",()=>{
    const basement={id:"B",elevation:-3} as GoogleFloorModel, upper={id:"U",elevation:6} as GoogleFloorModel;
    expect(floorAltitude(basement,0,-3,6,null)).toBe(.3);
    expect(floorAltitude(upper,3,-3,6,null)).toBe(27.3);
    expect(floorAltitude(upper,3,-3,12,"U")).toBe(6.3);
    expect(floorAltitude(basement,0,-3,0,"B")).toBe(.3);
    expect(floorAltitude(basement,0,-3,0,null)).toBe(-2.7);
  });
});

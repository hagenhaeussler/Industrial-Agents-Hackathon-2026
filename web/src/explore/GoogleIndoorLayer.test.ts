import {afterEach,describe,expect,it,vi} from "vitest";
import {compileScene} from "@locora/view";
import {fixture} from "../../../packages/building-view/src/testing/fixture";
import {GoogleIndoorLayer} from "./GoogleIndoorLayer";
import type {CampusBuilding} from "./geography";
import {planToGeographic} from "./geography";
import type {Google3dLibrary,GoogleMapElement} from "./google3d";

class Model extends HTMLElement {position={lat:0,lng:0,altitude:0};constructor(options:Record<string,unknown>){super();Object.assign(this,options);}}
class Flattener extends HTMLElement {path:unknown;constructor(options:Record<string,unknown>){super();this.path=options.path;}}
class Highlight extends HTMLElement {position={lat:0,lng:0,altitude:0};constructor(options:Record<string,unknown>){super();Object.assign(this,options);}}
customElements.define("test-floor-model",Model);customElements.define("test-building-flattener",Flattener);
customElements.define("test-room-highlight",Highlight);
const sdk={FlattenerElement:Flattener,Model3DInteractiveElement:Model,Model3DElement:Highlight} as unknown as Google3dLibrary;
const scene=compileScene(fixture());
const building={id:scene.id,center:[0,0],googleIndoorModel:"/maps/models/test/manifest.json",
  outline:{type:"Polygon",coordinates:[[[0,0],[1,0],[1,1],[0,1],[0,0]]]},
  localFrame:{crs:"EPSG:3857",matrix:[[1,0,0],[0,1,0]]},
} as CampusBuilding;
function setup(fail=false) {
  const map=document.createElement("div") as unknown as GoogleMapElement;document.body.append(map);
  const manifest={buildingId:scene.id,anchor:building.center,rooms:{A:"/maps/models/test/rooms/A.glb"},floors:scene.floors.map((f,i)=>({id:f.id,elevation:f.elevation,level:f.level,height:f.height,src:`/maps/models/test/${i}.glb`}))};
  vi.stubGlobal("fetch",vi.fn(async(url:string|URL)=>{
    if (String(url).endsWith("manifest.json")) return new Response(JSON.stringify(manifest));
    if (fail) return new Response("missing",{status:404});
    const bytes=new ArrayBuffer(20), view=new DataView(bytes);view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,20,true);
    return new Response(bytes);
  }));
  return map;
}
afterEach(()=>{document.body.replaceChildren();vi.unstubAllGlobals();});
describe("Google scene building replacement",()=>{
  it("replaces only the selected footprint, filters and moves floor models in the same map, and restores Google on exit",async()=>{
    const map=setup(), abort=new AbortController();
    const layer=await GoogleIndoorLayer.prepare(map,sdk,building,scene,vi.fn(),abort.signal);
    expect(map.children.length).toBe(0);
    layer.show(6,null);
    expect(map.querySelectorAll("test-building-flattener").length).toBe(1);
    expect(map.querySelectorAll("test-floor-model").length).toBe(scene.floors.length);
    expect((map.firstElementChild as Flattener).path).toEqual(building.outline.coordinates[0]!.map(([lng,lat])=>({lng,lat})));
    const model=map.querySelector("test-floor-model")!;
    layer.show(12,scene.floors[0]!.id);
    expect(map.querySelectorAll("test-floor-model").length).toBe(1);
    expect(map.querySelector("test-floor-model")).toBe(model);
    layer.hide();expect(map.children.length).toBe(0);expect(map.isConnected).toBe(true);
    layer.show(6,null);expect(map.querySelector("test-floor-model")).toBe(model);
    layer.destroy();expect(map.children.length).toBe(0);
  });
  it("keeps Google's building intact if any model is missing",async()=>{
    const map=setup(true);
    await expect(GoogleIndoorLayer.prepare(map,sdk,building,scene,vi.fn(),new AbortController().signal)).rejects.toThrow("unavailable");
    expect(map.children.length).toBe(0);
  });
  it("selects the real room on the clicked floor without reopening the exterior",async()=>{
    const map=setup(), onRoom=vi.fn(), outside=vi.fn();map.addEventListener("gmp-click",outside);
    const layer=await GoogleIndoorLayer.prepare(map,sdk,building,scene,onRoom,new AbortController().signal);
    layer.show(6,"F0","A");
    await vi.waitFor(()=>expect(map.querySelector("test-room-highlight")).not.toBeNull());
    expect(map.querySelector("test-room-highlight")?.getAttribute("data-room-id")).toBe("A");
    const highlight=map.querySelector("test-room-highlight") as Highlight & {altitudeMode:string};
    expect(highlight.altitudeMode).toBe("RELATIVE_TO_GROUND");
    expect(highlight.position).toEqual((map.querySelector("test-floor-model") as Model).position);
    const [lng,lat]=planToGeographic(building.localFrame!,2,1);
    const event=Object.assign(new Event("gmp-click",{bubbles:true}),{position:{lat,lng}});
    map.querySelector("test-floor-model")!.dispatchEvent(event);
    expect(onRoom).toHaveBeenCalledWith({id:"A",name:"Office 0.01",ref:"0.01",floorId:"F0",level:0});
    expect(outside).not.toHaveBeenCalled();
    layer.destroy();
  });
  it("does not attach stale models after cancellation",async()=>{
    const map=setup(), abort=new AbortController();abort.abort();
    await expect(GoogleIndoorLayer.prepare(map,sdk,building,scene,vi.fn(),abort.signal)).rejects.toThrow();
    expect(map.children.length).toBe(0);
  });
});

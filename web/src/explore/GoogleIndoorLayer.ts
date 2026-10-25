import type { BuildingScene } from "@locora/view";
import type { CampusBuilding } from "./geography";
import { planToGeographic } from "./geography";
import { isBuildingClick, type Google3dLibrary, type GoogleMapElement, type GoogleModelElement } from "./google3d";
import { floorAltitude, type GoogleIndoorManifest } from "./model-placement";
import type { RoomPick } from "./map";

/** Own floor meshes and a footprint-scoped flattener, all attached to the existing Google scene. */
export class GoogleIndoorLayer {
  private flattener: HTMLElement;
  private models: {model:GoogleModelElement;removeListener:()=>void}[] = [];
  private highlight?:{roomId:string;model:GoogleModelElement};
  private alive = true;
  private constructor(private map:GoogleMapElement, private sdk:Google3dLibrary, private building:CampusBuilding,
    private manifest:GoogleIndoorManifest, private scene:BuildingScene, onRoom:(room:RoomPick|undefined)=>void) {
    if (!sdk.FlattenerElement || !sdk.Model3DInteractiveElement) throw new Error("This Google SDK does not support building replacement.");
    const [outer,...holes] = (manifest.mask ?? building.outline).coordinates;
    const path = (ring:number[][]) => ring.map(([lng,lat])=>({lat:lat!,lng:lng!}));
    this.flattener = new sdk.FlattenerElement({path:path(outer!),innerPaths:holes.map(path)});
    this.flattener.dataset.buildingId = building.id;
    for (const floor of manifest.floors) {
      const model = new sdk.Model3DInteractiveElement({src:floor.src,
        position:{lat:manifest.anchor[1],lng:manifest.anchor[0],altitude:floor.elevation+.3},
        altitudeMode:"RELATIVE_TO_GROUND",orientation:{heading:0,tilt:0,roll:0},scale:1});
      model.dataset.floorId=floor.id; model.dataset.level=String(floor.level);
      const spaces = scene.floors.find(f=>f.id===floor.id)?.spaces.map(space=>({space,polygon:{type:"Polygon" as const,
        coordinates:[space.outline.map(([x,y])=>planToGeographic(building.localFrame!,x,y))]}})) ?? [];
      const clicked = (event:Event) => {
        event.stopPropagation();
        const position=(event as Event & {position?:{lat:number;lng:number}}).position;
        const found=spaces.find(({polygon})=>isBuildingClick({...building,outline:polygon},position))?.space;
        onRoom(found ? {id:found.id,name:found.name,ref:found.ref,floorId:floor.id,level:floor.level} : undefined);
      };
      model.addEventListener("gmp-click",clicked);
      this.models.push({model,removeListener:()=>model.removeEventListener("gmp-click",clicked)});
    }
  }

  static async prepare(map:GoogleMapElement,sdk:Google3dLibrary,building:CampusBuilding,scene:BuildingScene,
    onRoom:(room:RoomPick|undefined)=>void,signal:AbortSignal) {
    if (!building.googleIndoorModel || !building.localFrame) throw new Error("No calibrated Google floor model is available.");
    const response=await fetch(building.googleIndoorModel,{signal});
    if (!response.ok) throw new Error("The floor model catalogue could not load.");
    const manifest=await response.json() as GoogleIndoorManifest;
    if (manifest.buildingId!==building.id || scene.id!==building.id || manifest.floors.length!==scene.floors.length
      || manifest.anchor.some((n,i)=>Math.abs(n-building.center[i]!)>1e-8)
      || manifest.floors.some(f=>!scene.floors.some(s=>s.id===f.id && s.elevation===f.elevation))) {
      throw new Error("The floor models do not match this building's geographic frame.");
    }
    // Verify every asset before removing Google's shell. Never leave a blank footprint after a 404.
    await Promise.all(manifest.floors.map(async floor=>{
      const url=new URL(floor.src,location.origin);
      if (url.origin!==location.origin || !url.pathname.startsWith("/maps/models/")) throw new Error("Unexpected model source.");
      const asset=await fetch(url,{signal});
      if (!asset.ok) throw new Error("A floor model is unavailable.");
      const bytes=await asset.arrayBuffer();
      if (bytes.byteLength<20 || new DataView(bytes).getUint32(0,true)!==0x46546c67
        || new DataView(bytes).getUint32(4,true)!==2 || new DataView(bytes).getUint32(8,true)!==bytes.byteLength) throw new Error("Invalid floor model.");
    }));
    signal.throwIfAborted();
    return new GoogleIndoorLayer(map,sdk,building,manifest,scene,onRoom);
  }

  show(gap:number,focus:string|null,roomId?:string) {
    if (!this.alive) return;
    if (!this.flattener.isConnected) this.map.append(this.flattener);
    const lowest=Math.min(...this.manifest.floors.map(f=>f.elevation));
    this.models.forEach(({model},rank)=>{
      const floor=this.manifest.floors[rank]!;
      if (focus && focus!==floor.id) {model.remove();return;}
      const altitude=floorAltitude(floor,rank,lowest,gap,focus);
      model.position={lat:this.manifest.anchor[1],lng:this.manifest.anchor[0],altitude};
      model.dataset.altitude=String(altitude);
      if (!model.isConnected) this.map.append(model);
    });
    const sourceFloor=roomId ? this.scene.floors.find(f=>(!focus || f.id===focus) && f.spaces.some(s=>s.id===roomId)) : undefined;
    const room=sourceFloor?.spaces.find(s=>s.id===roomId);
    const src=room ? this.manifest.rooms?.[room.id] : undefined;
    if (room && sourceFloor && src) {
      const rank=this.manifest.floors.findIndex(f=>f.id===sourceFloor.id), floor=this.manifest.floors[rank]!;
      const position={lat:this.manifest.anchor[1],lng:this.manifest.anchor[0],altitude:floorAltitude(floor,rank,lowest,gap,focus)};
      if (this.highlight?.roomId===room.id) {this.highlight.model.position=position;return;}
      this.clearHighlight();
      // Use the exact same GLB transform and anchor as the floor. Terrain-relative polygons
      // drape to a different height at each vertex and therefore cannot mark a flat indoor slab.
      const url=new URL(src,location.origin);
      if (url.origin!==location.origin || !url.pathname.startsWith("/maps/models/")) return;
      const Model=this.sdk.Model3DElement ?? this.sdk.Model3DInteractiveElement!;
      const model=new Model({src:url.href,position,altitudeMode:"RELATIVE_TO_GROUND",orientation:{heading:0,tilt:0,roll:0},scale:1});
      model.dataset.roomId=room.id;this.map.append(model);this.highlight={roomId:room.id,model};
    } else this.clearHighlight();
  }
  private clearHighlight() {if(this.highlight){this.highlight.model.remove();this.highlight=undefined;}}
  hide() {this.flattener.remove();this.clearHighlight();for (const {model} of this.models) model.remove();}
  destroy() {this.alive=false;this.hide();for (const entry of this.models) entry.removeListener();}
}

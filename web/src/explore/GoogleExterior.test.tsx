import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { GoogleExterior } from "./GoogleExterior";
import { currentGoogle3d, loadGoogle3d, type Google3dLibrary } from "./google3d";
import type { CampusBuilding } from "./geography";
import {GoogleIndoorLayer} from "./GoogleIndoorLayer";
import {compileScene} from "@building/view";
import {fixture} from "../../../packages/building-view/src/testing/fixture";

vi.mock("./GoogleIndoorLayer",()=>({GoogleIndoorLayer:{prepare:vi.fn()}}));

vi.mock("./google3d", async (original) => ({ ...await original<typeof import("./google3d")>(),
  currentGoogle3d: vi.fn(), loadGoogle3d: vi.fn(),
}));

class MapStub extends HTMLElement {
  heading = 27; tilt = 61;
  mode="HYBRID";
  stopCameraAnimation=vi.fn();
  flyCameraTo = vi.fn();
}
customElements.define("test-google-map", MapStub);
const sdk = { Map3DElement: MapStub } as unknown as Google3dLibrary;
const building = { id: "test-building", label: "Test building", localFrame: {}, center: [11,48], bounds: [10,47,12,49],
  outline: {type:"Polygon",coordinates:[[[10,47],[12,47],[12,49],[10,49],[10,47]]]},
} as CampusBuilding;
beforeEach(() => {
  vi.mocked(currentGoogle3d).mockReturnValue(sdk);
  vi.mocked(loadGoogle3d).mockReset();
  vi.stubGlobal("matchMedia", () => ({ matches: true }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("Google exterior", () => {
  it("opens the matching floor plan with the current viewing direction, then preserves the exterior on return", () => {
    const onEnter = vi.fn(), onCancel = vi.fn();
    const props = {building,onEnter,onCancel,replay:0,topDown:0,gap:6,floor:null,onRoom:vi.fn()};
    const view = render(<GoogleExterior {...props} inside={false} />);
    const map = document.querySelector("test-google-map")! as MapStub;
    const event = new Event("gmp-click");
    Object.assign(event,{position:{lat:48,lng:11}});
    map.dispatchEvent(event);
    expect(onEnter).toHaveBeenCalledWith({heading:27,tilt:61});
    view.rerender(<GoogleExterior {...props} inside />);
    expect(map.parentElement!.parentElement!.hidden).toBe(false);
    view.rerender(<GoogleExterior {...props} inside={false} />);
    expect(document.querySelector("test-google-map")).toBe(map);
    expect(loadGoogle3d).not.toHaveBeenCalled();
  });
  it("ignores neighbours and keeps click handling attached to the newly selected building", () => {
    const onEnter = vi.fn(), props = {building,onEnter,onCancel:vi.fn(),replay:0,topDown:0,inside:false,gap:6,floor:null,onRoom:vi.fn()};
    const view = render(<GoogleExterior {...props} />);
    const map = document.querySelector("test-google-map")!;
    const event = new Event("gmp-click"); Object.assign(event,{position:{lat:48,lng:11}});
    view.rerender(<GoogleExterior {...props} building={{...building,id:"other",outline:{type:"Polygon",coordinates:[[[1,1],[2,1],[2,2],[1,2],[1,1]]]}}} />);
    map.dispatchEvent(event); expect(onEnter).not.toHaveBeenCalled();
  });
  it("asks for a runtime key without loading Google, rejects invalid input and clears the key before connecting", async () => {
    vi.mocked(currentGoogle3d).mockReturnValue(undefined);
    vi.mocked(loadGoogle3d).mockResolvedValue(sdk);
    render(<GoogleExterior building={building} inside={false} gap={6} floor={null} onRoom={vi.fn()} onEnter={vi.fn()} onCancel={vi.fn()} replay={0} topDown={0} />);
    expect(loadGoogle3d).not.toHaveBeenCalled();
    const input = screen.getByLabelText("Google Maps key") as HTMLInputElement;
    fireEvent.change(input,{target:{value:"not-a-key"}});
    fireEvent.click(screen.getByText("Open Google 3D"));
    expect(loadGoogle3d).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toContain("valid Google Maps");
    fireEvent.change(input,{target:{value:"AIza" + "x".repeat(35)}});
    fireEvent.click(screen.getByText("Open Google 3D"));
    expect(input.value).toBe("");
    await waitFor(() => expect(document.querySelector("test-google-map")).not.toBeNull());
  });
  it("offers the campus fallback when Google fails", async () => {
    const cancel = vi.fn();
    render(<GoogleExterior building={building} inside={false} gap={6} floor={null} onRoom={vi.fn()} onEnter={vi.fn()} onCancel={cancel} replay={0} topDown={0} />);
    fireEvent(document.querySelector("test-google-map")!,new Event("gmp-error"));
    expect(screen.getByRole("alert").textContent).toContain("Google 3D is unavailable");
    fireEvent.click(screen.getByText("Use Campus")); expect(cancel).toHaveBeenCalledOnce();
  });
  it("hides Google labels, focuses floors and rooms, then restores the exterior on the same map",async()=>{
    const layer={show:vi.fn(),hide:vi.fn(),destroy:vi.fn()};
    vi.mocked(GoogleIndoorLayer.prepare).mockResolvedValue(layer as unknown as GoogleIndoorLayer);
    const scene=compileScene(fixture()), props={building:{...building,id:scene.id,
      googleIndoorModel:"/maps/models/fixture/manifest.json",localFrame:{crs:"EPSG:3857" as const,matchedSpaces:12,medianResidualM:0,p95ResidualM:0,matrix:[[1,0,0],[0,1,0]] as [[number,number,number],[number,number,number]]}},
      scene,gap:8,floor:null,onRoom:vi.fn(),onEnter:vi.fn(),onCancel:vi.fn(),replay:0,topDown:0};
    const view=render(<GoogleExterior {...props} inside={false}/>);
    const map=document.querySelector("test-google-map")! as MapStub;
    await waitFor(()=>expect(GoogleIndoorLayer.prepare).toHaveBeenCalled());
    view.rerender(<GoogleExterior {...props} inside/>);
    await waitFor(()=>expect(map.flyCameraTo.mock.lastCall?.[0].endCamera.tilt).toBe(60));
    expect(map.mode).toBe("SATELLITE");
    expect(layer.show).toHaveBeenLastCalledWith(8,null,undefined);
    view.rerender(<GoogleExterior {...props} inside floor="F0"/>);
    expect(map.flyCameraTo.mock.lastCall?.[0].endCamera.tilt).toBe(16);
    const floorRange=map.flyCameraTo.mock.lastCall![0].endCamera.range;
    view.rerender(<GoogleExterior {...props} inside floor="F0" room={{id:"A",name:"Office 0.01",ref:"0.01",floorId:"F0",level:0}}/>);
    expect(map.flyCameraTo.mock.lastCall![0].endCamera.range).toBeLessThan(floorRange);
    expect(map.flyCameraTo.mock.lastCall![0].durationMillis).toBe(0);
    view.rerender(<GoogleExterior {...props} inside={false}/>);
    expect(map.mode).toBe("HYBRID");
    expect(layer.hide).toHaveBeenCalled();
    expect(document.querySelector("test-google-map")).toBe(map);
  });
});

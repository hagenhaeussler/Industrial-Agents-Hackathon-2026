import {afterEach,expect,it,vi} from "vitest";
import {cleanup,fireEvent,render,screen,waitFor,within} from "@testing-library/react";
import {QueryClient,QueryClientProvider} from "@tanstack/react-query";
import {fixture} from "../../../packages/building-view/src/testing/fixture";
import {CampusExplorer} from "./CampusExplorer";

vi.mock("./map",()=>({CampusMap:class {
  constructor(_host:unknown,_catalog:unknown,callbacks:{onReady:()=>void;onStage:(s:string)=>void}) {
    queueMicrotask(()=>{callbacks.onStage("campus");callbacks.onReady();});
  }
  setSelected=vi.fn();destroy=vi.fn();showExterior=vi.fn();showIndoor=vi.fn();flyTo=vi.fn();
}}));
vi.mock("./GoogleExterior",()=>({GoogleExterior:({room}:{room?:{id:string}})=><div aria-label="Google scene">{room ? `Focused room ${room.id}` : "Exterior or floors"}</div>}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();});

it("searches real source rooms, selects their floor, clears a floor search, and returns to the building list",async()=>{
  history.replaceState(null,"","/?building=fixture&map=photo");
  const source=fixture(),building={id:"fixture",name:"Fixture",label:"Fixture",city:"Test campus",center:[0,0],bounds:[0,0,.001,.001],
    outline:{type:"Polygon",coordinates:[[[0,0],[.001,0],[.001,.001],[0,.001],[0,0]]]},floors:2,rooms:1,
    localFrame:{crs:"EPSG:3857",matrix:[[1,0,0],[0,1,0]]},googleIndoorModel:"/maps/models/fixture/manifest.json"};
  vi.stubGlobal("fetch",vi.fn(async(url:string)=>new Response(JSON.stringify(url==="/maps/buildings.json"
    ? {featuredBuildingId:"fixture",buildings:[building]} : source))));
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={client}><CampusExplorer/></QueryClientProvider>);
  const enter=await screen.findByRole("button",{name:"Go inside"});
  await waitFor(()=>expect(enter.hasAttribute("disabled")).toBe(false));
  fireEvent.click(enter);
  const search=await screen.findByRole("textbox",{name:"Search rooms"});
  fireEvent.change(search,{target:{value:"0.01"}});
  const rooms=screen.getByLabelText("Rooms");
  const pick=await within(rooms).findByRole("button",{name:/Office 0.01/});
  fireEvent.click(pick);
  expect(screen.getByRole("button",{name:"Show Ground"}).getAttribute("aria-pressed")).toBe("true");
  expect(await screen.findByText("Focused room A")).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Show Level 1"}));
  expect((search as HTMLInputElement).value).toBe("");
  expect(screen.getByText("No rooms match this selection.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Back to 3D"}));
  expect(screen.getByRole("textbox",{name:"Search buildings or places"})).toBeTruthy();
  expect(screen.queryByLabelText("Rooms")).toBeNull();
});

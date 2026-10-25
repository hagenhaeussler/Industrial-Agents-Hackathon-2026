import { compileScene } from "@locora/view";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { fixture } from "../../../packages/building-view/src/testing/fixture";
import type { RouteRequest } from "../api/buildings";
import { Workspace } from "../admin/Workspace";
import { PhoneGuide } from "../phone/PhoneGuide";
import type { VoiceContext } from "./context";
import type { BuildingVoice } from "./useBuildingVoice";

const state = vi.hoisted(() => ({ voice: vi.fn(), building: vi.fn(), route: vi.fn(), navigate: vi.fn() }));
vi.mock("../api/buildings", () => ({ useBuilding: state.building, useRoute: state.route, useBuildings: () => ({ data: [] }) }));
vi.mock("./useBuildingVoice", () => ({ useBuildingVoice: state.voice }));
vi.mock("../router", () => ({ navigate: state.navigate }));
vi.mock("../views/BuildingView3DView", () => ({ BuildingView3DView: () => null }));
vi.mock("../views/FloorPlanView", () => ({ FloorPlanView: () => null }));
vi.mock("../avatar/Avatar", () => ({ Avatar: () => null }));
let context: VoiceContext;
let plan: (request: RouteRequest) => void;
beforeEach(() => {
  const document = fixture();
  state.building.mockReturnValue({ data: { document, scene: compileScene(document) } });
  state.route.mockReset().mockReturnValue({ data: undefined, isFetching: false });
  state.voice.mockImplementation((next: VoiceContext, onRoute: typeof plan): BuildingVoice => {
    context = next;
    plan = onRoute;
    return {
      phase: "off", entries: [], error: undefined, isMuted: false, hasLog: false,
      start: async () => {}, stop: vi.fn(), send: vi.fn(), toggleMute: vi.fn(), muteForTyping: vi.fn(),
      downloadLog: vi.fn(), level: () => 0,
    };
  });
});
afterEach(cleanup);

it("shows a voice route on desktop without claiming its start as the user's position", () => {
  render(<Workspace buildingId="fixture" query={new URLSearchParams()} />);
  const planned = { stops: ["A", "B", "C"], closed: ["O2"], stepFree: true };
  act(() => plan(planned));
  expect(context.position).toBeUndefined();
  expect(context.destination?.id).toBe("C");
  expect(state.route).toHaveBeenLastCalledWith("fixture", planned);
  fireEvent.click(screen.getByRole("tab", { name: "Route" }));
  fireEvent.click(screen.getByRole("button", { name: "Clear destination" }));
  expect(context.destination).toBeUndefined();
});

it("keeps the confirmed phone position when a voice route changes its start", () => {
  const { rerender } = render(<PhoneGuide buildingId="fixture" query={new URLSearchParams("from=A&to=B")} />);
  act(() => plan({ stops: ["C", "B"] }));
  rerender(<PhoneGuide buildingId="fixture" query={new URLSearchParams("from=C&to=B")} />);
  expect(context.position?.id).toBe("A");
  expect(context.destination?.id).toBe("B");
});

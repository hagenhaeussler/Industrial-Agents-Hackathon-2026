// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";

import type { CoworkerMarker, Overlay, PickResult } from "../overlay";
import { compileScene } from "../scene/compile";
import { fixture } from "../testing/fixture";
import { FloorPlan } from "./FloorPlan";

const scene = compileScene(fixture());
const coworker: CoworkerMarker = { id: "person", name: "Test Person", color: "#397a91", floorId: "F0", x: 2, y: 1 };
const plans: FloorPlan[] = [];

function mount(): FloorPlan {
  const container = document.createElement("div");
  document.body.append(container);
  const plan = new FloorPlan(container);
  plan.show(scene, "F0");
  plans.push(plan);
  return plan;
}

function marker(plan: FloorPlan): SVGGElement {
  const node = plan.svg.querySelector<SVGGElement>('[data-kind="coworker"]');
  if (!node) throw new Error("Expected a coworker marker");
  return node;
}

afterEach(() => {
  for (const plan of plans.splice(0)) plan.destroy();
  document.body.replaceChildren();
});

describe("floor plan coworkers", () => {
  it("draws a named bot at the supplied plan coordinates", () => {
    const plan = mount();
    plan.setOverlay({ coworkers: [coworker] });
    const node = marker(plan);
    expect({
      transform: node.getAttribute("transform"),
      color: node.style.color,
      name: node.querySelector("text")?.textContent,
      accessibleName: node.getAttribute("aria-label"),
      role: node.getAttribute("role"),
      tabIndex: node.getAttribute("tabindex"),
    }).toEqual({
      transform: "translate(2 -1)", color: "#397a91", name: coworker.name,
      accessibleName: "Chat with Test Person, AI coworker", role: "button", tabIndex: "0",
    });
  });

  it("selects the coworker from a child shape without selecting the room behind it", () => {
    const plan = mount();
    const picks: (PickResult | null)[] = [];
    plan.onPick((pick) => picks.push(pick));
    plan.setOverlay({ coworkers: [coworker] });
    marker(plan).querySelector("path")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(picks).toEqual([{ kind: "coworker", ...coworker }]);
  });

  it.each(["Enter", " "])("selects with the %s key and returns the current position", (key) => {
    const plan = mount();
    const picks: (PickResult | null)[] = [];
    plan.onPick((pick) => picks.push(pick));
    plan.setOverlay({ coworkers: [coworker] });
    const node = marker(plan);
    const moved = { ...coworker, x: 3 };
    plan.setOverlay({ coworkers: [moved] });
    node.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    expect(picks).toEqual([{ kind: "coworker", ...moved }]);
  });

  it("keeps the person, route and building nodes during coworker movement", () => {
    const plan = mount();
    const overlay: Overlay = {
      route: [{ floorId: "F0", x: 0, y: 0 }, { floorId: "F0", x: 4, y: 1 }],
      position: { floorId: "F0", x: 0, y: 1, headingDeg: 30 },
      coworkers: [coworker],
    };
    plan.setOverlay(overlay);
    const before = [marker(plan), plan.svg.querySelector("polyline"), plan.svg.querySelector('[data-id="A"]')];
    plan.setOverlay({ ...overlay, route: overlay.route?.map((point) => ({ ...point })), coworkers: [{ ...coworker, x: 3 }] });
    const after = [marker(plan), plan.svg.querySelector("polyline"), plan.svg.querySelector('[data-id="A"]')];
    expect(after.every((node, index) => node === before[index])).toBe(true);
  });

  it("redraws the route when its points change in place", () => {
    const plan = mount();
    const route = [{ floorId: "F0", x: 0, y: 0 }, { floorId: "F0", x: 4, y: 1 }];
    plan.setOverlay({ route, coworkers: [coworker] });
    route[1]!.x = 6;
    plan.setOverlay({ route, coworkers: [coworker] });
    expect(plan.svg.querySelector("polyline")?.getAttribute("points")).toBe("0,0 6,-1");
  });

  it("shows only coworkers on the selected floor, and removes them when hidden", () => {
    const plan = mount();
    plan.setOverlay({ coworkers: [coworker, { ...coworker, id: "upstairs", floorId: "F1" }] });
    const visibleIds = () => [...plan.svg.querySelectorAll('[data-kind="coworker"]')].map((node) => node.getAttribute("data-id"));
    expect(visibleIds()).toEqual(["person"]);
    plan.show(scene, "F1");
    expect(visibleIds()).toEqual(["upstairs"]);
    plan.setOverlay({ coworkers: [] });
    expect(visibleIds()).toEqual([]);
  });

  it("removes a marker when its journey reaches a different floor", () => {
    const plan = mount();
    plan.setOverlay({ coworkers: [coworker] });
    const node = marker(plan);
    plan.setOverlay({ coworkers: [{ ...coworker, floorId: "F1" }] });
    expect(node.isConnected).toBe(false);
  });

  it("clears old coworkers when switching buildings", () => {
    const plan = mount();
    plan.setOverlay({ coworkers: [coworker] });
    plan.show({ ...scene, id: "another-building" }, "F0");
    expect(plan.svg.querySelector('[data-kind="coworker"]')).toBeNull();
  });

  it("removes event handlers and markers when destroyed", () => {
    const plan = mount();
    const picks: (PickResult | null)[] = [];
    plan.onPick((pick) => picks.push(pick));
    plan.setOverlay({ coworkers: [coworker] });
    const node = marker(plan);
    plan.destroy();
    node.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect({ connected: plan.svg.isConnected, markers: plan.svg.querySelectorAll('[data-kind="coworker"]').length, picks })
      .toEqual({ connected: false, markers: 0, picks: [] });
  });
});

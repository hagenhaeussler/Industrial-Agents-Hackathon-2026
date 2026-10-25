// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";

import type { PickResult } from "../overlay";
import { compileScene } from "../scene/compile";
import { fixture } from "../testing/fixture";
import { FloorPlan, resizeView } from "./FloorPlan";

const scene = compileScene(fixture());

function mount(): FloorPlan {
  const container = document.createElement("div");
  document.body.append(container);
  return new FloorPlan(container);
}

const ids = (plan: FloorPlan, kind: string) =>
  [...plan.svg.querySelectorAll(`[data-kind="${kind}"]`)].map((node) => node.getAttribute("data-id"));

afterEach(() => document.body.replaceChildren());

describe("FloorPlan", () => {
  it("draws only the chosen floor", () => {
    const plan = mount();
    plan.show(scene, "F0");
    expect(ids(plan, "space")).toEqual(["A", "B"]);
    expect(ids(plan, "asset")).toEqual(["D1"]);
    plan.show(scene, "F1");
    expect(ids(plan, "space")).toEqual(["C"]);
    expect(ids(plan, "asset")).toEqual([]);
  });

  it("leaves the building layer untouched when the overlay changes", () => {
    const plan = mount();
    plan.show(scene, "F0");
    const room = plan.svg.querySelector('[data-id="A"]');
    plan.setOverlay({ position: { floorId: "F0", x: 1, y: 1 } });
    plan.setOverlay({ position: { floorId: "F0", x: 2, y: 1 } });
    expect(plan.svg.querySelector('[data-id="A"]')).toBe(room);
  });

  it("draws the route part on this floor and marks where it changes floor", () => {
    const plan = mount();
    plan.show(scene, "F0");
    plan.setOverlay({
      route: [
        { floorId: "F0", x: 1, y: 1 },
        { floorId: "F0", x: 6, y: 1.5 },
        { floorId: "F1", x: 4.5, y: 2 },
      ],
    });
    expect(plan.svg.querySelector("polyline")?.getAttribute("points")).toBe("1,-1 6,-1.5");
    const markers = [...plan.svg.querySelectorAll("circle")].map((c) => [c.getAttribute("cx"), c.getAttribute("cy")]);
    expect(markers).toContainEqual(["6", "-1.5"]);
  });

  it("reports the clicked entity, or null for empty plan", () => {
    const plan = mount();
    plan.show(scene, "F0");
    const picks: (PickResult | null)[] = [];
    plan.onPick((pick) => picks.push(pick));
    plan.svg.querySelector('[data-id="D1"]')!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    plan.svg.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(picks.map((pick) => pick && [pick.kind, pick.id, pick.floorId])).toEqual([["asset", "D1", "F0"], null]);
  });

  it("ignores the click after a drag but not after a cancelled drag", () => {
    const plan = mount();
    plan.show(scene, "F0");
    const picks: (PickResult | null)[] = [];
    plan.onPick((pick) => picks.push(pick));
    const desk = plan.svg.querySelector('[data-id="D1"]')!;
    const pointer = (type: string, clientX: number) =>
      plan.svg.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX, clientY: 0, buttons: 1 }));
    const click = () => desk.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    pointer("pointerdown", 0);
    pointer("pointermove", 30);
    pointer("pointerup", 30);
    click(); // ends a drag: no pick
    pointer("pointerdown", 0);
    pointer("pointermove", 30);
    pointer("pointercancel", 30);
    click(); // after a cancelled drag: a normal pick
    expect(picks.map((pick) => pick?.id)).toEqual(["D1"]);
  });

  it("can hide detail for an overview such as a minimap", () => {
    const plan = mount();
    plan.show(scene, "F0");
    plan.setOptions({ labels: false, assets: false, openings: false });
    expect(ids(plan, "asset")).toEqual([]);
    expect(ids(plan, "opening")).toEqual([]);
    expect(plan.svg.querySelectorAll("text")).toHaveLength(0);
  });
});

describe("resizeView", () => {
  it("keeps scale and centre, so resizing back and forth does not zoom", () => {
    const view = { x: 0, y: 0, width: 10, height: 10 };
    const wide = resizeView(view, { width: 100, height: 100 }, { width: 200, height: 100 });
    expect(wide).toEqual({ x: -5, y: 0, width: 20, height: 10 });
    expect(resizeView(wide, { width: 200, height: 100 }, { width: 100, height: 100 })).toEqual(view);
  });
});

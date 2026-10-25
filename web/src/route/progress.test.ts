import type { Route, RouteLeg } from "@building/view";
import { describe, expect, it } from "vitest";
import { stopsAhead } from "./progress";

const ref = (id: string) => ({ id, name: id, floor_name: "Ground" });
const leg = (...spaces: string[]): RouteLeg => ({
  start: ref(spaces[0]!),
  end: ref(spaces.at(-1)!),
  reachable: true,
  length_m: 10,
  spaces: spaces.map(ref),
  elements: [],
  blocked_by: [],
});
// From A through corridor C to waypoint W, then through corridor E to destination D.
const route: Route = { reachable: true, length_m: 20, legs: [leg("A", "C", "W"), leg("W", "E", "D")] };
const to = ["W", "D"];

describe("stopsAhead", () => {
  it("drops the stops the walker has passed", () => {
    expect(stopsAhead(route, "C", to)).toEqual(["W", "D"]);
    expect(stopsAhead(route, "W", to)).toEqual(["D"]);
    expect(stopsAhead(route, "E", to)).toEqual(["D"]);
  });

  it("has nothing ahead at the destination", () => {
    expect(stopsAhead(route, "D", to)).toEqual([]);
  });

  it("keeps every stop off the route or before the route loads", () => {
    expect(stopsAhead(route, "X", to)).toEqual(to);
    expect(stopsAhead(undefined, "C", to)).toEqual(to);
  });
});

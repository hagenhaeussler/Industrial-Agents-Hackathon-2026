import { describe, expect, it } from "vitest";
import { routeFromToolCall } from "./toolCalls";
import { withoutAudioTags } from "./transcript";

describe("routeFromToolCall", () => {
  it("reads stops and flat rules from a route call", () => {
    expect(routeFromToolCall("route", { stops: ["A", "B"], step_free: true, closed: ["D1"] })).toEqual({
      stops: ["A", "B"],
      stepFree: true,
      closed: ["D1"],
      minDoorWidthM: undefined,
    });
  });

  it("ignores other tools and malformed stops", () => {
    expect(routeFromToolCall("find_spaces", { stops: ["A", "B"] })).toBeUndefined();
    expect(routeFromToolCall("route", { stops: ["A"] })).toBeUndefined();
    expect(routeFromToolCall("route", { stops: "A,B" })).toBeUndefined();
  });
});

describe("withoutAudioTags", () => {
  it("removes speech tags but keeps bracketed refs", () => {
    expect(withoutAudioTags("[happy] Go to Room [A].")).toBe("Go to Room [A].");
  });
});

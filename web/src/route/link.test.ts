import { describe, expect, it } from "vitest";
import { guideLink, readGuideLink } from "./link";

describe("guide link", () => {
  it("round-trips start, stops and the step-free rule", () => {
    const link = guideLink("https://example.org", "fab 1", { stops: ["A", "B", "C"], stepFree: true });
    const url = new URL(link);
    expect(url.pathname).toBe("/b/fab%201");
    expect(readGuideLink(url.searchParams)).toEqual({ from: "A", to: ["B", "C"], stepFree: true });
  });

  it("allows a link without a start", () => {
    expect(readGuideLink(new URLSearchParams("to=B"))).toEqual({ from: undefined, to: ["B"], stepFree: false });
  });
});

describe("guidePath", () => {
  it("leaves out an unknown start", async () => {
    const { guidePath } = await import("./link");
    expect(guidePath("b1", { stops: ["", "B"] })).toBe("/b/b1?to=B");
  });
});

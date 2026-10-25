import { expect, it } from "vitest";
import { parsePage } from "./router";

it.each([
  ["/", { name: "home" }],
  ["/buildings", { name: "library" }],
  ["/explore", { name: "explore" }],
  ["/explore/", { name: "explore" }],
  ["/admin/fixture%2Fbuilding", { name: "admin", buildingId: "fixture/building" }],
  ["/b/fixture%20building", { name: "guide", buildingId: "fixture building" }],
  ["/explore/extra", { name: "missing" }],
  ["/buildings/extra", { name: "missing" }],
  ["/admin", { name: "missing" }],
  ["/b/fixture/extra", { name: "missing" }],
  ["/unknown", { name: "missing" }],
])("resolves %s without changing existing building routes", (path, expected) => {
  expect(parsePage(path as string)).toEqual(expected);
});

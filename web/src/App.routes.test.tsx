import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { App } from "./App";
import { navigate } from "./router";

vi.mock("./api/buildings", () => ({
  useBuildings: () => ({ data: [], isPending: false, isError: false }),
}));
vi.mock("./avatar/Avatar", () => ({ Avatar: () => <span aria-label="Locora assistant" /> }));
vi.mock("./explore/CampusExplorer", () => ({
  CampusExplorer: () => <label>Globe explorer<input aria-label="Runtime session" defaultValue="" /></label>,
}));
vi.mock("./phone/PhoneGuide", () => ({
  PhoneGuide: ({ buildingId, query }: { buildingId: string; query: URLSearchParams }) => (
    <p>Phone {buildingId}: {query.get("to")}</p>
  ),
}));
vi.mock("./admin/Workspace", () => ({
  Workspace: ({ buildingId }: { buildingId: string }) => <p>Workspace {buildingId}</p>,
}));

afterEach(() => { cleanup(); history.replaceState(null, "", "/"); });

it("preserves the Locora home and opens the globe from its existing-style action", async () => {
  history.replaceState(null, "", "/");
  render(<App />);
  expect(screen.getByRole("heading", { name: "Locora" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Explore on globe" }));
  expect(location.pathname).toBe("/explore");
  expect(await screen.findByLabelText("Runtime session")).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Locora" })).toBeNull();
});

it("keeps the building-list alias available", () => {
  history.replaceState(null, "", "/buildings");
  render(<App />);
  expect(screen.getByRole("heading", { name: "Locora" })).toBeTruthy();
});

it("keeps a legacy root preview mounted when navigating to its canonical explorer URL", async () => {
  history.replaceState(null, "", "/?building=fixture%2Fbuilding&map=photo");
  render(<App />);
  const session = await screen.findByLabelText("Runtime session") as HTMLInputElement;
  fireEvent.change(session, { target: { value: "in-memory session" } });
  act(() => navigate("/explore?building=fixture%2Fbuilding&map=photo"));
  expect(screen.getByLabelText("Runtime session")).toBe(session);
  expect(session.value).toBe("in-memory session");
});

it("preserves encoded workspace and phone routes with their guide query", async () => {
  history.replaceState(null, "", "/admin/fixture%2Fbuilding");
  render(<App />);
  expect(await screen.findByText("Workspace fixture/building")).toBeTruthy();
  act(() => navigate("/b/fixture%2Fbuilding?to=room%20one"));
  expect(await screen.findByText("Phone fixture/building: room one")).toBeTruthy();
});

it("retains the missing-page state for unsupported routes", () => {
  history.replaceState(null, "", "/explore/extra");
  render(<App />);
  expect(screen.getByText("This page does not exist.")).toBeTruthy();
});

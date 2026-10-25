import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { DemoBuilding } from "./DemoBuilding";

afterEach(cleanup);

it("waits for a real JSON instead of inventing a building or guide", () => {
  render(<QueryClientProvider client={new QueryClient()}><DemoBuilding buildings={[]} /></QueryClientProvider>);
  expect(screen.getByText("Awaiting building.json")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Add Demo JSON" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Open Demo guide" })).toBeNull();
});

it("opens the real imported building ID without claiming localization is ready", () => {
  render(<DemoBuilding buildings={[{ id: "actual office?#", name: "Demo", source: "scan", floors: 1 }]} />);
  expect(screen.getByText("Plan ready")).toBeTruthy();
  expect(screen.getByText(/needs the matching localization scan/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Open Demo guide" }));
  expect(location.pathname).toBe("/b/actual%20office%3F%23");
});

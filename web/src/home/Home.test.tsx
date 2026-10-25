import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Home } from "./Home";

beforeEach(() => history.replaceState(null, "", "/"));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function renderHome() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><Home /></QueryClientProvider>);
}

it("imports from the collection home page while retaining the existing building cards", async () => {
  const original = { id: "campus", name: "Existing campus", source: "procedural", floors: 4 };
  const imported = { id: "uploaded", name: "Uploaded building", source: "custom", floors: 2 };
  let saved = false;
  const fetch = vi.fn(async (url: string, options?: RequestInit) => {
    if (url === "/api/buildings/import" && options?.method === "POST") {
      saved = true;
      return Response.json({ id: imported.id, status: "imported" }, { status: 201 });
    }
    return Response.json(saved ? [original, imported] : [original]);
  });
  vi.stubGlobal("fetch", fetch);
  renderHome();
  await screen.findByText("Existing campus");
  expect(screen.getByRole("navigation", { name: "Collections" })).toBeTruthy();
  expect(screen.getAllByRole("textbox", { name: "Search buildings" })).toHaveLength(1);
  expect(screen.getByRole("button", { name: "Import building" })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Building JSON file"), {
    target: { files: [new File(["{}"], "building.json")] },
  });
  await waitFor(() => expect(location.pathname).toBe("/admin/uploaded"));
  expect(saved).toBe(true);
  expect(screen.getByText("Existing campus")).toBeTruthy();
});

it("keeps import available when the building catalog is empty", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([])));
  renderHome();
  await screen.findByText("No buildings yet. Import a building.json to open it here.");
  expect(screen.getByRole("button", { name: "Import building" })).toBeTruthy();
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ImportBuilding } from "./ImportBuilding";

beforeEach(() => history.replaceState(null, "", "/"));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderImport() {
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  queries.setQueryData(["buildings"], []);
  const view = render(<QueryClientProvider client={queries}><ImportBuilding /></QueryClientProvider>);
  return { ...view, queries };
}

function chooseFile(file = new File(["{}"], "building.json")) {
  fireEvent.change(screen.getByLabelText("Building JSON file"), { target: { files: [file] } });
}

function pendingResponse() {
  let resolve: (response: Response) => void = () => { throw new Error("Promise has not started"); };
  const promise = new Promise<Response>((settle) => { resolve = settle; });
  return { promise, resolve };
}

it.each(["imported", "unchanged"])("opens the saved building and refreshes the list after %s", async (status) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ id: "new building?#", status })));
  const { queries } = renderImport();
  chooseFile();
  await waitFor(() => expect(location.pathname).toBe("/admin/new%20building%3F%23"));
  expect(queries.getQueryState(["buildings"])?.isInvalidated).toBe(true);
});

it("keeps the user on the page and shows a validation error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ detail: "Unknown floor F9" }, { status: 422 })));
  renderImport();
  chooseFile();
  expect((await screen.findByRole("alert")).textContent).toBe("Unknown floor F9");
  expect(location.pathname).toBe("/");
});

it("shows a local file error without making a request", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  renderImport();
  chooseFile(new File([], "building.json"));
  expect((await screen.findByRole("alert")).textContent).toContain("empty");
  expect(fetch).not.toHaveBeenCalled();
});

it("allows the same file to be retried after a failed save", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(Response.json({ detail: "The building could not be saved. Try again." }, { status: 503 }))
    .mockResolvedValueOnce(Response.json({ id: "retried", status: "imported" }, { status: 201 }));
  vi.stubGlobal("fetch", fetch);
  renderImport();
  const file = new File(["{}"], "building.json");
  chooseFile(file);
  await screen.findByRole("alert");
  chooseFile(file);
  await waitFor(() => expect(location.pathname).toBe("/admin/retried"));
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("disables import and ignores repeated file events while the save is pending", async () => {
  const pending = pendingResponse();
  const fetch = vi.fn().mockReturnValue(pending.promise);
  vi.stubGlobal("fetch", fetch);
  renderImport();
  act(() => { chooseFile(); chooseFile(); });
  await screen.findByRole("status");
  expect(screen.getByRole<HTMLButtonElement>("button", { name: "Importing…" }).disabled).toBe(true);
  expect(location.pathname).toBe("/");
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => pending.resolve(Response.json({ id: "once", status: "imported" })));
  await waitFor(() => expect(location.pathname).toBe("/admin/once"));
});

it("does not navigate after the user leaves during an upload", async () => {
  const pending = pendingResponse();
  vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending.promise));
  const { unmount, queries } = renderImport();
  chooseFile();
  await screen.findByRole("status");
  unmount();
  history.pushState(null, "", "/admin/another-building");
  await act(async () => pending.resolve(Response.json({ id: "late", status: "imported" })));
  await waitFor(() => expect(queries.getMutationCache().getAll()[0]?.state.status).toBe("success"));
  expect(location.pathname).toBe("/admin/another-building");
});

it("does nothing when the file picker is cancelled", () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  renderImport();
  fireEvent.change(screen.getByLabelText("Building JSON file"), { target: { files: [] } });
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.queryByRole("alert")).toBeNull();
});

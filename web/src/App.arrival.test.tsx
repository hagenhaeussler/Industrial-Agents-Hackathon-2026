import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode, useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { arrivalBuildings } from "./arrival/catalogue";
import { navigate } from "./router";

const mocks = vi.hoisted(() => ({ start: vi.fn(), mounted: vi.fn(), unmounted: vi.fn() }));
const mapped = arrivalBuildings[0]!;
vi.mock("./arrival/map", () => ({ startArrival: mocks.start }));
vi.mock("./avatar/Avatar", () => ({ Avatar: () => null }));
vi.mock("./api/buildings", () => ({ useBuildings: () => ({ data: [
  { id: mapped.id, name: mapped.label, floors: 2 }, { id: "local-building", name: "Local building", floors: 1 },
] }) }));
vi.mock("./admin/Workspace", () => ({ Workspace: ({ buildingId }: { buildingId: string }) => {
  const [clicks, setClicks] = useState(0);
  useEffect(() => { mocks.mounted(); return mocks.unmounted; }, []);
  return <main aria-label="Existing workspace"><span>{buildingId}</span>
    <button onClick={() => setClicks((value) => value + 1)}>Selected room {clicks}</button></main>;
} }));
vi.mock("./phone/PhoneGuide", () => ({ PhoneGuide: () => <main>Phone guide</main> }));

let motion: MediaQueryList;
beforeEach(() => {
  vi.clearAllMocks();
  motion = Object.assign(new EventTarget(), { matches: false }) as MediaQueryList;
  vi.stubGlobal("matchMedia", () => motion);
  history.replaceState(null, "", "/");
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

function renderApp(strict = false) {
  const app = <QueryClientProvider client={new QueryClient()}><App /></QueryClientProvider>;
  return render(strict ? <StrictMode>{app}</StrictMode> : app);
}

async function openWorkspace(id = mapped.id) {
  renderApp();
  const row = screen.getByText(id === mapped.id ? mapped.label : "Local building").closest("li")!;
  fireEvent.click(within(row).getByRole("button", { name: "Workspace" }));
  await act(async () => { await vi.dynamicImportSettled(); });
}

describe("Home workspace arrival", () => {
  it("animates mapped buildings, then reveals the same mounted workspace with its state intact", async () => {
    await openWorkspace();
    expect(mocks.start).toHaveBeenCalledOnce();
    expect(mocks.start.mock.calls[0]![1]).toEqual(mapped);
    expect(screen.getByLabelText(`Arriving at ${mapped.label}`)).toBeTruthy();
    expect(screen.getByRole("main", { name: "Existing workspace" })).toBeTruthy();
    fireEvent.click(screen.getByText("Selected room 0"));
    vi.useFakeTimers();
    act(() => mocks.start.mock.calls[0]![2]());
    act(() => vi.advanceTimersByTime(200));
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeNull();
    expect(screen.getByText("Selected room 1")).toBeTruthy();
    expect(mocks.mounted).toHaveBeenCalledOnce();
    expect(mocks.unmounted).not.toHaveBeenCalled();
    expect(location.pathname).toBe(`/admin/${mapped.id}`);
    expect(location.search).toBe("");
    expect(history.state.workspaceArrival).toBeUndefined();
  });

  it("caps the entire entrance at five seconds even if the map never completes", async () => {
    vi.useFakeTimers();
    renderApp();
    fireEvent.click(screen.getAllByRole("button", { name: "Workspace" })[0]!);
    act(() => vi.advanceTimersByTime(4999));
    expect(screen.getByLabelText(`Arriving at ${mapped.label}`)).toBeTruthy();
    act(() => vi.advanceTimersByTime(1));
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeNull();
  });

  it("skips buildings without a geographic location", async () => {
    await openWorkspace("local-building");
    expect(screen.getByText("local-building")).toBeTruthy();
    expect(mocks.start).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Skip animation" })).toBeNull();
  });

  it("preserves direct workspace and phone links", async () => {
    history.replaceState(null, "", `/admin/${mapped.id}?from=A&to=B`);
    renderApp();
    await act(async () => { await vi.dynamicImportSettled(); });
    expect(screen.getByRole("main", { name: "Existing workspace" })).toBeTruthy();
    expect(mocks.start).not.toHaveBeenCalled();
    act(() => navigate(`/b/${mapped.id}?from=A&to=B`));
    expect(screen.getByText("Phone guide")).toBeTruthy();
    expect(location.search).toBe("?from=A&to=B");
  });

  it("keeps the Home Guide action immediate", async () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: `Open ${mapped.label} as phone guide` }));
    expect(screen.getByText("Phone guide")).toBeTruthy();
    expect(mocks.start).not.toHaveBeenCalled();
  });

  it("allows immediate skipping and aborts pending map work", async () => {
    await openWorkspace();
    const signal = mocks.start.mock.calls[0]![3] as AbortSignal;
    fireEvent.click(screen.getByRole("button", { name: "Skip animation" }));
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeNull();
    expect(signal.aborted).toBe(true);
    expect(screen.getByRole("main", { name: "Existing workspace" })).toBeTruthy();
  });

  it("opens immediately for reduced motion and responds to preference changes mid-flight", async () => {
    Object.assign(motion, { matches: true });
    await openWorkspace();
    expect(mocks.start).not.toHaveBeenCalled();
    cleanup();
    history.replaceState(null, "", "/");
    Object.assign(motion, { matches: false });
    await openWorkspace();
    vi.useFakeTimers();
    Object.assign(motion, { matches: true });
    act(() => motion.dispatchEvent(new Event("change")));
    act(() => vi.advanceTimersByTime(200));
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeNull();
  });

  it("cancels on navigation and does not replay consumed history entries", async () => {
    await openWorkspace();
    const state = history.state;
    const signal = mocks.start.mock.calls[0]![3] as AbortSignal;
    act(() => navigate("/"));
    expect(signal.aborted).toBe(true);
    act(() => navigate(`/admin/${mapped.id}`, false, state));
    await act(async () => { await vi.dynamicImportSettled(); });
    expect(mocks.start).toHaveBeenCalledOnce();
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeNull();
  });

  it("survives StrictMode's effect replay without consuming the entrance too early", async () => {
    history.replaceState({ workspaceArrival: mapped.id }, "", `/admin/${mapped.id}`);
    renderApp(true);
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeTruthy();
    await act(async () => { await vi.dynamicImportSettled(); });
    await waitFor(() => expect(mocks.start).toHaveBeenCalledOnce());
    expect(screen.getByLabelText(`Arriving at ${mapped.label}`)).toBeTruthy();
  });

  it("continues into the workspace if starting the map throws", async () => {
    mocks.start.mockImplementationOnce(() => { throw new Error("WebGL unavailable"); });
    await openWorkspace();
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 220)); });
    expect(screen.queryByLabelText(`Arriving at ${mapped.label}`)).toBeNull();
    expect(screen.getByRole("main", { name: "Existing workspace" })).toBeTruthy();
  });
});

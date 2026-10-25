import { act, cleanup, renderHook } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CoworkerMessageRequest } from "../api/coworkers";
import { coworker, coworkerSession } from "./__tests__/coworkerData";
import { coworkerPosition, useCoworkerMarkers } from "./coworkerPositions";
import { useCoworkers } from "./useCoworkers";

const fetchMock = vi.fn<typeof fetch>();
const sessionKey = (buildingId: string) => `building-workspace:coworker-session:${encodeURIComponent(buildingId)}`;
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

async function flush() {
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", fetchMock);
  localStorage.clear();
  sessionStorage.clear();
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => response(coworkerSession()));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("coworker sessions", () => {
  it("creates only one session during React's development effect checks", async () => {
    renderHook(() => useCoworkers("building-a", false), { wrapper: StrictMode });
    await flush();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("uses the server roster and keeps drafts and history with the selected member", async () => {
    fetchMock.mockResolvedValue(response(coworkerSession({ messages: [
      { id: "m1", memberId: "maya", role: "assistant", text: "Maya only", createdAt: Date.now() },
      { id: "m2", memberId: "jonas", role: "assistant", text: "Jonas only", createdAt: Date.now() },
    ] })));
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    act(() => result.current.select("maya"));
    act(() => result.current.setDraft("Maya's draft"));
    act(() => result.current.select("jonas"));
    expect({ name: result.current.selected?.name, draft: result.current.draft, messages: result.current.messages.map((message) => message.text) })
      .toEqual({ name: "Jonas Weber", draft: "", messages: ["Jonas only"] });
    act(() => result.current.select("maya"));
    expect(result.current.draft).toBe("Maya's draft");
  });

  it("never shows the previous building's messages while the next building loads", async () => {
    fetchMock.mockResolvedValueOnce(response(coworkerSession({ messages: [
      { id: "secret", memberId: "maya", role: "user", text: "First building only", createdAt: Date.now() },
    ] })));
    const { result, rerender } = renderHook(({ buildingId }) => useCoworkers(buildingId, true), { initialProps: { buildingId: "building-a" } });
    await flush();
    act(() => result.current.select("maya"));
    act(() => result.current.setDraft("First draft"));
    fetchMock.mockImplementationOnce(() => new Promise<Response>(() => {}));
    rerender({ buildingId: "building-b" });
    expect({ selected: result.current.selected, messages: result.current.messages, draft: result.current.draft })
      .toEqual({ selected: undefined, messages: [], draft: "" });
  });

  it("ignores a late response from the previous building", async () => {
    let finish: (value: Response) => void = () => {};
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => { finish = resolve; }));
    const { result, rerender } = renderHook(({ buildingId }) => useCoworkers(buildingId, true), { initialProps: { buildingId: "building-a" } });
    await flush();
    rerender({ buildingId: "building-b" });
    await flush();
    finish(response(coworkerSession({ sessionId: "old-building", members: [coworker({ name: "Wrong building" })] })));
    await flush();
    expect(result.current.members.map((member) => member.name)).toEqual(["Maya Chen", "Jonas Weber"]);
  });

  it("loads only the token stored for this building and browser session", async () => {
    sessionStorage.setItem(sessionKey("building/a"), "private/session");
    fetchMock.mockResolvedValueOnce(response(coworkerSession({ sessionId: "private/session" })));
    renderHook(() => useCoworkers("building/a", false));
    await flush();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/buildings/building%2Fa/coworkers/sessions/private%2Fsession");
  });

  it("starts with an empty chat after the browser session token is removed", async () => {
    const first = renderHook(() => useCoworkers("building-a", true));
    await flush();
    first.unmount();
    sessionStorage.clear();
    fetchMock.mockClear();
    const second = renderHook(() => useCoworkers("building-a", true));
    await flush();
    expect({ method: fetchMock.mock.calls[0]?.[1]?.method, messages: second.result.current.messages })
      .toEqual({ method: "POST", messages: [] });
  });

  it("clears expired session content and offers explicit recovery", async () => {
    sessionStorage.setItem(sessionKey("building-a"), "expired");
    fetchMock.mockResolvedValueOnce(response({ detail: "Expired" }, 410));
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    expect({ expired: result.current.expired, stored: sessionStorage.getItem(sessionKey("building-a")), messages: result.current.messages })
      .toEqual({ expired: true, stored: null, messages: [] });
    act(() => result.current.reload());
    await flush();
    expect({ expired: result.current.expired, available: result.current.chatAvailable }).toEqual({ expired: false, available: true });
  });

  it("clears an invalid stored session token instead of retrying it forever", async () => {
    sessionStorage.setItem(sessionKey("building-a"), "invalid-token");
    fetchMock.mockResolvedValueOnce(response({ detail: [{ type: "string_pattern_mismatch" }] }, 422));
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    expect({ expired: result.current.expired, stored: sessionStorage.getItem(sessionKey("building-a")) })
      .toEqual({ expired: true, stored: null });
  });

  it("ignores a late send reply after a building change", async () => {
    const { result, rerender } = renderHook(({ buildingId }) => useCoworkers(buildingId, true), { initialProps: { buildingId: "building-a" } });
    await flush();
    act(() => result.current.select("maya"));
    act(() => result.current.setDraft("First building message"));
    let finish: (value: Response) => void = () => {};
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => { finish = resolve; }));
    act(() => result.current.send());
    rerender({ buildingId: "building-b" });
    await flush();
    finish(response(coworkerSession({ messages: [
      { id: "late-reply", memberId: "maya", role: "assistant", text: "Private first-building reply", createdAt: Date.now() },
    ] })));
    await flush();
    act(() => result.current.select("maya"));
    expect({ messages: result.current.messages, pending: result.current.pending }).toEqual({ messages: [], pending: undefined });
  });

  it("keeps a failed message for retry with the same request ID and no duplicate history", async () => {
    const requests: CoworkerMessageRequest[] = [];
    fetchMock.mockImplementation(async (_path, init) => {
      if (!init?.body) return response(coworkerSession());
      const body: CoworkerMessageRequest = JSON.parse(String(init.body));
      requests.push(body);
      if (requests.length === 1) return response({ detail: "Provider unavailable" }, 503);
      return response(coworkerSession({ messages: [
        { id: "accepted", memberId: body.memberId, role: "user", text: body.text, createdAt: Date.now() },
        { id: "reply", memberId: body.memberId, role: "assistant", text: "On my way", createdAt: Date.now() },
      ] }));
    });
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    act(() => result.current.select("maya"));
    act(() => result.current.setDraft("Go to the lobby"));
    act(() => result.current.send());
    await flush();
    expect(result.current.pending?.status).toBe("failed");
    act(() => { result.current.retry(); result.current.retry(); });
    await flush();
    expect({ requests, texts: result.current.messages.map((message) => message.text), pending: result.current.pending })
      .toEqual({ requests: [requests[0], requests[0]], texts: ["Go to the lobby", "On my way"], pending: undefined });
  });

  it("keeps the fallback roster and an error when the server is unavailable", async () => {
    fetchMock.mockRejectedValueOnce(new Error("Network offline"));
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    expect({ count: result.current.members.length, error: result.current.error, available: result.current.chatAvailable })
      .toEqual({ count: 4, error: "Network offline", available: false });
  });

  it("rejects an invalid server payload before it can appear in the UI", async () => {
    fetchMock.mockResolvedValueOnce(response({ sessionId: "partial" }));
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    expect(result.current.error).toBe("Invalid coworker response.");
  });

  it("stores visibility and stops polling when both the drawing and chat are closed", async () => {
    const { result, rerender } = renderHook(({ open }) => useCoworkers("building-a", open), { initialProps: { open: false } });
    await flush();
    act(() => result.current.setShow(false));
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect({ calls: fetchMock.mock.calls.length, stored: localStorage.getItem("building-workspace:show-coworkers"), markers: result.current.markers })
      .toEqual({ calls: 1, stored: "false", markers: [] });
    rerender({ open: true });
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("restores hidden coworkers after a remount without disabling chats", async () => {
    localStorage.setItem("building-workspace:show-coworkers", "false");
    const { result } = renderHook(() => useCoworkers("building-a", true));
    await flush();
    expect({ show: result.current.show, available: result.current.chatAvailable }).toEqual({ show: false, available: true });
  });

  it("uses the server clock and catches up after coworkers were hidden", async () => {
    vi.setSystemTime(10_000);
    const member = coworker({ journey: { destinationName: "Workshop", arrivesAt: 104_000, points: [
      { floorId: "ground", x: 0, y: 0, at: 100_000 },
      { floorId: "ground", x: 8, y: 4, at: 104_000 },
    ] } });
    fetchMock.mockResolvedValue(response(coworkerSession({ serverTime: 100_000, members: [member] })));
    const { result } = renderHook(() => useCoworkers("building-a", false));
    await flush();
    act(() => result.current.setShow(false));
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    act(() => result.current.setShow(true));
    expect(result.current.markers[0]).toMatchObject({ floorId: "ground", x: 4, y: 2 });
  });
});

describe("coworker display position", () => {
  const member = coworker({ journey: { destinationName: "Upper room", arrivesAt: 3_000, points: [
    { floorId: "ground", x: 0, y: 0, at: 1_000 },
    { floorId: "ground", x: 10, y: 4, at: 2_000 },
    { floorId: "upper", x: 30, y: 8, at: 3_000 },
  ] } });

  it("moves on each animation frame and stops after arrival", () => {
    vi.setSystemTime(1_000);
    const members = [member];
    const { result } = renderHook(() => useCoworkerMarkers(members, true, 0));
    act(() => vi.advanceTimersToNextFrame());
    const first = result.current[0]!.x;
    act(() => vi.advanceTimersToNextFrame());
    const second = result.current[0]!.x;
    act(() => vi.advanceTimersByTime(2_000));
    expect({ movesEachFrame: first > 0 && Math.abs(second - first - 0.16) < 1e-10, final: result.current[0], timers: vi.getTimerCount() }).toMatchObject({
      movesEachFrame: true, final: { floorId: "upper", x: 30, y: 8 }, timers: 0,
    });
  });

  it("cancels movement frames when hidden and catches up when shown", () => {
    vi.setSystemTime(1_000);
    const members = [member];
    const { result, rerender } = renderHook(({ show }) => useCoworkerMarkers(members, show, 0), { initialProps: { show: true } });
    rerender({ show: false });
    const hiddenTimers = vi.getTimerCount();
    act(() => vi.advanceTimersByTime(500));
    rerender({ show: true });
    expect({ hiddenTimers, position: result.current[0] }).toMatchObject({ hiddenTimers: 0, position: { x: 5, y: 2 } });
  });

  it("interpolates a same-floor segment", () => {
    expect(coworkerPosition(member, 1_500)).toMatchObject({ floorId: "ground", x: 5, y: 2 });
  });

  it("holds at the floor connector until the next floor is reached", () => {
    expect(coworkerPosition(member, 2_500)).toMatchObject({ floorId: "ground", x: 10, y: 4 });
  });

  it("reaches the final point even without another server poll", () => {
    expect(coworkerPosition(member, 9_000)).toMatchObject({ floorId: "upper", x: 30, y: 8 });
  });
});

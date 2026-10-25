import { Conversation, ConversationProvider, type HookOptions } from "@elevenlabs/react";
import { act, cleanup, fireEvent, render, renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ChatInput } from "./ConversationLog";
import type { VoiceContext } from "./context";
import { MicButton } from "./MicButton";
import { useBuildingVoice } from "./useBuildingVoice";

// Keep the React SDK provider real. Only the paid connection and browser microphone are replaced.
const transport = { start: vi.fn() };

function connection() {
  return {
    setMicMuted: vi.fn(), sendUserMessage: vi.fn(), sendUserActivity: vi.fn(),
    sendContextualUpdate: vi.fn(), getOutputVolume: () => 0,
    endSession: vi.fn().mockResolvedValue(undefined),
  };
}
type Connection = ReturnType<typeof connection>;
type Options = Omit<HookOptions, "onConversationCreated"> & { onConversationCreated?: (value: Connection) => void };
let options: Options;
let wire: Connection;
const context: VoiceContext = { buildingId: "building", position: { id: "A", name: "Lobby" }, destination: { id: "B", name: "Office" } };
const microphone = vi.fn();
const fetchToken = vi.fn();
const wrapper = ({ children }: { children: ReactNode }) => <ConversationProvider>{children}</ConversationProvider>;

beforeEach(() => {
  transport.start.mockReset();
  vi.spyOn(Conversation, "startSession").mockImplementation(transport.start);
  wire = connection();
  transport.start.mockImplementation(async (next: Options) => {
    options = next;
    next.onConversationCreated?.(wire);
    next.onStatusChange?.({ status: "connected" });
    next.onConnect?.({ conversationId: "test-conversation" });
    return wire;
  });
  microphone.mockReset().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] });
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia: microphone } });
  fetchToken.mockReset().mockImplementation(async () => new Response(JSON.stringify({ token: "private-test-token" })));
  vi.stubGlobal("fetch", fetchToken);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("starts through the SDK, mutes without ending, and keeps typed messages in the same session", async () => {
  const { result } = renderHook(() => useBuildingVoice(context, vi.fn()), { wrapper });
  await act(() => result.current.start());
  expect(result.current.phase).toBe("listening");
  act(() => result.current.toggleMute());
  expect(result.current.isMuted).toBe(true);
  expect(wire.endSession).not.toHaveBeenCalled();
  act(() => result.current.send("  Is the lift open?  "));
  expect(wire.sendUserMessage).toHaveBeenCalledWith("Is the lift open?");
  expect(result.current.entries).toEqual([expect.objectContaining({ role: "user", text: "Is the lift open?" })]);
  act(() => result.current.toggleMute());
  expect(result.current.isMuted).toBe(false);
});

it("clears old history on restart and ignores events from the ended session", async () => {
  const onRoute = vi.fn();
  const { result } = renderHook(() => useBuildingVoice(context, onRoute), { wrapper });
  await act(() => result.current.start());
  const previous = options;
  act(() => previous.onMessage?.({ role: "agent", source: "ai", message: "Old answer", event_id: 1 }));
  act(() => {
    result.current.stop();
    previous.onStatusChange?.({ status: "disconnected" });
  });
  await act(() => result.current.start());
  act(() => {
    previous.onMessage?.({ role: "agent", source: "ai", message: "Late answer", event_id: 2 });
    previous.onError?.("Late error", undefined);
    previous.onDisconnect?.({ reason: "user" });
  });
  expect(result.current.entries).toEqual([]);
  expect(result.current.error).toBeUndefined();
  expect(result.current.phase).toBe("listening");
  expect(onRoute).not.toHaveBeenCalled();
});

it("sends explicit cleared context and does not repeat unchanged context", async () => {
  const { result, rerender } = renderHook((value: VoiceContext) => useBuildingVoice(value, vi.fn()), { wrapper, initialProps: context });
  await act(() => result.current.start());
  rerender({ buildingId: "building" });
  expect(wire.sendContextualUpdate).toHaveBeenCalledWith(JSON.stringify({ type: "app_context", current_space: null, displayed_destination: null }), undefined);
  rerender({ buildingId: "building" });
  expect(wire.sendContextualUpdate).toHaveBeenCalledTimes(1);
});

it("uses the latest room if it changes while fetching a token", async () => {
  let resolveToken: (value: Response) => void = () => {};
  fetchToken.mockImplementation(() => new Promise<Response>((resolve) => { resolveToken = resolve; }));
  const { result, rerender } = renderHook((value: VoiceContext) => useBuildingVoice(value, vi.fn()), { wrapper, initialProps: context });
  let pending: Promise<void>;
  await act(async () => { pending = result.current.start(); });
  rerender({ buildingId: "building", position: { id: "C", name: "Stairs" } });
  await act(async () => { resolveToken(new Response(JSON.stringify({ token: "token" }))); await pending; });
  expect(options.dynamicVariables).toMatchObject({ current_space_id: "C", destination_id: "" });
});

it("cancels a pending microphone request without starting a connection", async () => {
  let allow: (value: { getTracks: () => { stop: () => void }[] }) => void = () => {};
  const stopTrack = vi.fn();
  microphone.mockImplementation(() => new Promise((resolve) => { allow = resolve; }));
  const { result } = renderHook(() => useBuildingVoice(context, vi.fn()), { wrapper });
  let pending: Promise<void>;
  await act(async () => { pending = result.current.start(); });
  act(() => result.current.stop());
  await act(async () => { allow({ getTracks: () => [{ stop: stopTrack }] }); await pending; });
  expect(stopTrack).toHaveBeenCalled();
  expect(fetchToken).not.toHaveBeenCalled();
  expect(transport.start).not.toHaveBeenCalled();
});

it("shows a connection rejection reported by the SDK", async () => {
  transport.start.mockRejectedValue(new Error("Connection failed"));
  const { result } = renderHook(() => useBuildingVoice(context, vi.fn()), { wrapper });
  await act(() => result.current.start());
  expect(result.current.error).toBe("Connection failed");
  expect(result.current.phase).toBe("error");
});

it("replaces an interrupted response with the provider correction", async () => {
  const { result } = renderHook(() => useBuildingVoice(context, vi.fn()), { wrapper });
  await act(() => result.current.start());
  act(() => {
    options.onMessage?.({ role: "agent", source: "ai", message: "Go to the lift and turn left", event_id: 8 });
    options.onAgentResponseCorrection?.({ event_id: 8, original_agent_response: "Go to the lift and turn left", corrected_agent_response: "Go to the lift" });
  });
  expect(result.current.entries).toEqual([expect.objectContaining({ text: "Go to the lift" })]);
});

it("keeps mute, typing and end as separate UI actions", async () => {
  function Controls() {
    const voice = useBuildingVoice(context, vi.fn());
    return <><MicButton voice={voice} /><ChatInput enabled={voice.phase === "listening"} onSend={voice.send} onTyping={voice.muteForTyping} /></>;
  }
  render(<ConversationProvider><Controls /></ConversationProvider>);
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Talk to Locora" })));
  fireEvent.focus(screen.getByRole("textbox", { name: "Message" }));
  expect(screen.getByRole("button", { name: "Unmute microphone" })).toBeTruthy();
  expect(wire.endSession).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("textbox", { name: "Message" }), { target: { value: "Find the exit" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  expect(wire.sendUserMessage).toHaveBeenCalledWith("Find the exit");
  fireEvent.click(screen.getByRole("button", { name: "End conversation" }));
  expect(wire.endSession).toHaveBeenCalledTimes(1);
});

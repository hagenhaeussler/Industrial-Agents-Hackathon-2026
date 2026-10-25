import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fixture } from "../../../packages/building-view/src/testing/fixture";
import type { ChatMessage } from "../api/coworkers";
import { coworkerSession } from "./__tests__/coworkerData";
import { DirectMessages } from "./DirectMessages";
import { Sidebar } from "./Sidebar";
import { useCoworkers } from "./useCoworkers";

const fetchMock = vi.fn<typeof fetch>();
let messages: ChatMessage[];

function Harness() {
  const [open, setOpen] = useState(true);
  const chat = useCoworkers("building-a", open);
  return <>
    <Sidebar
      building={fixture()} view="model" onView={() => {}} channel={undefined} onChannel={() => {}}
      selectedAssetId={undefined} onSelectEquipment={() => {}}
      positionName={undefined} onSettings={() => {}} coworkers={chat.members}
      selectedMemberId={open ? chat.selected?.id : undefined}
      onMember={(id) => { chat.select(id); setOpen(true); }} showCoworkers={chat.show} onShowCoworkers={chat.setShow}
    />
    <button type="button" onClick={() => setOpen(false)}>Open assistant</button>
    <button type="button" onClick={chat.reload}>Refresh session</button>
    {open && <DirectMessages chat={chat} />}
  </>;
}

function renderChat() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Harness /></QueryClientProvider>);
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  messages = [
    { id: "maya-one", memberId: "maya", role: "assistant", text: "Maya's building update", createdAt: 1_000 },
    { id: "jonas-one", memberId: "jonas", role: "assistant", text: "Jonas's maintenance update", createdAt: 2_000 },
  ];
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (path) => new Response(JSON.stringify(path === "/api/buildings" ? [] : coworkerSession({ messages })), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("direct messages", () => {
  it("opens the selected coworker's history and preserves a separate draft for each member", async () => {
    renderChat();
    await screen.findByText("Choose a coworker in the sidebar to open their chat.");
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    await screen.findByText("Maya's building update");
    fireEvent.change(screen.getByRole("textbox", { name: "Message Maya Chen" }), { target: { value: "Maya draft" } });
    fireEvent.click(screen.getByRole("button", { name: "Jonas Weber, Maintenance, AI coworker" }));
    await screen.findByText("Jonas's maintenance update");
    expect(screen.queryByText("Maya's building update")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    expect(screen.getByRole("textbox", { name: "Message Maya Chen" }).getAttribute("disabled")).toBeNull();
    expect(screen.getByDisplayValue("Maya draft")).toBeTruthy();
  });

  it("highlights a member only while their direct message panel is active", async () => {
    renderChat();
    const member = await screen.findByRole("button", { name: "Maya Chen, Facility manager, AI coworker" });
    fireEvent.click(member);
    expect(member.getAttribute("aria-current")).toBe("page");
    fireEvent.click(screen.getByRole("button", { name: "Open assistant" }));
    expect(member.getAttribute("aria-current")).toBeNull();
  });

  it("opens a chat from the narrow-screen workspace menu and closes the menu", async () => {
    renderChat();
    await waitFor(() => expect(screen.queryByText("Loading coworkers…")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Open workspace menu" }));
    const menu = screen.getByRole("dialog", { name: "Workspace" });
    fireEvent.click(within(menu).getByRole("button", { name: "Jonas Weber, Maintenance, AI coworker" }));
    expect(screen.queryByRole("dialog", { name: "Workspace" })).toBeNull();
    expect(screen.getByRole("list", { name: "Messages with Jonas Weber" }).textContent).toContain("Jonas's maintenance update");
  });

  it("keeps chat usable when the sidebar hides coworkers", async () => {
    renderChat();
    await waitFor(() => expect(screen.queryByText("Loading coworkers…")).toBeNull());
    fireEvent.click(screen.getByRole("checkbox", { name: "Show coworkers" }));
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Message Maya Chen" }), { target: { value: "Hello" } });
    expect({ visible: localStorage.getItem("building-workspace:show-coworkers"), disabled: screen.getByRole("button", { name: "Send direct message" }).getAttribute("disabled") })
      .toEqual({ visible: "false", disabled: null });
  });

  it("disables an empty or blank message", async () => {
    renderChat();
    await waitFor(() => expect(screen.queryByText("Loading coworkers…")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Message Maya Chen" }), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: "Send direct message" }).hasAttribute("disabled")).toBe(true);
  });

  it("shows the failed send and a retry without adding an unconfirmed chat message", async () => {
    renderChat();
    await waitFor(() => expect(screen.queryByText("Loading coworkers…")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Reply service is offline" }), { status: 503 }));
    fireEvent.change(screen.getByRole("textbox", { name: "Message Maya Chen" }), { target: { value: "Can you check the lobby?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send direct message" }));
    await screen.findByRole("button", { name: "Retry message" });
    expect(screen.getByRole("alert").textContent).toContain("Reply service is offline");
    expect(screen.getByRole("list", { name: "Messages with Maya Chen" }).textContent).not.toContain("Can you check the lobby?");
  });

  it("shows a failed user message only once after the server returns it in history", async () => {
    renderChat();
    await waitFor(() => expect(screen.queryByText("Loading coworkers…")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    fetchMock.mockImplementationOnce(async (_path, init) => {
      const body: { requestId: string; memberId: string; text: string } = JSON.parse(String(init?.body));
      messages = [...messages, { id: body.requestId, memberId: body.memberId, role: "user", text: body.text, createdAt: Date.now() }];
      return new Response(JSON.stringify({ detail: "Reply failed" }), { status: 502 });
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Message Maya Chen" }), { target: { value: "Where are you now?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send direct message" }));
    await screen.findByRole("button", { name: "Retry message" });
    fireEvent.click(screen.getByRole("button", { name: "Refresh session" }));
    await waitFor(() => expect(screen.getByRole("list", { name: "Messages with Maya Chen" }).textContent).toContain("Where are you now?"));
    expect(screen.getAllByText("Where are you now?")).toHaveLength(1);
  });

  it("shows the server's unavailable reason and keeps sending disabled", async () => {
    fetchMock.mockImplementation(async (path) => new Response(JSON.stringify(path === "/api/buildings" ? [] : coworkerSession({
      chatAvailable: false, unavailableReason: "AI coworker replies are not configured on this server.",
    })), { status: 200 }));
    renderChat();
    await screen.findByText("AI coworker replies are not configured on this server.");
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    expect(screen.getByRole("textbox", { name: "Message Maya Chen" }).hasAttribute("disabled")).toBe(true);
  });

  it("does not move the reader when a new message arrives above the scroll end", async () => {
    renderChat();
    await waitFor(() => expect(screen.queryByText("Loading coworkers…")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Maya Chen, Facility manager, AI coworker" }));
    const list = screen.getByRole("list", { name: "Messages with Maya Chen" });
    Object.defineProperties(list, { scrollHeight: { value: 1_000, configurable: true }, clientHeight: { value: 100, configurable: true } });
    list.scrollTop = 100;
    fireEvent.scroll(list);
    messages = [...messages, { id: "maya-two", memberId: "maya", role: "assistant", text: "New update", createdAt: 3_000 }];
    fireEvent.click(screen.getByRole("button", { name: "Refresh session" }));
    const latest = await screen.findByRole("button", { name: "New messages. Go to latest" });
    expect(list.scrollTop).toBe(100);
    fireEvent.click(latest);
    expect(list.scrollTop).toBe(1_000);
  });
});

import { ConversationProvider, useConversation } from "@elevenlabs/react";
import { useEffect, useState, type FormEvent } from "react";
import { upsert, withoutAudioTags, type TranscriptEntry } from "./transcript";

export function App() {
  return (
    <ConversationProvider>
      <VoiceDemo />
    </ConversationProvider>
  );
}

type Building = { id: string; name: string };

/** Minimal test page: pick a building, start a voice conversation, follow the transcript and tool calls. */
function VoiceDemo() {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [buildingId, setBuildingId] = useState("");
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string>();
  const [draft, setDraft] = useState("");

  const conversation = useConversation({
    onMessage: ({ role, message, event_id }) =>
      setEntries((current) =>
        upsert(current, {
          key: `${role}-${event_id}`,
          kind: "message",
          role,
          text: role === "agent" ? withoutAudioTags(message) : message,
        }),
      ),
    onMCPToolCall: (call) =>
      setEntries((current) =>
        upsert(current, {
          key: `tool-${call.tool_call_id}`,
          kind: "tool",
          name: call.tool_name,
          state: call.state,
          parameters: call.parameters,
        }),
      ),
    onError: (message) => setError(message),
  });
  const { status, isSpeaking } = conversation;

  useEffect(() => {
    fetch("/api/voice/buildings")
      .then((response) => response.json())
      .then((list: Building[]) => {
        setBuildings(list);
        setBuildingId((current) => current || (list[0]?.id ?? ""));
      })
      .catch(() => setError("Could not load the buildings."));
  }, []);
  const active = status === "connected" || status === "connecting";

  async function start() {
    setError(undefined);
    setEntries([]);
    try {
      // Ask for the microphone first so a denied permission shows here; the SDK opens its own stream.
      const microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
      microphone.getTracks().forEach((track) => track.stop());
      const response = await fetch("/api/voice/token");
      const body: { token?: string; error?: string } = await response.json();
      if (!response.ok || !body.token) throw new Error(body.error ?? "Could not start a voice conversation.");
      // The agent sends building_id to the tools with every call, so they answer for this building.
      conversation.startSession({ conversationToken: body.token, dynamicVariables: { building_id: buildingId } });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  function send(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    conversation.sendUserMessage(text);
    // Typed messages do not come back through onMessage, so add them to the transcript here.
    setEntries((current) => [...current, { key: `typed-${crypto.randomUUID()}`, kind: "message", role: "user", text }]);
    setDraft("");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 p-6 font-sans text-neutral-900">
      <header className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Locora voice demo</h1>
        <select
          value={buildingId}
          onChange={(event) => setBuildingId(event.target.value)}
          disabled={active}
          aria-label="Building"
          className="min-w-0 flex-1 rounded border border-neutral-300 px-2 py-2"
        >
          {buildings.map((building) => (
            <option key={building.id} value={building.id}>
              {building.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={!active && !buildingId}
          onClick={active ? conversation.endSession : start}
          className={`rounded px-4 py-2 font-medium text-white disabled:opacity-50 ${active ? "bg-red-600" : "bg-blue-600"}`}
        >
          {active ? "End" : "Start conversation"}
        </button>
      </header>

      <p className="text-sm">
        Status: {status}
        {status === "connected" && (isSpeaking ? ", agent speaking" : ", listening")}
      </p>
      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <ol className="flex flex-1 flex-col gap-2">
        {entries.map((entry) =>
          entry.kind === "message" ? (
            <li key={entry.key} className={entry.role === "user" ? "self-end text-right" : "self-start"}>
              <span className="block text-xs text-neutral-500">{entry.role === "user" ? "You" : "Locora"}</span>
              <span
                className={`inline-block rounded px-3 py-2 ${entry.role === "user" ? "bg-blue-50" : "bg-neutral-100"}`}
              >
                {entry.text}
              </span>
            </li>
          ) : (
            <li key={entry.key} className="font-mono text-xs text-neutral-600">
              Tool {entry.name} ({entry.state}) {JSON.stringify(entry.parameters)}
            </li>
          ),
        )}
      </ol>

      <form onSubmit={send} className="flex gap-2">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={status !== "connected"}
          placeholder="Type a message"
          className="flex-1 rounded border border-neutral-300 px-3 py-2 disabled:bg-neutral-100"
        />
        <button type="submit" disabled={status !== "connected"} className="rounded border px-4 py-2 disabled:opacity-50">
          Send
        </button>
      </form>
    </main>
  );
}

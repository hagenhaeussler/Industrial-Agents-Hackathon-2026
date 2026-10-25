import { useConversation, type HookOptions } from "@elevenlabs/react";
import { useEffect, useRef, useState } from "react";
import type { RouteRequest } from "../api/buildings";
import { contextUpdate, dynamicVariables, type VoiceContext } from "./context";
import { createVoiceLog } from "./diagnostics";
import { routeFromToolCall } from "./toolCalls";
import { toolLabel, upsert, withoutAudioTags, type TranscriptEntry } from "./transcript";

const VOICE_SERVER: string = import.meta.env.VITE_VOICE_SERVER ?? "";
export type VoicePhase = "off" | "connecting" | "listening" | "speaking" | "error";

/** One conversation owns its callbacks, transcript and context. Ended sessions cannot change a new one. */
export function useBuildingVoice(context: VoiceContext, onRoute: (request: RouteRequest) => void) {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string>();
  const [starting, setStarting] = useState(false);
  const [hasLog, setHasLog] = useState(false);
  const conversation = useConversation();
  const latest = useRef({ context, onRoute });
  latest.current = { context, onRoute };
  const log = useRef(createVoiceLog());
  const session = useRef<{ abort: AbortController; context: string } | undefined>(undefined);
  const connected = conversation.status === "connected";

  const currentContext = contextUpdate(context);
  useEffect(() => {
    const active = session.current;
    if (!connected || !active || active.context === currentContext) return;
    conversation.sendContextualUpdate(currentContext);
    active.context = currentContext;
    log.current.add("context", JSON.parse(currentContext));
  }, [connected, currentContext, conversation.sendContextualUpdate]);

  useEffect(() => () => {
    session.current?.abort.abort();
    session.current = undefined;
  }, []);

  async function start() {
    if (session.current || conversation.status === "connecting" || connected) return;
    const active = { abort: new AbortController(), context: "" };
    session.current = active;
    const currentLog = createVoiceLog();
    log.current = currentLog;
    setHasLog(true);
    setEntries([]);
    setError(undefined);
    setStarting(true);
    const isCurrent = () => session.current === active;
    const callbacks = {
      onConnect: ({ conversationId }) => {
        if (!isCurrent()) return;
        conversation.setMuted(false);
        currentLog.connect(conversationId);
        currentLog.add("connected", {});
        setStarting(false);
      },
      onDisconnect: (details) => {
        if (!isCurrent()) return;
        currentLog.add("disconnected", details);
        if (details.reason === "error") setError(details.message);
        session.current = undefined;
        setStarting(false);
      },
      onMessage: ({ role, message, event_id }) => {
        if (!isCurrent()) return;
        currentLog.add("message", { role, message, event_id, input: role === "user" ? "microphone" : "agent" });
        if (role === "user" && message.trim() === "...") return;
        setEntries((current) => upsert(current, {
          key: `${role}-${event_id}`, kind: "message", role,
          text: role === "agent" ? withoutAudioTags(message) : message,
        }));
      },
      onMCPToolCall: (call) => {
        if (!isCurrent()) return;
        currentLog.add("tool", call);
        setEntries((current) => upsert(current, {
          key: `tool-${call.tool_call_id}`, kind: "tool", name: toolLabel(call.tool_name), state: call.state,
        }));
        if (call.state !== "success") return;
        const request = routeFromToolCall(call.tool_name, call.parameters);
        if (request) latest.current.onRoute(request);
      },
      onAgentToolResponse: (result) => { if (isCurrent()) currentLog.add("tool_result", result); },
      onInterruption: (event) => { if (isCurrent()) currentLog.add("interruption", event); },
      onAgentResponseCorrection: (event) => {
        if (!isCurrent()) return;
        currentLog.add("correction", event);
        setEntries((current) => upsert(current, {
          key: `agent-${event.event_id}`, kind: "message", role: "agent",
          text: withoutAudioTags(event.corrected_agent_response),
        }));
      },
      onError: (message) => {
        if (!isCurrent()) return;
        currentLog.add("error", { message });
        setError(message);
        session.current = undefined;
        setStarting(false);
        conversation.endSession();
      },
    } satisfies HookOptions;

    try {
      const microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
      microphone.getTracks().forEach((track) => track.stop());
      if (!isCurrent()) return;
      const response = await fetch(`${VOICE_SERVER}/api/voice/token`, { cache: "no-store", signal: active.abort.signal });
      const body: unknown = await response.json();
      if (!isCurrent()) return;
      if (!response.ok || typeof body !== "object" || body === null || !("token" in body)
        || typeof body.token !== "string" || !body.token.trim()) {
        throw new Error("The voice assistant is not available right now.");
      }
      const startContext = latest.current.context;
      active.context = contextUpdate(startContext);
      currentLog.add("context", JSON.parse(active.context));
      conversation.startSession({ conversationToken: body.token, dynamicVariables: dynamicVariables(startContext), ...callbacks });
    } catch (cause) {
      if (!isCurrent()) return;
      callbacks.onError(cause instanceof DOMException && cause.name === "NotAllowedError"
        ? "Allow the microphone to talk to Locora."
        : cause instanceof Error ? cause.message : String(cause));
    }
  }

  function stop() {
    session.current?.abort.abort();
    session.current = undefined;
    setStarting(false);
    log.current.add("end_requested", {});
    conversation.endSession();
  }

  function muteForTyping() {
    if (!connected || !session.current) return;
    conversation.setMuted(true);
    conversation.sendUserActivity();
    log.current.add("microphone", { muted: true, reason: "typing" });
  }

  function toggleMute() {
    if (!connected || !session.current) return;
    const muted = !conversation.isMuted;
    conversation.setMuted(muted);
    log.current.add("microphone", { muted, reason: "button" });
  }

  function send(text: string) {
    const message = text.trim();
    if (!message || !connected || !session.current) return;
    muteForTyping();
    conversation.sendUserMessage(message);
    log.current.add("message", { role: "user", message, input: "typed" });
    setEntries((current) => [...current, { key: `typed-${crypto.randomUUID()}`, kind: "message", role: "user", text: message }]);
  }

  const phase: VoicePhase = starting || conversation.status === "connecting"
    ? "connecting" : connected ? conversation.isSpeaking ? "speaking" : "listening"
      : error || conversation.status === "error" ? "error" : "off";

  return {
    phase, entries, error, start, stop, send, isMuted: conversation.isMuted, toggleMute, muteForTyping,
    hasLog, downloadLog: () => log.current.download(), level: conversation.getOutputVolume,
  };
}

export type BuildingVoice = ReturnType<typeof useBuildingVoice>;

import { useConversation } from "@elevenlabs/react";
import { useEffect, useRef, useState } from "react";
import type { RouteRequest } from "../api/buildings";
import { routeFromToolCall } from "./toolCalls";
import { toolLabel, upsert, withoutAudioTags, type TranscriptEntry } from "./transcript";

/** The voice server that issues conversation tokens. Empty means the same origin, as with the dev proxy. */
const VOICE_SERVER: string = import.meta.env.VITE_VOICE_SERVER ?? "";

export interface Place {
  id: string;
  name: string;
}

/** What the agent should know about this screen. It talks about this building only. */
export interface VoiceContext {
  buildingId: string;
  position?: Place;
  destination?: Place;
}

/** What the avatar shows. It follows the conversation; the UI decides nothing else from it. */
export type VoicePhase = "off" | "connecting" | "listening" | "speaking" | "error";

/** Dynamic variables for the ElevenLabs agent. Unknown places are empty strings, as the agent config expects. */
export function dynamicVariables(context: VoiceContext): Record<string, string> {
  return {
    building_id: context.buildingId,
    current_space_id: context.position?.id ?? "",
    current_space_name: context.position?.name ?? "",
    destination_id: context.destination?.id ?? "",
    destination_name: context.destination?.name ?? "",
  };
}

/**
 * One voice conversation with the building agent. Must be used inside `ConversationProvider`.
 * `onRoute` receives each route the agent plans, so the screen can draw it.
 */
export function useBuildingVoice(context: VoiceContext, onRoute: (request: RouteRequest) => void) {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string>();
  const onRouteRef = useRef(onRoute);
  onRouteRef.current = onRoute;

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
    onMCPToolCall: (call) => {
      setEntries((current) =>
        upsert(current, { key: `tool-${call.tool_call_id}`, kind: "tool", name: toolLabel(call.tool_name), state: call.state }),
      );
      if (call.state !== "success") return;
      const request = routeFromToolCall(call.tool_name, call.parameters);
      if (request) onRouteRef.current(request);
    },
    onError: (message) => setError(message),
  });
  const { status, isSpeaking } = conversation;
  const connected = status === "connected";

  // Tell a running conversation when the user picks a new position or destination on screen.
  const { position, destination } = context;
  useEffect(() => {
    if (connected && position) {
      conversation.sendContextualUpdate(`The user is now at ${position.name} (space ID ${position.id}).`);
    }
  }, [connected, position?.id]);
  useEffect(() => {
    if (connected && destination) {
      conversation.sendContextualUpdate(`The user wants to go to ${destination.name} (space ID ${destination.id}).`);
    }
  }, [connected, destination?.id]);

  async function start() {
    setError(undefined);
    try {
      // Ask for the microphone first so a denied permission shows here; the SDK opens its own stream.
      const microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
      microphone.getTracks().forEach((track) => track.stop());
      const response = await fetch(`${VOICE_SERVER}/api/voice/token`);
      const body: { token?: string; error?: string } = await response.json().catch(() => ({}));
      if (!response.ok || !body.token) throw new Error(body.error ?? "The voice assistant is not available right now.");
      conversation.startSession({ conversationToken: body.token, dynamicVariables: dynamicVariables(context) });
    } catch (cause) {
      if (cause instanceof DOMException) setError("Allow the microphone to talk to the building.");
      else setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  function send(text: string) {
    const message = text.trim();
    if (!message || !connected) return;
    conversation.sendUserMessage(message);
    // Typed messages do not come back through onMessage, so add them here.
    setEntries((current) => [...current, { key: `typed-${crypto.randomUUID()}`, kind: "message", role: "user", text: message }]);
  }

  const phase: VoicePhase =
    status === "connecting"
      ? "connecting"
      : connected
        ? isSpeaking
          ? "speaking"
          : "listening"
        : error || status === "error"
          ? "error"
          : "off";

  return {
    phase,
    entries,
    error,
    start,
    stop: conversation.endSession,
    send,
    /** The agent's current output level from 0 to 1, for the avatar. */
    level: conversation.getOutputVolume,
  };
}

export type BuildingVoice = ReturnType<typeof useBuildingVoice>;

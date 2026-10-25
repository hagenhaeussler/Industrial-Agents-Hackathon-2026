import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import {
  CoworkerApiError, createCoworkerSession, loadCoworkerSession, sendCoworkerMessage,
  type Coworker, type CoworkerMessageRequest, type CoworkerSession,
} from "../api/coworkers";
import { MEMBERS } from "./team";
import { useCoworkerMarkers } from "./coworkerPositions";

export type CoworkerIdentity = Pick<Coworker, "id" | "name" | "role" | "color">;
const FALLBACK_COLORS = ["#b56843", "#397a91", "#8568a6", "#b58c26"];
const FALLBACK_MEMBERS: CoworkerIdentity[] = MEMBERS.map((member, index) => ({
  id: member.id, name: member.name, role: member.role, color: FALLBACK_COLORS[index] ?? "#397a91",
}));
const SHOW_KEY = "building-workspace:show-coworkers";
const POLL_MS = 5_000;
const NO_MEMBERS: Coworker[] = [];

export type PendingMessage = CoworkerMessageRequest & (
  { status: "sending" } | { status: "failed"; error: string }
);

interface Snapshot {
  buildingId: string;
  session: CoworkerSession | null;
  offset: number;
  loading: boolean;
  error: string | null;
  expired: boolean;
  selectedId: string | null;
  drafts: Record<string, string>;
  pending: Record<string, PendingMessage>;
}

interface Scope {
  buildingId: string;
  controller: AbortController;
  session: CoworkerSession | null;
  busy: boolean;
  polling: boolean;
  syncedAt: number;
}

function initialSnapshot(buildingId: string): Snapshot {
  return { buildingId, session: null, offset: 0, loading: true, error: null, expired: false, selectedId: null, drafts: {}, pending: {} };
}

function readStorage(storage: "localStorage" | "sessionStorage", key: string) {
  try { return window[storage].getItem(key); } catch { return null; }
}

function writeStorage(storage: "localStorage" | "sessionStorage", key: string, value: string | null) {
  try {
    if (value === null) window[storage].removeItem(key);
    else window[storage].setItem(key, value);
  } catch { /* The workspace also works when browser storage is blocked. */ }
}

function sessionKey(buildingId: string) {
  return `building-workspace:coworker-session:${encodeURIComponent(buildingId)}`;
}

function errorText(error: unknown) {
  return error instanceof Error ? error.message : "Could not reach AI coworkers.";
}

function isExpired(error: unknown) {
  return error instanceof CoworkerApiError && (error.status === 404 || error.status === 410);
}

/** Owns browser-session isolation, retries and the server's authoritative coworker state. */
export function useCoworkers(buildingId: string, chatOpen: boolean) {
  const [snapshot, setSnapshot] = useState(() => initialSnapshot(buildingId));
  const [show, setShow] = useState(() => readStorage("localStorage", SHOW_KEY) !== "false");
  const [reload, restart] = useReducer((value: number) => value + 1, 0);
  const scopeRef = useRef<Scope | null>(null);
  const current = snapshot.buildingId === buildingId ? snapshot : initialSnapshot(buildingId);

  const apply = useCallback((scope: Scope, session: CoworkerSession) => {
    if (scopeRef.current !== scope || scope.controller.signal.aborted) return;
    if (scope.session && session.sessionId !== scope.session.sessionId) throw new Error("The coworker session changed. Reload the session.");
    if (scope.session && session.serverTime < scope.session.serverTime) return;
    scope.session = session;
    scope.syncedAt = Date.now();
    writeStorage("sessionStorage", sessionKey(scope.buildingId), session.sessionId);
    setSnapshot((previous) => ({
      ...(previous.buildingId === scope.buildingId ? previous : initialSnapshot(scope.buildingId)),
      session, offset: session.serverTime - Date.now(), loading: false, error: null, expired: false,
    }));
  }, []);

  const fail = useCallback((scope: Scope, error: unknown) => {
    if (scopeRef.current !== scope || scope.controller.signal.aborted) return;
    if (isExpired(error)) {
      scope.session = null;
      writeStorage("sessionStorage", sessionKey(scope.buildingId), null);
      setSnapshot({
        ...initialSnapshot(scope.buildingId), loading: false, expired: true,
        error: "This coworker session has expired or is no longer available. Start a new session to chat again.",
      });
      return;
    }
    setSnapshot((previous) => ({ ...previous, loading: false, error: errorText(error) }));
  }, []);

  useEffect(() => {
    const scope: Scope = { buildingId, controller: new AbortController(), session: null, busy: false, polling: false, syncedAt: 0 };
    scopeRef.current = scope;
    setSnapshot((previous) => previous.buildingId === buildingId
      ? { ...previous, loading: true, error: null, expired: false }
      : initialSnapshot(buildingId));
    const stored = readStorage("sessionStorage", sessionKey(buildingId));
    const load = async () => {
      // React's development checks can discard an effect before its first request.
      await Promise.resolve();
      if (scope.controller.signal.aborted) return;
      const session = stored
        ? await loadCoworkerSession({ buildingId, sessionId: stored, signal: scope.controller.signal })
        : await createCoworkerSession(buildingId, scope.controller.signal);
      if (stored && session.sessionId !== stored) throw new Error("The server returned a different coworker session.");
      apply(scope, session);
    };
    void load().catch((error: unknown) => {
      if (stored && error instanceof CoworkerApiError && error.status === 422) {
        fail(scope, new CoworkerApiError("The stored session is invalid.", 410));
      } else fail(scope, error);
    });
    return () => {
      scope.controller.abort();
      if (scopeRef.current === scope) scopeRef.current = null;
    };
  }, [buildingId, reload, apply, fail]);

  useEffect(() => {
    if ((!show && !chatOpen) || !current.session || current.expired) return;
    const poll = async () => {
      const scope = scopeRef.current;
      if (!scope?.session || scope.buildingId !== buildingId || scope.busy || scope.polling || document.visibilityState === "hidden") return;
      scope.polling = true;
      try {
        const session = await loadCoworkerSession({ buildingId, sessionId: scope.session.sessionId, signal: scope.controller.signal });
        // A send that started during this read owns the newer state.
        if (!scope.busy) apply(scope, session);
      } catch (error) { if (!scope.busy) fail(scope, error); }
      finally { scope.polling = false; }
    };
    if (scopeRef.current && Date.now() - scopeRef.current.syncedAt >= POLL_MS) void poll();
    const timer = window.setInterval(() => void poll(), POLL_MS);
    const onVisible = () => { if (document.visibilityState !== "hidden") void poll(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [buildingId, show, chatOpen, current.session?.sessionId, current.expired, apply, fail]);

  const transmit = async (message: CoworkerMessageRequest) => {
    const scope = scopeRef.current;
    if (!scope?.session || scope.buildingId !== buildingId || scope.busy) return;
    scope.busy = true;
    setSnapshot((previous) => ({
      ...previous, drafts: { ...previous.drafts, [message.memberId]: "" },
      pending: { ...previous.pending, [message.memberId]: { ...message, status: "sending" } },
    }));
    try {
      const session = await sendCoworkerMessage({ buildingId, sessionId: scope.session.sessionId, signal: scope.controller.signal }, message);
      apply(scope, session);
      if (scopeRef.current !== scope || scope.controller.signal.aborted) return;
      setSnapshot((previous) => {
        const pending = { ...previous.pending };
        delete pending[message.memberId];
        return { ...previous, pending };
      });
    } catch (error) {
      if (scopeRef.current !== scope || scope.controller.signal.aborted) return;
      if (isExpired(error)) { fail(scope, error); return; }
      setSnapshot((previous) => ({ ...previous, pending: {
        ...previous.pending, [message.memberId]: { ...message, status: "failed", error: errorText(error) },
      } }));
    } finally { scope.busy = false; }
  };

  const members = current.session?.members ?? FALLBACK_MEMBERS;
  const selected = members.find((member) => member.id === current.selectedId);
  const setDraft = (text: string) => {
    if (!selected) return;
    setSnapshot((previous) => ({ ...previous, drafts: { ...previous.drafts, [selected.id]: text } }));
  };
  const send = () => {
    if (!selected || !current.session?.chatAvailable || current.pending[selected.id]) return;
    const text = current.drafts[selected.id]?.trim();
    if (text) void transmit({ memberId: selected.id, text, requestId: crypto.randomUUID() });
  };
  const retry = () => {
    const pending = selected && current.pending[selected.id];
    if (pending?.status === "failed") void transmit(pending);
  };
  const select = useCallback((id: string) => setSnapshot((previous) => ({ ...previous, selectedId: id })), []);
  const markers = useCoworkerMarkers(current.session?.members ?? NO_MEMBERS, show, current.offset);

  return {
    members, selected, selectedCoworker: current.session?.members.find((member) => member.id === selected?.id), markers, show,
    setShow: (value: boolean) => { setShow(value); writeStorage("localStorage", SHOW_KEY, String(value)); },
    select,
    messages: current.session?.messages.filter((message) => message.memberId === selected?.id) ?? [],
    draft: selected ? current.drafts[selected.id] ?? "" : "", setDraft, send, retry,
    pending: selected ? current.pending[selected.id] : undefined,
    busy: Object.values(current.pending).some((message) => message.status === "sending"),
    loading: current.loading, error: current.error, expired: current.expired,
    chatAvailable: current.session?.chatAvailable ?? false,
    unavailableReason: current.session?.unavailableReason ?? null,
    reload: restart,
  };
}

export type CoworkerChat = ReturnType<typeof useCoworkers>;

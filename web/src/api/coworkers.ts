export interface CoworkerPoint {
  floorId: string;
  x: number;
  y: number;
}

export interface Coworker {
  id: string;
  name: string;
  role: string;
  color: string;
  position: CoworkerPoint & { spaceId: string; spaceName: string };
  activity: string;
  journey: null | {
    points: Array<CoworkerPoint & { at: number }>;
    destinationName: string;
    arrivesAt: number;
  };
}

export interface ChatMessage {
  id: string;
  memberId: string;
  role: "user" | "assistant";
  text: string;
  createdAt: number;
}

export interface CoworkerSession {
  sessionId: string;
  serverTime: number;
  members: Coworker[];
  messages: ChatMessage[];
  chatAvailable: boolean;
  unavailableReason: string | null;
  totalCostUsd: number;
}

export interface CoworkerMessageRequest {
  memberId: string;
  text: string;
  requestId: string;
}

export class CoworkerApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

function object(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error("Invalid coworker response.");
  return value as Record<string, unknown>;
}

function string(value: unknown): string {
  if (typeof value !== "string") throw new Error("Invalid coworker response.");
  return value;
}

function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error("Invalid coworker response.");
  return value;
}

function array<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error("Invalid coworker response.");
  return value.map(parse);
}

function point(value: unknown): CoworkerPoint {
  const data = object(value);
  return { floorId: string(data.floorId), x: number(data.x), y: number(data.y) };
}

function member(value: unknown): Coworker {
  const data = object(value);
  const position = object(data.position);
  const journey = data.journey === null ? null : object(data.journey);
  return {
    id: string(data.id), name: string(data.name), role: string(data.role), color: string(data.color),
    position: { ...point(position), spaceId: string(position.spaceId), spaceName: string(position.spaceName) },
    activity: string(data.activity),
    journey: journey && {
      points: array(journey.points, (value) => ({ ...point(value), at: number(object(value).at) })),
      destinationName: string(journey.destinationName), arrivesAt: number(journey.arrivesAt),
    },
  };
}

function message(value: unknown): ChatMessage {
  const data = object(value);
  if (data.role !== "user" && data.role !== "assistant") throw new Error("Invalid coworker response.");
  return {
    id: string(data.id), memberId: string(data.memberId), role: data.role,
    text: string(data.text), createdAt: number(data.createdAt),
  };
}

function session(value: unknown): CoworkerSession {
  const data = object(value);
  if (typeof data.chatAvailable !== "boolean") throw new Error("Invalid coworker response.");
  return {
    sessionId: string(data.sessionId), serverTime: number(data.serverTime),
    members: array(data.members, member), messages: array(data.messages, message),
    chatAvailable: data.chatAvailable,
    unavailableReason: data.unavailableReason === null ? null : string(data.unavailableReason),
    totalCostUsd: number(data.totalCostUsd),
  };
}

function sessionPath(buildingId: string, sessionId?: string) {
  const base = `/api/buildings/${encodeURIComponent(buildingId)}/coworkers/sessions`;
  return sessionId === undefined ? base : `${base}/${encodeURIComponent(sessionId)}`;
}

async function request(path: string, init: RequestInit): Promise<CoworkerSession> {
  const response = await fetch(path, { ...init, cache: "no-store" });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null && "detail" in body ? body.detail : undefined;
    throw new CoworkerApiError(typeof detail === "string" ? detail : `Request failed (${response.status}).`, response.status);
  }
  return session(body);
}

export function createCoworkerSession(buildingId: string, signal: AbortSignal) {
  return request(sessionPath(buildingId), { method: "POST", signal });
}

export function loadCoworkerSession(scope: { buildingId: string; sessionId: string; signal: AbortSignal }) {
  return request(sessionPath(scope.buildingId, scope.sessionId), { signal: scope.signal });
}

export function sendCoworkerMessage(
  scope: { buildingId: string; sessionId: string; signal: AbortSignal },
  body: CoworkerMessageRequest,
) {
  return request(`${sessionPath(scope.buildingId, scope.sessionId)}/messages`, {
    method: "POST", signal: scope.signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ memberId: body.memberId, text: body.text, requestId: body.requestId }),
  });
}

import type { BuildingSummary, ChatReply, Device, Marker, Position, Role, Session, Snapshot, StopStatus, ToolResponse, Tour } from './types';

/** `?mock=1` serves the bundled fixtures from `src/mocks/` instead of the live API (CONTRACTS §15). */
export const mockMode = typeof location !== 'undefined' && new URLSearchParams(location.search).get('mock') === '1';

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string) { super(message); }
}

export type Transport = (method: string, path: string, body?: unknown) => Promise<unknown>;

const http: Transport = async (method, path, body) => {
  const response = await fetch(path, { method, headers: body === undefined ? undefined : { 'content-type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (data as { error?: { code?: string; message?: string }; detail?: unknown } | null);
    throw new ApiError(response.status, error?.error?.code ?? 'internal', error?.error?.message ?? (typeof error?.detail === 'string' ? error.detail : `${method} ${path} failed with ${response.status}`));
  }
  return data;
};

let mockTransport: Promise<Transport> | null = null;
const send = async <T>(method: string, path: string, body?: unknown): Promise<T> => {
  if (!mockMode) return await http(method, path, body) as T;
  mockTransport ??= import('../mocks').then(module => module.mockTransport);
  return await (await mockTransport)(method, path, body) as T;
};

export const api = {
  buildings: () => send<BuildingSummary[]>('GET', '/api/buildings'),
  building: (id: string, version?: number) => send<Snapshot>('GET', `/api/buildings/${encodeURIComponent(id)}${version === undefined ? '' : `?version=${version}`}`),
  createSession: (body: { building_id: string; device: Device; role: Role; profile?: string }) => send<Session>('POST', '/api/sessions', { profile: 'walk', ...body }),
  session: (id: string) => send<Session>('GET', `/api/sessions/${id}`),
  updateSession: (id: string, patch: { position?: Partial<Position> | null; profile?: string; active_tour_id?: string | null }) => send<Session>('PATCH', `/api/sessions/${id}`, patch),
  planTour: (body: { session_id: string; items: string[]; keep_order: boolean; start?: { space_id: string; point?: [number, number] }; end?: null }) => send<Tour>('POST', '/api/tours', body),
  tour: (id: string) => send<Tour>('GET', `/api/tours/${encodeURIComponent(id)}`),
  progress: (id: string, stop_id: string, status: StopStatus) => send<Tour>('POST', `/api/tours/${encodeURIComponent(id)}/progress`, { stop_id, status }),
  replan: (id: string, body: { session_id: string; from: { space_id: string; point?: [number, number] }; reason: string }) => send<Tour>('POST', `/api/tours/${encodeURIComponent(id)}/replan`, body),
  tool: (name: string, session_id: string, args: Record<string, unknown>) => send<ToolResponse>('POST', `/api/tools/${name}`, { session_id, args }),
  chat: (session_id: string, message: string) => send<ChatReply>('POST', '/api/chat', { session_id, message }),
  marker: (id: string) => send<Marker>('GET', `/api/markers/${encodeURIComponent(id)}`),
};

/** Reuses the stored session for this building and device, or creates one (CONTRACTS §10). */
export async function ensureSession(building_id: string, device: Device, role: Role = 'navigator'): Promise<Session> {
  const key = `tyb.session.${building_id}.${device}.${role}${mockMode ? '.mock' : ''}`;
  let stored: string | null = null;
  try { stored = localStorage.getItem(key); } catch { /* storage blocked: a fresh session per load */ }
  if (stored) {
    try {
      const session = await api.session(stored);
      if (session.building_id === building_id) return session;
    } catch { /* expired or unknown: create a new one */ }
  }
  const session = await api.createSession({ building_id, device, role });
  try { localStorage.setItem(key, session.session_id); } catch { /* ignore */ }
  return session;
}

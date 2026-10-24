import type { BuildingEventRecord, BuildingSummary, TeamSummary, TeamBuildingResult, Constraints, Validation, ChatReply, Device, Marker, MobilityProfile, Position, Role, Session, Snapshot, StopStatus, ToolResponse, Tour } from './types';
import { forgetAdminCode, readAdminCode } from './adminAccess';

/** `?mock=1` serves the bundled fixtures from `src/mocks/` instead of the live API (CONTRACTS §15). */
export const mockMode = typeof location !== 'undefined' && new URLSearchParams(location.search).get('mock') === '1';

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string, readonly data?: unknown) { super(message); }
}

export type Transport = (method: string, path: string, body?: unknown, headers?: Record<string, string>) => Promise<unknown>;

const http: Transport = async (method, path, body, headers) => {
  const response = await fetch(path, { method, headers: { ...(body === undefined ? {} : { 'content-type': 'application/json' }), ...headers }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (data as { error?: { code?: string; message?: string }; detail?: unknown } | null);
    throw new ApiError(response.status, error?.error?.code ?? 'internal', error?.error?.message ?? (typeof error?.detail === 'string' ? error.detail : `${method} ${path} failed with ${response.status}`), error?.error);
  }
  return data;
};

let mockTransport: Promise<Transport> | null = null;
const send = async <T>(method: string, path: string, body?: unknown, headers?: Record<string, string>): Promise<T> => {
  if (!mockMode) return await http(method, path, body, headers) as T;
  mockTransport ??= import('../mocks').then(module => module.mockTransport);
  return await (await mockTransport)(method, path, body, headers) as T;
};

export const api = {
  teams: () => send<TeamSummary[]>('GET', '/api/teams'),
  teamBuildings: (teamId: string) => send<BuildingSummary[]>('GET', `/api/teams/${encodeURIComponent(teamId)}/buildings`),
  createTeamBuilding: (teamId: string, floorPlan: Record<string, unknown>, equipmentCsv: string, code: string) => send<TeamBuildingResult>('POST', `/api/teams/${encodeURIComponent(teamId)}/buildings`, { floor_plan: floorPlan, equipment_csv: equipmentCsv }, { 'X-Admin-Token': code }),
  buildings: () => send<BuildingSummary[]>('GET', '/api/buildings'),
  building: (id: string, version?: number) => send<Snapshot>('GET', `/api/buildings/${encodeURIComponent(id)}${version === undefined ? '' : `?version=${version}`}`),
  createSession: (body: { building_id: string; device: Device; role: Role; profile?: MobilityProfile }, adminCode?: string) => send<Session>('POST', '/api/sessions', { profile: 'walk', ...body }, body.role === 'admin' && adminCode ? { 'X-Admin-Token': adminCode } : undefined),
  session: (id: string) => send<Session>('GET', `/api/sessions/${id}`),
  updateSession: (id: string, patch: { position?: Position | null; profile?: MobilityProfile; constraints?: Partial<Constraints>; active_tour_id?: string | null }) => send<Session>('PATCH', `/api/sessions/${id}`, patch),
  planTour: (body: { session_id: string; items: string[]; keep_order: boolean; start?: { space_id: string; point?: [number, number] }; end?: string | null }) => send<Tour>('POST', '/api/tours', body),
  tour: (id: string) => send<Tour>('GET', `/api/tours/${encodeURIComponent(id)}`),
  /** `X-Session-ID` lets "Got it" advance the phone session's position (CONTRACTS C2). */
  progress: (id: string, stop_id: string, status: StopStatus, sessionId?: string) => send<Tour>('POST', `/api/tours/${encodeURIComponent(id)}/progress`, { stop_id, status }, sessionId ? { 'X-Session-ID': sessionId } : undefined),
  replan: (id: string, body: { session_id: string; from: Position; reason: string; constraints?: Partial<Constraints> }) => send<Tour>('POST', `/api/tours/${encodeURIComponent(id)}/replan`, body),
  tool: (name: string, session_id: string, args: Record<string, unknown>) => send<ToolResponse>('POST', `/api/tools/${name}`, { session_id, args }),
  chat: (session_id: string, message: string) => send<ChatReply>('POST', '/api/chat', { session_id, message }),
  marker: (id: string) => send<Marker>('GET', `/api/markers/${encodeURIComponent(id)}`),
  /** Admin upload of a kit-format building.json; the server validates it with the core validator. */
  uploadBuilding: (raw: unknown, adminSessionId: string) => send<{ building_id: string; validation: Validation }>('POST', '/api/buildings', raw, { 'X-Session-ID': adminSessionId }),
  events: (buildingId: string) => send<BuildingEventRecord[]>('GET', `/api/buildings/${encodeURIComponent(buildingId)}/events`),
  /** Demo mode only (TYB_DEMO_MODE on the server); admin session in `X-Session-ID`. */
  demoReset: (buildingId: string, adminSessionId: string) => send<{ building_id: string; building_version: number }>('POST', '/api/demo/reset', { building_id: buildingId }, { 'X-Session-ID': adminSessionId }),
};

const sessionKey = (buildingId: string, device: Device, role: Role) => `tyb.session.${buildingId}.${device}.${role}${mockMode ? '.mock' : ''}`;

export function clearAdminSession(buildingId: string, device: Device = 'desk'): void {
  const key = sessionKey(buildingId, device, 'admin');
  forgetAdminCode();
  try { sessionStorage.removeItem(key); } catch { /* ignore */ }
  try { localStorage.removeItem(key); } catch { /* remove legacy privileged identity */ }
}

/** Navigator sessions persist; privileged sessions and codes last only in this tab. */
export async function ensureSession(building_id: string, device: Device, role: Role = 'navigator', adminCode?: string): Promise<Session> {
  const key = sessionKey(building_id, device, role);
  if (role === 'admin') { try { localStorage.removeItem(key); } catch { /* remove pre-auth privileged identities */ } }
  const credential = role === 'admin' ? adminCode ?? readAdminCode() ?? undefined : undefined;
  if (role === 'admin' && !credential?.trim()) throw new ApiError(403, 'forbidden', 'Enter the admin access code to continue.');
  let storage: Storage | null = null;
  try { storage = role === 'admin' ? sessionStorage : localStorage; } catch { /* storage blocked */ }
  let stored: string | null = null;
  try { stored = storage?.getItem(key) ?? null; } catch { /* a fresh session per load */ }
  if (stored) {
    try {
      const session = await api.session(stored);
      if (session.building_id === building_id && session.role === role && session.device === device) return session;
    } catch (error) {
      if (role === 'admin' && error instanceof ApiError && error.status === 403) {
        clearAdminSession(building_id, device);
        throw error; // revoked or rotated access requires a fresh human entry
      }
    }
    try { storage?.removeItem(key); } catch { /* ignore */ }
  }
  let session: Session;
  try { session = await api.createSession({ building_id, device, role }, credential); }
  catch (error) {
    if (role === 'admin' && error instanceof ApiError && error.status === 403) clearAdminSession(building_id, device);
    throw error;
  }
  try { storage?.setItem(key, session.session_id); } catch { /* ignore */ }
  return session;
}

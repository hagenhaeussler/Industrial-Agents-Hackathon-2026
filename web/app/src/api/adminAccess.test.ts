import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { ApiError, api, clearAdminSession, ensureSession } from './client';
import { readAdminCode, rememberAdminCode } from './adminAccess';
import type { Session } from './types';

class MemoryStorage implements Storage {
  values = new Map<string, string>();
  get length() { return this.values.size; }
  clear() { this.values.clear(); }
  getItem(key: string) { return this.values.get(key) ?? null; }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
  removeItem(key: string) { this.values.delete(key); }
  setItem(key: string, value: string) { this.values.set(key, String(value)); }
}

const session = (role: 'admin' | 'navigator' = 'admin'): Session => ({
  session_id: `${role}-test-session`, building_id: 'building-test', device: 'desk', role, profile: 'walk',
  position: null, active_tour_id: null,
  constraints: { step_free: false, closed: [], min_door_width_m: 0, no_transit_room_types: [] },
});
let previousFetch: typeof fetch;
let localDescriptor: PropertyDescriptor | undefined;
let sessionDescriptor: PropertyDescriptor | undefined;

beforeEach(() => {
  previousFetch = globalThis.fetch;
  localDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  sessionDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage');
  Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true });
  Object.defineProperty(globalThis, 'sessionStorage', { value: new MemoryStorage(), configurable: true });
});
afterEach(() => {
  globalThis.fetch = previousFetch;
  if (localDescriptor) Object.defineProperty(globalThis, 'localStorage', localDescriptor);
  else Reflect.deleteProperty(globalThis, 'localStorage');
  if (sessionDescriptor) Object.defineProperty(globalThis, 'sessionStorage', sessionDescriptor);
  else Reflect.deleteProperty(globalThis, 'sessionStorage');
});

describe('explicit admin access', () => {
  test('does not mint an admin session without a human-entered or tab-stored code', async () => {
    let calls = 0;
    globalThis.fetch = (async () => { calls += 1; return Response.json(session()); }) as unknown as typeof fetch;
    await expect(ensureSession('building-test', 'desk', 'admin')).rejects.toMatchObject({ status: 403, code: 'forbidden' });
    expect(calls).toBe(0);
  });

  test('sends the code only in the admin creation header, never in JSON or navigator calls', async () => {
    const requests: { path: string; headers: Headers; body: Record<string, unknown> }[] = [];
    globalThis.fetch = (async (input, init) => {
      requests.push({ path: String(input), headers: new Headers(init?.headers), body: JSON.parse(String(init?.body)) });
      return Response.json(session(requests.length === 1 ? 'admin' : 'navigator'));
    }) as typeof fetch;
    await api.createSession({ building_id: 'building-test', device: 'desk', role: 'admin' }, 'test-only-admin-code');
    await api.createSession({ building_id: 'building-test', device: 'desk', role: 'navigator' }, 'test-only-admin-code');
    expect(requests[0]!.headers.get('X-Admin-Token')).toBe('test-only-admin-code');
    expect(JSON.stringify(requests[0]!.body)).not.toContain('test-only-admin-code');
    expect(requests[0]!.path).toBe('/api/sessions');
    expect(requests[1]!.headers.has('X-Admin-Token')).toBe(false);
  });

  test('keeps admin code and identity only in sessionStorage; navigator identity still persists', async () => {
    globalThis.fetch = (async (_input, init) => Response.json(session(JSON.parse(String(init?.body)).role))) as typeof fetch;
    localStorage.setItem('tyb.session.building-test.desk.admin', 'legacy-unverified-admin');
    rememberAdminCode('test-only-admin-code');
    await ensureSession('building-test', 'desk', 'admin');
    expect(readAdminCode()).toBe('test-only-admin-code');
    expect(sessionStorage.getItem('tyb.session.building-test.desk.admin')).toBe('admin-test-session');
    expect(localStorage.length).toBe(0);
    await ensureSession('building-test', 'desk');
    expect(localStorage.getItem('tyb.session.building-test.desk.navigator')).toBe('navigator-test-session');
    expect(JSON.stringify([...((localStorage as MemoryStorage).values.values())])).not.toContain('test-only-admin-code');
    clearAdminSession('building-test');
    expect(readAdminCode()).toBeNull();
    expect(sessionStorage.getItem('tyb.session.building-test.desk.admin')).toBeNull();
    expect(localStorage.getItem('tyb.session.building-test.desk.navigator')).toBe('navigator-test-session');
  });

  test('a revoked cached admin GET 403 clears access and requires re-entry without reminting', async () => {
    rememberAdminCode('revoked-test-code');
    sessionStorage.setItem('tyb.session.building-test.desk.admin', 'revoked-session');
    let calls = 0;
    globalThis.fetch = (async (input, init) => {
      calls += 1;
      expect(String(input)).toBe('/api/sessions/revoked-session');
      expect(init?.method).toBe('GET');
      expect(new Headers(init?.headers).has('X-Admin-Token')).toBe(false);
      return Response.json({ error: { code: 'forbidden', message: 'Admin access is no longer valid.' } }, { status: 403 });
    }) as typeof fetch;
    await expect(ensureSession('building-test', 'desk', 'admin')).rejects.toBeInstanceOf(ApiError);
    expect(calls).toBe(1);
    expect(readAdminCode()).toBeNull();
    expect(sessionStorage.getItem('tyb.session.building-test.desk.admin')).toBeNull();
  });

  test('a denied new code is forgotten and cannot trigger automatic retries', async () => {
    rememberAdminCode('wrong-test-code');
    let calls = 0;
    globalThis.fetch = (async () => { calls += 1; return Response.json({ error: { code: 'forbidden', message: 'Invalid admin access code.' } }, { status: 403 }); }) as unknown as typeof fetch;
    await expect(ensureSession('building-test', 'desk', 'admin')).rejects.toMatchObject({ status: 403 });
    expect(readAdminCode()).toBeNull();
    await expect(ensureSession('building-test', 'desk', 'admin')).rejects.toMatchObject({ status: 403 });
    expect(calls).toBe(1);
  });
});

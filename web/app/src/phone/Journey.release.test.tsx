import { afterEach, beforeAll, beforeEach, describe, expect, mock, test } from 'bun:test';
import { Window } from 'happy-dom';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import type { ComponentType, ReactNode } from 'react';
import { ApiError, api } from '../api/client';
import type { Position, Session, Snapshot, Tour } from '../api/types';
import snapshotJson from '../mocks/data/building_proc-factory-dev-003.json';
import payloads from './fixtures/final-destination-c7.json';

// Keep the real Journey state and request handlers; replace visual/device
// integrations so HTTP rejection and cold-load behavior can be tested offline.
const voice = { available: false, status: 'disconnected', isSpeaking: false, error: null,
  start: async () => undefined, stop: async () => undefined, sendContext: () => undefined };
mock.module('./voice', () => ({ VoiceRoot: ({ children }: { children: ReactNode }) => children, useVoiceSession: () => voice }));
mock.module('../api/ws', () => ({ useBuildingSocket: () => 'live' }));
mock.module('../map/MapView', () => ({ MapView: () => <div data-testid="route-map"/> }));
mock.module('@blobatar/react', () => ({ Blobatar: () => <span aria-hidden="true"/> }));

let Journey: ComponentType<{ tourId: string }>;
const originalApi = { ...api };
let dom: Window;
const finalLeg = payloads.finalLeg as unknown as Tour;
let loaded: Tour;
let snapshot: Snapshot;
let phone: Session;

beforeAll(async () => { Journey = (await import('./Journey')).Journey; });
beforeEach(() => {
  dom = new Window({ url: 'http://localhost/go/release-test' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    localStorage: { value: dom.localStorage, configurable: true }, sessionStorage: { value: dom.sessionStorage, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
  loaded = structuredClone(finalLeg);
  snapshot = structuredClone(snapshotJson) as unknown as Snapshot;
  snapshot.building_version = loaded.building_version;
  phone = { session_id: 'release-phone-session', building_id: loaded.building_id, device: 'phone', role: 'navigator',
    profile: 'walk', constraints: loaded.constraints, position: { ...loaded.start, source: 'manual', confidence: 'medium' }, active_tour_id: loaded.tour_id };
  localStorage.setItem(`tyb.confirmed.${loaded.tour_id}`, '1');
  localStorage.setItem(`tyb.session.${loaded.building_id}.phone.navigator`, phone.session_id);
  api.tour = async () => structuredClone(loaded);
  api.building = async () => structuredClone(snapshot);
  api.session = async () => structuredClone(phone);
  api.updateSession = async (_id, patch) => { phone = { ...phone, ...patch, constraints: { ...phone.constraints, ...patch.constraints } }; return structuredClone(phone); };
  api.events = async () => [];
});
afterEach(() => { cleanup(); Object.assign(api, originalApi); dom.happyDOM.abort(); });

async function openAtArrival() {
  const view = render(<Journey tourId={loaded.tour_id}/>);
  await waitFor(() => expect(view.queryByRole('button', { name: 'Next step' })).not.toBeNull());
  const leg = finalLeg.legs[0];
  if (!leg?.reachable) throw new Error('The release fixture needs a reachable final leg.');
  for (let step = 0; step < leg.maneuvers.length; step += 1) {
    const button = view.queryByRole('button', { name: 'Next step' });
    if (!button) break;
    await act(async () => { fireEvent.click(button); });
  }
  expect(view.queryByRole('button', { name: 'I have arrived' })).not.toBeNull();
  return view;
}

describe('release navigation failures (CR-M-7/8)', () => {
  test.each([400, 404, 422])('rejected final arrival HTTP %i never displays completion', async status => {
    let attempts = 0;
    api.progress = async (_id, stopId, value, sessionId) => {
      attempts += 1;
      expect(stopId).toBe('end'); expect(value).toBe('collected'); expect(sessionId).toBe(phone.session_id);
      throw new ApiError(status, 'no_route', 'The final destination cannot currently be reached.');
    };
    const view = await openAtArrival();
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'I have arrived' })); });
    expect(attempts).toBe(1);
    expect(view.queryByRole('heading', { name: 'Your part is collected' })).toBeNull();
    expect(view.getByRole('alert').textContent).toContain('The final destination cannot currently be reached');
    expect(view.queryByRole('button', { name: 'I have arrived' })).not.toBeNull();
  });

  test('an accepted final arrival displays the server-confirmed completed state', async () => {
    api.progress = async () => structuredClone(payloads.arrived) as unknown as Tour;
    const view = await openAtArrival();
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'I have arrived' })); });
    expect(view.queryByRole('heading', { name: 'Your part is collected' })).not.toBeNull();
    expect(view.queryByRole('button', { name: 'I have arrived' })).toBeNull();
  });

  test('cold-opening an all-collected stale final leg replans a newly closed destination', async () => {
    loaded.building_version = 2; snapshot.building_version = 3;
    localStorage.removeItem(`tyb.confirmed.${loaded.tour_id}`);
    const previousRoom = loaded.end!.space_id;
    phone.position = { space_id: previousRoom, source: 'manual', confidence: 'medium' };
    let from: Position | undefined;
    api.replan = async (_id, body) => {
      from = body.from;
      return { ...structuredClone(payloads.blockedEnd) as unknown as Tour, building_version: 3, revision: loaded.revision + 1 };
    };
    const view = render(<Journey tourId={loaded.tour_id}/>);
    await waitFor(() => expect(from).toBeDefined());
    await waitFor(() => expect(view.queryByRole('alert')?.textContent).toContain('can no longer be reached'));
    expect(from!.space_id).toBe(loaded.start.space_id);
    expect(from!.space_id).not.toBe(previousRoom);
    expect(from!.source).toBe('tour_start');
    expect(view.queryByRole('heading', { name: 'Your part is collected' })).toBeNull();
    expect(view.queryByRole('button', { name: 'Next step' })).toBeNull();
  });

  test('cold-opening a stale blocked final destination restores its reopened route', async () => {
    loaded = { ...structuredClone(payloads.blockedEnd) as unknown as Tour, building_version: 2 };
    snapshot.building_version = 3;
    let replans = 0;
    api.replan = async () => {
      replans += 1;
      return { ...structuredClone(payloads.reopenedEnd) as unknown as Tour, building_version: 3, revision: loaded.revision + 1 };
    };
    const view = render(<Journey tourId={loaded.tour_id}/>);
    await waitFor(() => expect(view.queryByRole('button', { name: 'Next step' })).not.toBeNull());
    expect(replans).toBe(1);
    expect(view.queryByRole('heading', { name: 'Your part is collected' })).toBeNull();
  });
});

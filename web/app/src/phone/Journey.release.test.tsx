import { afterEach, beforeAll, beforeEach, describe, expect, mock, test } from 'bun:test';
import { Window } from 'happy-dom';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import type { ComponentType, ReactNode } from 'react';
import { ApiError, api } from '../api/client';
import type { Display, Position, ReachableRoute, ServerMessage, Session, Snapshot, Tour } from '../api/types';
import snapshotJson from '../mocks/data/building_proc-factory-dev-003.json';
import payloads from './fixtures/final-destination-c7.json';
import scenarioJson from '../../../../demo/scenario.json';

// Keep the real Journey state and request handlers; replace visual/device
// integrations so HTTP rejection and cold-load behavior can be tested offline.
const voice = { available: false, status: 'disconnected', isSpeaking: false, error: null as string | null,
  start: async () => undefined, stop: async () => undefined, sendContext: () => undefined };
let emitDisplay: (display: Display) => void = () => undefined;
mock.module('./voice', () => ({ VoiceRoot: ({ children }: { children: ReactNode }) => children, useVoiceSession: (_id: string | null, handler: (display: Display) => void) => { emitDisplay = handler; return voice; }, VoiceButton: () => null }));
let socketMessage: (event: ServerMessage) => void = () => undefined;
let socketReconnect: () => void = () => undefined;
mock.module('../api/ws', () => ({ useBuildingSocket: (_id: string | null, onMessage: typeof socketMessage, onReconnect: typeof socketReconnect) => { socketMessage = onMessage; socketReconnect = onReconnect; return 'live'; } }));
mock.module('../map/MapView', () => ({ MapView: ({ route, tour, highlightSpaceIds }: { route?: ReachableRoute | null; tour?: Tour | null; highlightSpaceIds?: string[] }) => <div data-testid="route-map" data-route-target={route?.to_space_id} data-tour-id={tour?.tour_id} data-highlights={highlightSpaceIds?.join(',')}/> }));
mock.module('@blobatar/react', () => ({ Blobatar: () => <span aria-hidden="true"/> }));
mock.module('../demo/scenario', () => ({ scenario: scenarioJson }));

let Journey: ComponentType<{ tourId: string }>;
let Desk: ComponentType;
const originalApi = { ...api };
let dom: Window;
const finalLeg = payloads.finalLeg as unknown as Tour;
let loaded: Tour;
let snapshot: Snapshot;
let phone: Session;

beforeAll(async () => { Journey = (await import('./Journey')).Journey; Desk = (await import('../desk/Desk')).Desk; });
beforeEach(() => {
  voice.available = false; voice.status = 'disconnected'; voice.error = null;
  dom = new Window({ url: 'http://localhost/go/release-test' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    location: { value: dom.location, configurable: true }, history: { value: dom.history, configurable: true },
    requestAnimationFrame: { value: (callback: FrameRequestCallback) => setTimeout(() => callback(0), 0), configurable: true },
    cancelAnimationFrame: { value: (id: number) => clearTimeout(id), configurable: true },
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
  api.createSession = async body => ({ ...structuredClone(phone), ...body, session_id: `${body.device}-display-session` });
});

describe('actual screen shared text/voice display handlers', () => {
  const routeForSnapshot = () => ({ ...structuredClone(finalLeg.legs[0]) as ReachableRoute, building_version: snapshot.building_version, content_hash: snapshot.content_hash });

  test('the desk renders standalone route geometry', async () => {
    const route = routeForSnapshot();
    const screen = render(<Desk/>);
    await waitFor(() => expect(screen.queryByTestId('route-map')).not.toBeNull());
    await act(async () => { emitDisplay({ kind: 'route', route }); });
    expect(screen.getByTestId('route-map').getAttribute('data-route-target')).toBe(route.to_space_id);
    expect(screen.getByRole('region', { name: 'Requested route' }).textContent).toContain('Back to building');
  });

  test('the desk highlights all spatial-query rooms instead of ignoring space_ids', async () => {
    const ids = snapshot.building.spaces.slice(0, 2).map(space => space.id);
    const screen = render(<Desk/>);
    await waitFor(() => expect(screen.queryByTestId('route-map')).not.toBeNull());
    await act(async () => { emitDisplay({ kind: 'highlight', space_ids: ids }); });
    expect(screen.getByTestId('route-map').getAttribute('data-highlights')).toBe(ids.join(','));
  });

  test('the phone previews a route without collecting a stop or replacing its active tour', async () => {
    const route = routeForSnapshot();
    let progressCalls = 0;
    api.progress = async () => { progressCalls += 1; return loaded; };
    const screen = render(<Journey tourId={loaded.tour_id}/>);
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Ask the building' })).not.toBeNull());
    await act(async () => { emitDisplay({ kind: 'route', route }); });
    expect(screen.getByTestId('route-map').getAttribute('data-route-target')).toBe(route.to_space_id);
    expect(screen.queryByRole('button', { name: 'Next step' })).toBeNull();
    expect(progressCalls).toBe(0);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Back to collection tour' })); });
    expect(screen.getByTestId('route-map').getAttribute('data-route-target')).toBeNull();
    expect(screen.getByTestId('route-map').getAttribute('data-tour-id')).toBe(loaded.tour_id);
    expect(screen.queryByRole('button', { name: 'Next step' })).not.toBeNull();
    expect(progressCalls).toBe(0);
  });

  test('an asynchronous SDK failure after a voice attempt automatically opens text fallback', async () => {
    voice.available = true;
    const screen = render(<Journey tourId={loaded.tour_id}/>);
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Start voice guidance' })).not.toBeNull());
    expect(screen.queryByRole('dialog', { name: 'Ask the building' })).toBeNull();
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Start voice guidance' })); });
    voice.status = 'error'; voice.error = 'Voice is unavailable. Please use text chat.';
    await act(async () => { screen.rerender(<Journey tourId={loaded.tour_id}/>); });
    expect(screen.queryByRole('dialog', { name: 'Ask the building' })).not.toBeNull();
    expect(screen.queryByRole('button', { name: 'Next step' })).not.toBeNull();
  });
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

describe('C9 reset identity in actual screens', () => {
  for (const scenario of [{ name: 'lower version', old: 3, next: 0 }, { name: 'reused equal version', old: 2, next: 2 }]) {
    for (const target of ['pending part', 'all-collected final leg'] as const) {
      test(`cold open replans ${target} after ${scenario.name}`, async () => {
        loaded = structuredClone(target === 'pending part' ? payloads.before : payloads.finalLeg) as unknown as Tour;
        loaded.building_version = scenario.old; loaded.building_state_id = 'before-reset';
        snapshot.building_version = scenario.next; snapshot.building_state_id = 'after-reset';
        phone = { ...phone, position: { ...loaded.start, source: 'manual', confidence: 'medium' } };
        let from: Position | undefined;
        let finish: ((value: Tour) => void) | undefined;
        api.replan = async (_id, body) => { from = body.from; return new Promise(resolve => { finish = resolve; }); };
        const screen = render(<Journey tourId={loaded.tour_id}/>);
        await waitFor(() => expect(from).toBeDefined());
        // Old directions disappear while the authoritative replan is pending.
        expect(screen.queryByRole('button', { name: 'Next step' })).toBeNull();
        expect(screen.getByTestId('route-map').getAttribute('data-tour-id')).toBeNull();
        expect(from!.space_id).toBe(phone.position!.space_id);
        expect(from!.source).toBe('manual');
        const after = { ...structuredClone(loaded), building_version: scenario.next, building_state_id: 'after-reset', revision: loaded.revision + 1 };
        await act(async () => { finish?.(after); });
        await waitFor(() => expect(screen.getByTestId('route-map').getAttribute('data-tour-id')).toBe(loaded.tour_id));
        expect(screen.queryByRole('heading', { name: 'Your part is collected' })).toBeNull();
        expect(after.stops.map(stop => stop.status)).toEqual(loaded.stops.map(stop => stop.status));
      });
    }

    for (const trigger of ['socket reset', 'reconnect'] as const) {
      test(`${trigger} refreshes an unfinished final leg after ${scenario.name}`, async () => {
        loaded.building_version = scenario.old; loaded.building_state_id = 'before-reset';
        snapshot.building_version = scenario.old; snapshot.building_state_id = 'before-reset';
        let replans = 0;
        api.replan = async (_id, body) => {
          replans += 1;
          expect(body.from.source).toBe('manual');
          return { ...structuredClone(loaded), revision: loaded.revision + 1, building_version: snapshot.building_version, building_state_id: snapshot.building_state_id };
        };
        const screen = render(<Journey tourId={loaded.tour_id}/>);
        await waitFor(() => expect(screen.queryByRole('button', { name: 'Next step' })).not.toBeNull());
        expect(replans).toBe(0);
        snapshot = { ...snapshot, building_version: scenario.next, building_state_id: 'after-reset' };
        await act(async () => { if (trigger === 'socket reset') socketMessage({ type: 'building_reset', building_id: loaded.building_id, building_version: 0 }); else socketReconnect(); });
        await waitFor(() => expect(replans).toBe(1));
        await waitFor(() => expect(screen.getByTestId('route-map').getAttribute('data-tour-id')).toBe(loaded.tour_id));
        expect(screen.queryByRole('heading', { name: 'Your part is collected' })).toBeNull();
      });
    }
  }

  test('desk equal-version reset discards the old preview and accepts only the new state identity', async () => {
    snapshot.building_state_id = 'before-reset';
    const route = { ...structuredClone(finalLeg.legs[0]) as ReachableRoute, building_version: snapshot.building_version, content_hash: snapshot.content_hash, building_state_id: 'before-reset' };
    const screen = render(<Desk/>);
    await waitFor(() => expect(screen.queryByTestId('route-map')).not.toBeNull());
    await act(async () => { emitDisplay({ kind: 'route', route }); });
    expect(screen.queryByRole('region', { name: 'Requested route' })).not.toBeNull();
    let reads = 0;
    snapshot = { ...snapshot, building_state_id: 'after-reset' };
    api.building = async () => { reads += 1; return structuredClone(snapshot); };
    await act(async () => { socketMessage({ type: 'building_reset', building_id: loaded.building_id, building_version: snapshot.building_version }); });
    await waitFor(() => expect(reads).toBe(1));
    expect(screen.queryByRole('region', { name: 'Requested route' })).toBeNull();
    await act(async () => { emitDisplay({ kind: 'route', route }); });
    expect(screen.queryByRole('region', { name: 'Requested route' })).toBeNull();
    await act(async () => { emitDisplay({ kind: 'route', route: { ...route, building_state_id: 'after-reset' } }); });
    expect(screen.queryByRole('region', { name: 'Requested route' })).not.toBeNull();
  });

  test('desk removes a stale tour after equal-version reset and refuses a late old-state refresh', async () => {
    loaded = structuredClone(payloads.before) as unknown as Tour;
    loaded.building_state_id = 'before-reset'; snapshot.building_state_id = 'before-reset';
    const screen = render(<Desk/>);
    await waitFor(() => expect(screen.queryByTestId('route-map')).not.toBeNull());
    await act(async () => { emitDisplay({ kind: 'tour', tour_id: loaded.tour_id }); });
    await waitFor(() => expect(screen.container.querySelector('#tour-title')).not.toBeNull());
    snapshot = { ...snapshot, building_state_id: 'after-reset' };
    await act(async () => { socketMessage({ type: 'building_reset', building_id: loaded.building_id, building_version: snapshot.building_version }); });
    await waitFor(() => expect(screen.container.querySelector('#tour-title')).toBeNull());
    await act(async () => { emitDisplay({ kind: 'tour', tour_id: loaded.tour_id }); });
    expect(screen.container.querySelector('#tour-title')).toBeNull();
    expect(screen.queryByText('The building changed. Plan your selection again using the latest map.')).not.toBeNull();
  });
});

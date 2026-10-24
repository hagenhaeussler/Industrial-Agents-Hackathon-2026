import { afterEach, beforeAll, beforeEach, describe, expect, mock, test } from 'bun:test';
import { Window } from 'happy-dom';
import type { ComponentType, ReactNode } from 'react';
import { ApiError, api } from '../api/client';
import type { Session, Snapshot } from '../api/types';
import snapshotJson from '../mocks/data/building_proc-factory-dev-003.json';
import scenarioJson from '../../../../demo/scenario.json';

// Keep the screen's chat, session and selection behavior. Device and map integrations are separate tests.
mock.module('../phone/voice', () => ({
  VoiceRoot: ({ children }: { children: ReactNode }) => children,
  useVoiceSession: () => ({ available: false }),
  VoiceButton: () => null,
}));
mock.module('../api/ws', () => ({ useBuildingSocket: () => 'live' }));
mock.module('../map/MapView', () => ({ MapView: () => <div aria-label="Building map test fixture"/> }));
mock.module('../demo/scenario', () => ({ scenario: scenarioJson }));

let Desk: ComponentType;
let dom: Window;
const originalApi = { ...api };
const snapshot = snapshotJson as unknown as Snapshot;
const session: Session = {
  session_id: 'desk-chat-session', building_id: snapshot.building.building.id, device: 'desk', role: 'navigator', profile: 'walk',
  constraints: { step_free: false, min_door_width_m: 0, closed: [], no_transit_room_types: [] },
  position: { space_id: snapshot.building.spaces[0]!.id, source: 'desk', confidence: 'medium' }, active_tour_id: null,
};

function initializeDom() {
  dom = new Window({ url: `http://localhost/desk?building=${session.building_id}` });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    HTMLInputElement: { value: dom.HTMLInputElement, configurable: true },
    location: { value: dom.location, configurable: true }, history: { value: dom.history, configurable: true },
    localStorage: { value: dom.localStorage, configurable: true }, sessionStorage: { value: dom.sessionStorage, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true, writable: true },
  });
}

// React's input event support must be detected with a document already present.
initializeDom();
const { act, cleanup, fireEvent, render, waitFor } = await import('@testing-library/react');
function enterText(input: HTMLElement, value: string) {
  // Other suites can load ReactDOM before a document exists, selecting its legacy input path.
  Object.assign(input, { attachEvent: () => undefined, detachEvent: () => undefined });
  fireEvent.focusIn(input);
  fireEvent.change(input, { target: { value } });
  fireEvent.keyUp(input, { key: 'a' });
}

beforeAll(async () => { Desk = (await import('./Desk')).Desk; });
beforeEach(() => {
  initializeDom();
  api.building = async () => structuredClone(snapshot);
  api.createSession = async () => structuredClone(session);
  api.session = async () => structuredClone(session);
});
afterEach(() => { cleanup(); Object.assign(api, originalApi); dom.happyDOM.abort(); });

async function openChat() {
  const view = render(<Desk/>);
  await waitFor(() => expect(view.getByRole('button', { name: /Change/ }).hasAttribute('disabled')).toBe(false));
  const input = view.getByRole('textbox', { name: 'What do you need?' });
  if (!(input instanceof HTMLInputElement)) throw new Error('Expected the chat input');
  return { view, input, submit: () => {
    if (!input.form) throw new Error('Expected the chat form');
    fireEvent.submit(input.form);
  } };
}

describe('Desk live chat failures', () => {
  test.each(['unavailable', 'incomplete', 'superseded'] as const)('retains the request when the server reports %s', async status => {
    api.chat = async () => ({ reply: 'The agent could not finish.', status, tool_calls: [], display: null });
    const { view, input, submit } = await openChat();
    await act(async () => { enterText(input, 'Find the nearest printer without stairs'); });
    await act(async () => { submit(); });
    await waitFor(() => expect(view.queryByText('The agent could not finish.')).not.toBeNull());
    expect(input.value).toBe('Find the nearest printer without stairs');
    expect(view.getByRole('button', { name: 'Ask' }).hasAttribute('disabled')).toBe(false);
  });

  test.each([404, 501, 503, 500, 'offline'] as const)('keeps a failed %s request for retry and sends the retry to the server', async failure => {
    const requests: string[] = [];
    api.chat = async (sessionId, text) => {
      expect(sessionId).toBe(session.session_id);
      requests.push(text);
      if (requests.length === 1) {
        if (failure === 'offline') throw new Error('The server could not be reached.');
        throw new ApiError(failure, 'not_available', 'Chat is unavailable.');
      }
      return { reply: 'Server reply after retry.', tool_calls: [], display: null };
    };
    const { view, input, submit } = await openChat();
    const request = 'Where is the 3D printer H-A3-A?';
    await act(async () => { enterText(input, request); });
    expect(view.getByRole('button', { name: 'Ask' }).hasAttribute('disabled')).toBe(false);
    await act(async () => { submit(); });
    await waitFor(() => expect(view.queryByText(/Chat failed:/)).not.toBeNull());
    expect(input.value).toBe(request);
    expect(view.queryByRole('button', { name: 'Select parts to plan a tour' })).not.toBeNull();
    expect(view.queryByText(/searched the parts list/)).toBeNull();
    expect(view.queryByText('Add to tour', { selector: 'button' })).toBeNull();
    expect(view.getByRole('button', { name: 'Ask' }).hasAttribute('disabled')).toBe(false);
    await act(async () => { submit(); });
    await waitFor(() => expect(view.queryByText('Server reply after retry.')).not.toBeNull());
    expect(requests).toEqual([request, request]);
    expect(input.value).toBe('');
    expect(view.queryByText(/Chat failed:/)).toBeNull();
  });
});

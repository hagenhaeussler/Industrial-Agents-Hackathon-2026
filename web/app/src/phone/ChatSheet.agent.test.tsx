import { afterEach, beforeEach, expect, test } from 'bun:test';
import { Window } from 'happy-dom';
import { api, ApiError } from '../api/client';
import { ChatSheet } from './ChatSheet';
import type { ChatReply } from '../api/types';

let dom: Window;
const originalChat = api.chat;
function initializeDom() {
  dom = new Window({ url: 'http://localhost/' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    HTMLInputElement: { value: dom.HTMLInputElement, configurable: true },
    requestAnimationFrame: { value: (callback: FrameRequestCallback) => { callback(0); return 0; }, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true, writable: true },
  });
}
initializeDom();
const { act, cleanup, fireEvent, render, waitFor } = await import('@testing-library/react');
function enterText(input: HTMLElement, value: string) {
  // Other suites can load ReactDOM before a document exists, selecting its legacy input path.
  Object.assign(input, { attachEvent: () => undefined, detachEvent: () => undefined });
  fireEvent.focusIn(input);
  fireEvent.change(input, { target: { value } });
  fireEvent.keyUp(input, { key: 'a' });
}

beforeEach(initializeDom);
afterEach(() => { cleanup(); api.chat = originalChat; dom.happyDOM.abort(); });

test.each(['incomplete', 'unavailable', 'superseded', 'http-error'] as const)('phone chat retains a %s request', async status => {
  api.chat = async () => {
    if (status === 'http-error') throw new ApiError(503, 'not_available', 'Unavailable');
    return { reply: 'The agent could not finish.', status, tool_calls: [], display: null };
  };
  const view = render(<ChatSheet open={false} sessionId="session" onClose={() => {}}/>);
  const input = view.getByLabelText('Message');
  enterText(input, 'Find a printer without stairs');
  await act(async () => { fireEvent.submit(input.closest('form')!); });
  await waitFor(() => expect((input as HTMLInputElement).value).toBe('Find a printer without stairs'));
});

test('a retired phone session cannot display a late agent result', async () => {
  let finish: ((reply: ChatReply) => void) | undefined;
  api.chat = () => new Promise(resolve => { finish = resolve; });
  const displays: unknown[] = [];
  const props = { open: false, onClose: () => {}, onDisplay: (display: unknown) => displays.push(display) };
  const view = render(<ChatSheet {...props} sessionId="old"/>);
  const input = view.getByLabelText('Message');
  enterText(input, 'Go upstairs');
  await act(async () => { fireEvent.submit(input.closest('form')!); });
  view.rerender(<ChatSheet {...props} sessionId="new"/>);
  await act(async () => { finish?.({ reply: 'Old route', tool_calls: [], display: { kind: 'route' } }); });
  expect(view.queryByText('Old route')).toBeNull();
  expect(displays).toEqual([]);
});

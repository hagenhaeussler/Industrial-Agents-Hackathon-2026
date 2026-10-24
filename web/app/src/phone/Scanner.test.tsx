import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { StrictMode } from 'react';
import { act, cleanup, render, waitFor } from '@testing-library/react';
import { Window } from 'happy-dom';
import { Scanner } from './Scanner';

let dom: Window;
beforeEach(() => {
  dom = new Window({ url: 'https://localhost' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
  Object.defineProperty(dom, 'isSecureContext', { value: true });
  Object.defineProperty(dom.HTMLMediaElement.prototype, 'play', { value: async () => undefined, configurable: true });
  Object.defineProperty(dom.HTMLMediaElement.prototype, 'srcObject', { value: null, configurable: true, writable: true });
});
afterEach(() => { cleanup(); dom.happyDOM.abort(); });

describe('scanner camera ownership', () => {
  test('React StrictMode remount starts a new request and stops the stale stream', async () => {
    const resolvers: ((value: unknown) => void)[] = [];
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: () => new Promise(resolve => { resolvers.push(resolve); }) } });
    const screen = render(<StrictMode><Scanner open onMarker={() => undefined} onClose={() => undefined}/></StrictMode>);
    await waitFor(() => expect(resolvers.length).toBe(2));
    const stops = [0, 0];
    await act(async () => {
      resolvers.forEach((resolve, index) => {
        const track = Object.assign(new EventTarget(), { stop: () => { stops[index]! += 1; } });
        resolve({ getTracks: () => [track], getVideoTracks: () => [track] });
      });
    });
    expect(stops).toEqual([1, 0]);
    expect(screen.queryByText('Waiting for camera permission…')).toBeNull();
    screen.unmount(); expect(stops).toEqual([1, 1]);
  });
});

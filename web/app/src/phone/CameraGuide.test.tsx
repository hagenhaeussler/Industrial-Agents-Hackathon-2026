import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { Window } from 'happy-dom';
import type { ReachableRoute, Tour } from '../api/types';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { CameraGuide } from './CameraGuide';

let dom: Window;
const route = (tourJson as unknown as Tour).legs.find((leg): leg is ReachableRoute => leg.reachable)!;
const start = route.maneuvers[0]!;
const anchor = { point: start.at, heading_deg: 0, floor_id: start.floor_id, alphaAtScan: 0 };
let stopped = 0;
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
  stopped = 0;
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => {
    const track = Object.assign(new EventTarget(), { stop: () => { stopped += 1; } });
    return { getTracks: () => [track], getVideoTracks: () => [track] };
  } } });
});
afterEach(() => { cleanup(); dom.happyDOM.abort(); });

const view = (onExit: (message?: string) => void = () => undefined) => render(<CameraGuide leg={route} step={0} position={start.at} floorId={start.floor_id} anchor={anchor} motion={false} onAlpha={() => undefined} onScan={() => undefined} onExit={onExit} minimap={<span>Map</span>}/>);

describe('camera guidance fallbacks', () => {
  test('keeps the direction-only mode and never offers unsupported AR', async () => {
    const screen = view();
    await waitFor(() => expect(screen.queryByText('Waiting for camera permission…')).toBeNull());
    expect(screen.queryByText('Direction only · facing the code direction')).not.toBeNull();
    expect(screen.queryByRole('button', { name: 'Try experimental AR' })).toBeNull();
    screen.unmount(); expect(stopped).toBe(1);
  });

  test('camera denial provides a working return to the map', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => { throw new DOMException('Denied', 'NotAllowedError'); } } });
    let message: string | undefined;
    const screen = view(value => { message = value; });
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Back to the map' })).not.toBeNull());
    fireEvent.click(screen.getByRole('button', { name: 'Back to the map' }));
    expect(message).toContain('Camera access was not allowed');
  });

  test('AR requires a fresh standing/facing confirmation and denial restores the camera', async () => {
    let requests = 0;
    Object.defineProperty(navigator, 'xr', { configurable: true, value: {
      isSessionSupported: async () => true,
      requestSession: () => { requests += 1; return Promise.reject(new Error('Denied')); },
    } });
    const screen = view();
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Try experimental AR' })).not.toBeNull());
    const button = screen.getByRole('button', { name: 'Try experimental AR' });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(requests).toBe(0);
    await act(async () => { fireEvent.click(screen.getByRole('checkbox')); });
    expect((button as HTMLButtonElement).disabled).toBe(false);
    await act(async () => { fireEvent.click(button); expect(requests).toBe(1); });
    await waitFor(() => expect(screen.queryByRole('alert')?.textContent).toContain('AR could not start'));
    expect((screen.getByRole('checkbox') as HTMLInputElement).checked).toBe(false);
    expect(screen.queryByText('Direction only · facing the code direction')).not.toBeNull();
    expect(stopped).toBe(1);
  });
});

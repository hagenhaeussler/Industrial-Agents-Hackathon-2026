import { afterEach, beforeAll, describe, expect, mock, test } from 'bun:test';
import { Window } from 'happy-dom';
import { act, cleanup, renderHook } from '@testing-library/react';
import { useCamera } from './useCamera';

beforeAll(() => {
  const dom = new Window({ url: 'http://localhost' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true },
    document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true },
    HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
  Object.defineProperty(window, 'isSecureContext', { value: true });
});
afterEach(cleanup);

function installCamera(getUserMedia: () => Promise<unknown>) {
  Object.defineProperty(navigator, 'mediaDevices', { value: { getUserMedia }, configurable: true });
}

function createStream() {
  const track = Object.assign(new EventTarget(), { stop: mock(() => undefined) });
  return { track, stream: { getTracks: () => [track], getVideoTracks: () => [track] } };
}

describe('camera lifecycle', () => {
  test('reports denied permission and allows returning to the demo', async () => {
    installCamera(async () => { throw new DOMException('Denied', 'NotAllowedError'); });
    const { result } = renderHook(useCamera);
    await act(async () => { await result.current.start(); });
    expect(result.current.state.kind).toBe('error');
    if (result.current.state.kind === 'error') expect(result.current.state.message).toContain('not allowed');
    act(() => result.current.stop());
    expect(result.current.state.kind).toBe('off');
  });

  test('stops active tracks on stop and unmount', async () => {
    const { stream, track } = createStream();
    installCamera(async () => stream);
    const { result, unmount } = renderHook(useCamera);
    await act(async () => { await result.current.start(); });
    expect(result.current.state.kind).toBe('live');
    act(() => result.current.stop());
    expect(track.stop).toHaveBeenCalledTimes(1);
    await act(async () => { await result.current.start(); });
    unmount();
    expect(track.stop).toHaveBeenCalledTimes(2);
  });

  test('discards a late stream after a pending request is cancelled', async () => {
    const { stream, track } = createStream();
    const pending: { resolve?: (value: typeof stream) => void } = {};
    installCamera(() => new Promise(resolve => { pending.resolve = resolve; }));
    const { result } = renderHook(useCamera);
    let completion: Promise<void> | undefined;
    act(() => { completion = result.current.start(); });
    expect(result.current.state.kind).toBe('requesting');
    act(() => result.current.stop());
    await act(async () => { pending.resolve?.(stream); await completion; });
    expect(result.current.state.kind).toBe('off');
    expect(track.stop).toHaveBeenCalledTimes(1);
  });

  test('reports when an active camera is disconnected', async () => {
    const { stream, track } = createStream();
    installCamera(async () => stream);
    const { result } = renderHook(useCamera);
    await act(async () => { await result.current.start(); });
    act(() => { track.dispatchEvent(new Event('ended')); });
    expect(result.current.state.kind).toBe('error');
    expect(track.stop).toHaveBeenCalledTimes(1);
  });
});

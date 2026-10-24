import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { act, cleanup, fireEvent, render } from '@testing-library/react';
import { Window } from 'happy-dom';
import type { Voice } from '../phone/voice';
import { VoiceConversation } from './VoiceConversation';

let dom: Window;
beforeEach(() => {
  dom = new Window({ url: 'https://localhost' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
});
afterEach(() => { cleanup(); dom.happyDOM.abort(); });

const state = (patch: Partial<Voice> = {}): Voice => ({
  available: true, status: 'disconnected', isSpeaking: false, error: null, messages: [],
  isMuted: false, setMuted: () => undefined, start: async () => undefined, stop: async () => undefined,
  inputLevel: 0, outputLevel: 0, sendContext: () => undefined, sendText: () => false, ...patch,
});

describe('inline voice conversation', () => {
  test('idle rendering never requests the microphone or invents a transcript', () => {
    let starts = 0;
    const screen = render(<VoiceConversation voice={state({ start: async () => { starts += 1; } })}/>);
    expect(screen.container.textContent).toBe('');
    expect(starts).toBe(0);
  });

  test.each([
    [{ status: 'connecting' }, 'Connecting'],
    [{ status: 'connected' }, 'Listening'],
    [{ status: 'connected', isSpeaking: true }, 'Speaking'],
    [{ status: 'connected', isMuted: true }, 'Microphone muted'],
    [{ status: 'connected', isMuted: true, isSpeaking: true }, 'Speaking'],
  ] as [Partial<Voice>, string][])('shows the actual conversation phase %#', (patch, expected) => {
    const screen = render(<VoiceConversation voice={state(patch)}/>);
    expect(screen.getByRole('status').textContent).toBe(expected);
    expect(screen.getByRole('heading', { name: 'Building agent' })).not.toBeNull();
    expect(screen.queryByRole('log')).toBeNull();
  });

  test('renders real user and agent messages as escaped text and retains them after disconnection', () => {
    const messages: Voice['messages'] = [{ id: 'u1', role: 'user', text: 'Find the printer' }, { id: 'a1', role: 'agent', text: 'Floor 2.\n<img src=x onerror=alert(1)>' }];
    const screen = render(<VoiceConversation voice={state({ messages })}/>);
    expect(screen.getByRole('status').textContent).toBe('Conversation ended');
    const log = screen.getByRole('log', { name: 'Messages with the building agent' });
    expect(log.textContent).toContain('YouFind the printer');
    expect(log.textContent).toContain('Building agentFloor 2.');
    expect(log.textContent).toContain('<img src=x onerror=alert(1)>');
    expect(log.querySelector('img')).toBeNull();
    expect(screen.getByRole('button', { name: 'Retry voice' })).not.toBeNull();
  });

  test('retries only from an explicit click and lets the user end a connection attempt', async () => {
    let starts = 0, stops = 0;
    let finish: (() => void) | undefined;
    const voice = state({ error: 'Voice is unavailable. Please use text chat.', start: () => { starts += 1; return new Promise(resolve => { finish = resolve; }); }, stop: async () => { stops += 1; } });
    const screen = render(<VoiceConversation voice={voice}/>);
    expect(starts).toBe(0);
    expect(screen.getByRole('alert').textContent).toBe('Voice is unavailable. Please use text chat.');
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Retry voice' })); });
    expect(starts).toBe(1);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'End conversation' })); finish?.(); });
    expect(stops).toBe(1);
  });

  test('mute and unmute use the existing conversation without starting another one', async () => {
    const calls: boolean[] = [];
    let starts = 0;
    const voice = state({ status: 'connected', setMuted: value => calls.push(value), start: async () => { starts += 1; } });
    const screen = render(<VoiceConversation voice={voice}/>);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Mute microphone' })); });
    expect(calls).toEqual([true]);
    screen.rerender(<VoiceConversation voice={{ ...voice, isMuted: true }}/>);
    expect(screen.getByRole('button', { name: 'Unmute microphone' }).getAttribute('aria-pressed')).toBe('true');
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Unmute microphone' })); });
    expect(calls).toEqual([true, false]); expect(starts).toBe(0);
  });

  test('an action rejection shows a safe error without exposing raw provider details', async () => {
    const screen = render(<VoiceConversation voice={state({ error: null, status: 'error', start: async () => { throw new Error('private provider token detail'); } })}/>);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Retry voice' })); });
    expect(screen.getByRole('alert').textContent).toBe('Voice could not start. You can keep typing and try again.');
    expect(screen.container.textContent).not.toContain('private provider token detail');
  });

  test('a retry started through the orb clears an earlier local action error', async () => {
    const voice = state({ status: 'error', start: async () => { throw new Error('failed retry'); } });
    const screen = render(<VoiceConversation voice={voice}/>);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Retry voice' })); });
    expect(screen.queryByRole('alert')).not.toBeNull();
    screen.rerender(<VoiceConversation voice={{ ...voice, status: 'connecting' }}/>);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByRole('status').textContent).toBe('Connecting');
    screen.rerender(<VoiceConversation voice={{ ...voice, status: 'connected' }}/>);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByRole('status').textContent).toBe('Listening');
  });
});

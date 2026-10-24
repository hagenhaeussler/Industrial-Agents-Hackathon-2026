import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { Window } from 'happy-dom';
import { api } from '../api/client';
import type { ChatReply, Display } from '../api/types';
import { ChatSheet } from './ChatSheet';
import type { Voice } from './voice';

let dom: Window;
const originalChat = api.chat;
const connectedVoice = (): Voice => ({
  available: true, status: 'connected', isSpeaking: false, error: null,
  start: async () => undefined, stop: async () => undefined, sendContext: () => undefined,
  sendText: () => true, messages: [], inputLevel: 0, outputLevel: 0, isMuted: false, setMuted: () => undefined,
});

function enterText(input: HTMLElement, value: string) {
  // ReactDOM loads before this suite creates a DOM, so its input support probe
  // selects the legacy key-up path. Supply the legacy listener hooks as a DOM shim.
  Object.assign(input, { attachEvent: () => undefined, detachEvent: () => undefined });
  fireEvent.focusIn(input);
  fireEvent.change(input, { target: { value } });
  fireEvent.keyUp(input, { key: 'a' });
}

beforeEach(() => {
  dom = new Window({ url: 'https://localhost/go/test-tour' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    requestAnimationFrame: { value: (callback: FrameRequestCallback) => setTimeout(() => callback(0), 0), configurable: true },
    cancelAnimationFrame: { value: (id: number) => clearTimeout(id), configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
});
afterEach(() => { cleanup(); api.chat = originalChat; dom.happyDOM.abort(); });

describe('phone chat and live voice', () => {
  test('alternates typed and spoken provider transcript without a second chat request or duplicate rows', async () => {
    let requests = 0;
    api.chat = async () => { requests++; throw new Error('A connected conversation must use sendText.'); };
    const sent: string[] = [];
    const voice = connectedVoice();
    voice.messages = [{ id: 'spoken-user', role: 'user', text: 'Where is the lift?' }, { id: 'spoken-agent', role: 'agent', text: 'It is by the entrance.' }];
    voice.sendText = text => { sent.push(text); return true; };
    const view = render(<ChatSheet open sessionId="phone-session" voice={voice} onClose={() => undefined}/>);
    expect(view.getAllByText('Where is the lift?')).toHaveLength(1);
    expect(view.getAllByText('It is by the entrance.')).toHaveLength(1);
    await act(async () => {
      enterText(view.getByRole('textbox', { name: 'Message' }), '  Is it step-free?  ');
    });
    await act(async () => {
      fireEvent.click(view.getByRole('button', { name: 'Send' }));
    });
    expect(sent).toEqual(['Is it step-free?']);
    expect(requests).toBe(0);
    expect((view.getByRole('textbox', { name: 'Message' }) as HTMLInputElement).value).toBe('');
    expect(view.queryByText('Is it step-free?')).toBeNull();
    voice.messages = [...voice.messages, { id: 'typed-user', role: 'user', text: 'Is it step-free?' }, { id: 'typed-agent', role: 'agent', text: 'Yes, use the lift.' }];
    view.rerender(<ChatSheet open sessionId="phone-session" voice={voice} onClose={() => undefined}/>);
    expect(view.getAllByText('Is it step-free?')).toHaveLength(1);
    expect(view.getAllByText('Yes, use the lift.')).toHaveLength(1);
    voice.messages = [...voice.messages, { id: 'spoken-again', role: 'user', text: 'Thanks, what comes next?' }];
    view.rerender(<ChatSheet open sessionId="phone-session" voice={voice} onClose={() => undefined}/>);
    expect(view.getAllByText('Thanks, what comes next?')).toHaveLength(1);
    expect(requests).toBe(0);
  });

  test('sends suggestion buttons through the connected provider too', async () => {
    let requests = 0;
    api.chat = async () => { requests++; throw new Error('No fallback expected.'); };
    const voice = connectedVoice();
    const sent: string[] = [];
    voice.sendText = text => { sent.push(text); return true; };
    const view = render(<ChatSheet open sessionId="phone-session" voice={voice} onClose={() => undefined}/>);
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'What is next?' })); });
    expect(sent).toEqual(['What is next?']);
    expect(requests).toBe(0);
  });

  test('retains an unsent message and reports a live send failure without silently using another provider', async () => {
    let requests = 0;
    api.chat = async () => { requests++; throw new Error('No fallback expected.'); };
    const voice = connectedVoice();
    voice.sendText = () => false;
    const view = render(<ChatSheet open sessionId="phone-session" voice={voice} onClose={() => undefined}/>);
    await act(async () => {
      enterText(view.getByRole('textbox', { name: 'Message' }), 'Find a toilet');
    });
    await act(async () => {
      fireEvent.click(view.getByRole('button', { name: 'Send' }));
    });
    expect(view.getByRole('alert').textContent).toContain('not sent');
    expect((view.getByRole('textbox', { name: 'Message' }) as HTMLInputElement).value).toBe('Find a toilet');
    expect(requests).toBe(0);
  });

  test('does not fork a text request during the voice handshake', async () => {
    let requests = 0;
    let sends = 0;
    api.chat = async () => { requests++; throw new Error('No request expected.'); };
    const voice = connectedVoice();
    voice.status = 'connecting'; voice.sendText = () => { sends++; return true; };
    const view = render(<ChatSheet open sessionId="phone-session" voice={voice} onClose={() => undefined}/>);
    await act(async () => { enterText(view.getByRole('textbox', { name: 'Message' }), 'What is next?'); });
    expect((view.getByRole('button', { name: 'Send' }) as HTMLButtonElement).disabled).toBe(true);
    expect((view.getByRole('button', { name: 'What is next?' }) as HTMLButtonElement).disabled).toBe(true);
    await act(async () => { fireEvent.submit(view.getByRole('textbox', { name: 'Message' }).closest('form')!); });
    expect(requests).toBe(0); expect(sends).toBe(0);
  });

  test('keeps the disconnected text fallback and its actual display response', async () => {
    const requests: string[][] = [];
    const display: Display = { kind: 'highlight', space_id: 'actual-room' };
    const shown: (Display | null)[] = [];
    api.chat = async (id, message) => { requests.push([id, message]); return { reply: 'The toilet is by the stairs.', display, tool_calls: [] }; };
    const voice = connectedVoice(); voice.status = 'disconnected';
    voice.error = 'Microphone access was not allowed.';
    const view = render(<ChatSheet open sessionId="phone-session" voice={voice} onDisplay={value => shown.push(value)} onClose={() => undefined}/>);
    await act(async () => {
      enterText(view.getByRole('textbox', { name: 'Message' }), ' Where is the toilet? ');
    });
    await act(async () => {
      fireEvent.click(view.getByRole('button', { name: 'Send' }));
    });
    await waitFor(() => expect(view.queryByText('The toilet is by the stairs.')).not.toBeNull());
    expect(requests).toEqual([['phone-session', 'Where is the toilet?']]);
    expect(shown).toEqual([display]);
    expect(view.getAllByText('Where is the toilet?')).toHaveLength(1);
    expect(view.getAllByText('Microphone access was not allowed.').length).toBeGreaterThan(0);
  });

  test('drops a previous session reply and display after switching sessions', async () => {
    let finish: ((value: ChatReply) => void) | undefined;
    api.chat = () => new Promise(resolve => { finish = resolve; });
    const shown: (Display | null)[] = [];
    const props = { open: true, onClose: () => undefined, onDisplay: (value: Display | null) => shown.push(value) };
    const view = render(<ChatSheet {...props} sessionId="old-phone-session"/>);
    await act(async () => {
      enterText(view.getByRole('textbox', { name: 'Message' }), 'Old building question');
    });
    await act(async () => {
      fireEvent.click(view.getByRole('button', { name: 'Send' }));
    });
    view.rerender(<ChatSheet {...props} sessionId="new-phone-session"/>);
    await act(async () => { finish?.({ reply: 'Wrong building answer', tool_calls: [], display: { kind: 'highlight', space_id: 'old-room' } }); });
    expect(view.queryByText('Wrong building answer')).toBeNull();
    expect(view.queryByText('Old building question')).toBeNull();
    expect(shown).toEqual([]);
    api.chat = async () => ({ reply: 'Current building answer', tool_calls: [], display: null });
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'What is next?' })); });
    expect(view.queryByText('Current building answer')).not.toBeNull();
  });
});

import { LoaderCircle, Send, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, api } from '../api/client';
import type { Display } from '../api/types';
import { VoiceConversation } from '../voice/VoiceConversation';
import type { Voice } from './voice';

type Line = { id: number; role: 'agent' | 'user'; text: string };

/** Text chat with the same tools as voice (`POST /api/chat`); the fallback when voice is unavailable (U9). */
export function ChatSheet({ open, sessionId, onClose, onDisplay, voice, voiceError, suggestions = ['What is next?', 'Is there a step-free way?', 'Where is the nearest toilet?'] }: {
  open: boolean; sessionId: string | null; onClose: () => void; onDisplay?: (display: Display | null) => void; voice?: Voice; voiceError?: string | null; suggestions?: string[];
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [deliveryError, setDeliveryError] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([{ id: 0, role: 'agent', text: 'Ask me about your route or anything in this building.' }]);
  const generation = useRef(0);
  const connected = voice?.status === 'connected';
  const connecting = voice?.status === 'connecting';
  // The shared conversation renders provider errors; keep local delivery errors separate.
  const error = deliveryError ?? (voice ? null : voiceError);

  useEffect(() => {
    generation.current++;
    setLines([{ id: 0, role: 'agent', text: 'Ask me about your route or anything in this building.' }]);
    setText(''); setBusy(false); setDeliveryError(null);
    return () => { generation.current++; };
  }, [sessionId]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) { dialog.showModal(); requestAnimationFrame(() => input.current?.focus()); }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => history.current?.scrollTo({ top: history.current.scrollHeight }));
    return () => cancelAnimationFrame(frame);
  }, [open, lines, busy, voice?.messages]);

  const add = (role: Line['role'], value: string) => setLines(current => [...current, { id: current.length, role, text: value }]);
  const send = async (value: string) => {
    if (!sessionId || !value.trim() || busy || connecting) return;
    setDeliveryError(null);
    if (connected && voice) {
      // The SDK emits the real user/agent transcript. Do not start a second LLM
      // conversation, nor optimistically invent another transcript row here.
      if (voice.sendText(value.trim())) setText('');
      else setDeliveryError('That message was not sent. Reconnect voice or end it to use text chat.');
      return;
    }
    const request = generation.current;
    add('user', value.trim()); setText(''); setBusy(true);
    try {
      const reply = await api.chat(sessionId, value.trim());
      if (request !== generation.current) return;
      add('agent', reply.reply);
      onDisplay?.(reply.display ?? reply.tool_calls.find(call => call.ok && call.display)?.display ?? null);
    } catch (error) {
      if (request !== generation.current) return;
      add('agent', error instanceof ApiError && [404, 501, 503].includes(error.status) ? 'Text chat is not connected yet. The map and the step list still guide you.' : `That did not work: ${error instanceof Error ? error.message : 'unknown error'}`);
    }
    if (request === generation.current) setBusy(false);
  };
  const submit = (event: FormEvent) => { event.preventDefault(); void send(text); };

  return <dialog ref={ref} className="sheet chat-sheet" aria-labelledby="chat-title" onClose={onClose} onCancel={onClose}>
    <div className="sheet-handle"/>
    <header className="sheet-header"><div><h2 id="chat-title">Ask the building</h2><p>{connected ? 'Type or speak in the same live conversation.' : connecting ? 'Voice is connecting. You can type once it is ready.' : 'Answers come from the building data.'}</p></div><button className="icon-button" onClick={onClose} aria-label="Close chat"><X size={22}/></button></header>
    {error && <p className="plan-error" role="alert">{error}</p>}
    <div className="chat-history" ref={history}>
      {(lines.length > 1 || (!connected && !connecting && !voice?.messages?.length)) && <div role="log" aria-live="polite" aria-label="Text conversation">{lines.map(line => <div className={`message ${line.role}`} key={line.id}><span className="message-author">{line.role === 'agent' ? 'Alain' : 'You'}</span><p>{line.text}</p></div>)}</div>}
      {voice && <VoiceConversation voice={voice}/>}
      {busy && <p className="loading"><LoaderCircle className="spin" size={16}/>Thinking…</p>}
    </div>
    <div className="suggestions">{suggestions.map(item => <button key={item} onClick={() => void send(item)} disabled={busy || connecting || !sessionId}>{item}</button>)}</div>
    <form className="chat-input" onSubmit={submit}><label className="sr-only" htmlFor="chat-message">Message</label><input ref={input} id="chat-message" value={text} maxLength={500} onChange={event => setText(event.target.value)} placeholder="Ask about a room or a part" autoComplete="off"/><button className="icon-button dark" type="submit" disabled={!text.trim() || busy || connecting || !sessionId} aria-label="Send"><Send size={19}/></button></form>
  </dialog>;
}

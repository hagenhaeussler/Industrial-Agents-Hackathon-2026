import { LoaderCircle, Send, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, api } from '../api/client';
import type { Display } from '../api/types';

type Line = { id: number; role: 'agent' | 'user'; text: string };

/** Text chat with the same tools as voice (`POST /api/chat`); the fallback when voice is unavailable (U9). */
export function ChatSheet({ open, sessionId, onClose, onDisplay, voiceError, suggestions = ['What is next?', 'Is there a step-free way?', 'Where is the nearest toilet?'] }: {
  open: boolean; sessionId: string | null; onClose: () => void; onDisplay?: (display: Display | null) => void; voiceError?: string | null; suggestions?: string[];
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [lines, setLines] = useState<Line[]>([{ id: 0, role: 'agent', text: 'Ask me about your route or anything in this building.' }]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) { dialog.showModal(); requestAnimationFrame(() => input.current?.focus()); }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const add = (role: Line['role'], value: string) => setLines(current => [...current, { id: current.length, role, text: value }]);
  const send = async (value: string) => {
    if (!sessionId || !value.trim() || busy) return;
    add('user', value.trim()); setText(''); setBusy(true);
    try {
      const reply = await api.chat(sessionId, value.trim());
      add('agent', reply.reply);
      onDisplay?.(reply.display ?? reply.tool_calls.find(call => call.ok && call.display)?.display ?? null);
    } catch (error) {
      add('agent', error instanceof ApiError && [404, 501, 503].includes(error.status) ? 'Text chat is not connected yet. The map and the step list still guide you.' : `That did not work: ${error instanceof Error ? error.message : 'unknown error'}`);
    }
    setBusy(false);
    requestAnimationFrame(() => history.current?.scrollTo({ top: history.current.scrollHeight }));
  };
  const submit = (event: FormEvent) => { event.preventDefault(); void send(text); };

  return <dialog ref={ref} className="sheet chat-sheet" aria-labelledby="chat-title" onClose={onClose} onCancel={onClose}>
    <div className="sheet-handle"/>
    <header className="sheet-header"><div><h2 id="chat-title">Ask the building</h2><p>{voiceError ? `${voiceError} Text chat uses the same tools.` : 'Answers come from the building data.'}</p></div><button className="icon-button" onClick={onClose} aria-label="Close chat"><X size={22}/></button></header>
    <div className="chat-history" ref={history} role="log" aria-live="polite" aria-label="Conversation">
      {lines.map(line => <div className={`message ${line.role}`} key={line.id}><span className="message-author">{line.role === 'agent' ? 'Alain' : 'You'}</span><p>{line.text}</p></div>)}
      {busy && <p className="loading"><LoaderCircle className="spin" size={16}/>Thinking…</p>}
    </div>
    <div className="suggestions">{suggestions.map(item => <button key={item} onClick={() => void send(item)} disabled={busy}>{item}</button>)}</div>
    <form className="chat-input" onSubmit={submit}><label className="sr-only" htmlFor="chat-message">Message</label><input ref={input} id="chat-message" value={text} maxLength={500} onChange={event => setText(event.target.value)} placeholder="Ask about a room or a part" autoComplete="off"/><button className="icon-button dark" type="submit" disabled={!text.trim() || busy} aria-label="Send"><Send size={19}/></button></form>
  </dialog>;
}

import { Blobatar } from '@blobatar/react';
import { happy, idle } from 'blobatar/expression';
import { ArrowUpRight, MessageCircle, Send, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { findDestination } from '../navigation/routes';
import type { Destination } from '../navigation/routes';
import { getDemoReply } from './replies';

type Message = { id: number; role: 'agent' | 'user'; text: string };

export function Agent({ arrived, onDestination }: { arrived: boolean; onDestination: (destination: Destination) => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const historyRef = useRef<HTMLDivElement>(null);
  const [text, setText] = useState('');
  const [hidden, setHidden] = useState(document.hidden);
  const [messages, setMessages] = useState<Message[]>([{ id: 0, role: 'agent', text: 'Hi, ich bin Alain. Wohin möchtest du? Ich kenne die Demo-Wege zur Werkstatt, Besprechung und Kaffeeküche.' }]);

  useEffect(() => {
    const updateVisibility = () => setHidden(document.hidden);
    document.addEventListener('visibilitychange', updateVisibility);
    return () => document.removeEventListener('visibilitychange', updateVisibility);
  }, []);

  const send = (message: string) => {
    if (!message.trim()) return;
    const destination = findDestination(message);
    if (destination) onDestination(destination);
    setMessages(current => [...current, { id: current.length, role: 'user', text: message.trim() }, { id: current.length + 1, role: 'agent', text: getDemoReply(message) }]);
    setText('');
    requestAnimationFrame(() => historyRef.current?.scrollTo({ top: historyRef.current.scrollHeight, behavior: 'instant' }));
    inputRef.current?.focus();
  };
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); send(text); };

  return <>
    <section className="agent-dock" aria-label="Gebäudeassistent">
      <button className="agent-presence" onClick={() => dialogRef.current?.showModal()} aria-label="Mit Alain sprechen">
        <span className="avatar-wrap" data-paused={hidden}><Blobatar name="alain00" animate="always" size={116} expression={arrived ? happy : idle} title="Alain, dein Gebäudeguide"/></span>
        <span className="agent-bubble surface"><strong>{arrived ? 'Da sind wir!' : 'Ich zeig dir den Weg.'}</strong></span>
      </button>
      <button className="ask-agent surface" onClick={() => dialogRef.current?.showModal()}><MessageCircle size={21}/><span>Frag das Gebäude …</span><span className="send-icon"><ArrowUpRight size={22}/></span></button>
    </section>
    <dialog className="sheet chat-sheet" ref={dialogRef} aria-labelledby="agent-title">
      <div className="sheet-handle"/>
      <header className="sheet-header"><div><h2 id="agent-title">Frag Alain.</h2><p>Demo-Antworten · Kein Sprachmodell verbunden</p></div><button className="icon-button" onClick={() => dialogRef.current?.close()} aria-label="Chat schließen"><X size={22}/></button></header>
      <div className="chat-history" ref={historyRef} aria-live="polite" role="log" aria-label="Gespräch mit Alain">
        {messages.map(message => <div className={`message ${message.role}`} key={message.id}><span className="message-author">{message.role === 'agent' ? 'Alain' : 'Du'}</span><p>{message.text}</p></div>)}
      </div>
      <div className="suggestions">{['Zur Kaffeeküche', 'Ohne Treppen?', 'Wo bin ich?'].map(suggestion => <button key={suggestion} onClick={() => send(suggestion)}>{suggestion}</button>)}</div>
      <form className="chat-input" onSubmit={submit}><label className="sr-only" htmlFor="message">Nachricht an Alain</label><input ref={inputRef} id="message" value={text} maxLength={1000} onChange={event => setText(event.target.value)} placeholder="Wohin möchtest du?" autoComplete="off"/><button className="icon-button dark" type="submit" disabled={!text.trim()} aria-label="Nachricht senden"><Send size={19}/></button></form>
    </dialog>
  </>;
}

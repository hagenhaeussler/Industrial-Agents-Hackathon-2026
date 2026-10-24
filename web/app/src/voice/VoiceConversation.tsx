import { useEffect, useRef, useState } from 'react';
import type { Voice } from '../phone/voice';
import './VoiceConversation.css';

/** Inline view of the real provider conversation. Starting audio always needs an explicit click. */
export function VoiceConversation({ voice }: { voice: Voice }) {
  const [action, setAction] = useState<'start' | 'stop' | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const messages = voice.messages ?? [];
  const connected = voice.status === 'connected';
  const connecting = voice.status === 'connecting' || action === 'start';
  const error = voice.error || actionError;
  const phase = voice.error ? 'Voice unavailable' : connecting ? 'Connecting' : connected
    ? voice.isSpeaking ? 'Speaking' : voice.isMuted ? 'Microphone muted' : 'Listening'
    : 'Conversation ended';

  useEffect(() => {
    const element = log.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages.length, messages.at(-1)?.text]);

  // The orb can retry outside this panel. A new provider attempt supersedes a
  // previous local action error, while a failed End still remains actionable.
  useEffect(() => {
    if (voice.status === 'connecting' || voice.status === 'connected') setActionError(null);
  }, [voice.status]);

  const perform = async (next: 'start' | 'stop') => {
    setActionError(null); setAction(next);
    try { await (next === 'start' ? voice.start() : voice.stop()); }
    catch { setActionError(next === 'start' ? 'Voice could not start. You can keep typing and try again.' : 'The conversation could not end. Try again.'); }
    finally { setAction(current => current === next ? null : current); }
  };
  const mute = () => {
    try { voice.setMuted(!voice.isMuted); setActionError(null); }
    catch { setActionError('Microphone control is unavailable. You can end the conversation and keep typing.'); }
  };

  if (!connecting && !connected && voice.status !== 'error' && !error && !messages.length) return null;

  return <section className="voice-conversation" aria-label="Building agent conversation">
    <header className="voice-conversation-header">
      <h2>Building agent</h2>
      <span className={`voice-conversation-status${connected ? ' live' : ''}`} role="status">{phase}</span>
    </header>
    {error && <p className="voice-conversation-error" role="alert">{error}</p>}
    {messages.length > 0 && <div ref={log} className="voice-conversation-log" role="log" aria-label="Messages with the building agent" aria-live="polite" aria-relevant="additions text">
      {messages.map(message => <div key={message.id} className={`voice-conversation-message ${message.role}`}>
        <strong>{message.role === 'user' ? 'You' : 'Building agent'}</strong>
        <p>{message.text}</p>
      </div>)}
    </div>}
    <div className="voice-conversation-actions">
      {connected && !voice.error && <button type="button" className="voice-conversation-action" aria-pressed={voice.isMuted} disabled={action === 'stop'} onClick={mute}>{voice.isMuted ? 'Unmute microphone' : 'Mute microphone'}</button>}
      {(connecting || connected) ? <button type="button" className="voice-conversation-action" disabled={action === 'stop'} onClick={() => void perform('stop')}>{action === 'stop' ? 'Ending…' : 'End conversation'}</button>
        : <button type="button" className="voice-conversation-action" disabled={!voice.available} onClick={() => void perform('start')}>Retry voice</button>}
    </div>
  </section>;
}

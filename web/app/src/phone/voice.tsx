import { createContext, lazy, Suspense, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

/**
 * Mounts Manuel's codex's `src/voice/useBuildingVoice` (CONTRACTS §8) when it is part of the build and
 * exposes one small voice API to the screens. The ElevenLabs SDK loads lazily in a sibling bridge after
 * the screen is up, so it never delays the tour and never remounts the screen. Without the hook (or a
 * token) the screens fall back to text chat with the same tools.
 */
export type Voice = {
  available: boolean;
  status: string; // 'disconnected' | 'connecting' | 'connected' | …
  isSpeaking: boolean;
  error: string | null;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  sendContext: (text: string) => void;
};
type Agent = 'navigator' | 'admin';
type VoiceHook = (options: { agent: Agent; sessionId: string; onDisplay?: (display: Record<string, unknown>) => void }) => Omit<Voice, 'available'>;
type BridgeProps = { agent: Agent; sessionId: string; onDisplay?: (display: Record<string, unknown>) => void; publish: (voice: Voice) => void };

const loadHook = Object.values(import.meta.glob('../voice/useBuildingVoice.ts'))[0] as (() => Promise<{ useBuildingVoice: VoiceHook }>) | undefined;

const unavailable = (message: string): Voice => ({
  available: false, status: 'disconnected', isSpeaking: false, error: message,
  start: async () => { throw new Error(message); }, stop: async () => undefined, sendContext: () => undefined,
});
const notBuilt = unavailable('Voice is not part of this build yet. Text chat uses the same tools.');
const loading: Voice = { ...unavailable('Voice is still loading. Try again in a moment.'), available: true };

const Bridge = loadHook ? lazy(async () => {
  const [{ ConversationProvider }, { useBuildingVoice }] = await Promise.all([import('@elevenlabs/react'), loadHook()]);
  function Inner({ agent, sessionId, onDisplay, publish }: BridgeProps) {
    const voice = useBuildingVoice({ agent, sessionId, onDisplay });
    useEffect(() => { publish({ available: true, ...voice }); }, [voice.status, voice.isSpeaking, voice.error, voice.start, voice.stop, voice.sendContext]); // eslint-disable-line react-hooks/exhaustive-deps
    return null;
  }
  return { default: (props: BridgeProps) => <ConversationProvider><Inner {...props}/></ConversationProvider> };
}) : null;

const VoiceContext = createContext<Voice>(notBuilt);
export const useVoice = () => useContext(VoiceContext);

export function VoiceProvider({ agent, sessionId, onDisplay, children }: { agent: Agent; sessionId: string | null; onDisplay?: (display: Record<string, unknown>) => void; children: ReactNode }) {
  const [voice, setVoice] = useState<Voice>(Bridge ? loading : notBuilt);
  const [ready, setReady] = useState(false);
  // load the SDK once the screen has had a moment to render
  useEffect(() => { if (!Bridge || !sessionId) return; const timer = setTimeout(() => setReady(true), 600); return () => clearTimeout(timer); }, [sessionId]);
  return <VoiceContext.Provider value={voice}>
    {children}
    {Bridge && ready && sessionId && <Suspense fallback={null}><Bridge key={sessionId} agent={agent} sessionId={sessionId} onDisplay={onDisplay} publish={setVoice}/></Suspense>}
  </VoiceContext.Provider>;
}

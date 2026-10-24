import { createContext, lazy, Suspense, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { VoiceOrb } from '../voice/VoiceOrb';
import type { VoiceClientTool, VoiceMessage } from '../voice/useBuildingVoice';
import type { ToolResponse } from '../voice/clientTools';

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
  sendText: (text: string) => boolean;
  messages: VoiceMessage[];
  inputLevel: number;
  outputLevel: number;
  isMuted: boolean;
  setMuted: (muted: boolean) => void;
};
type Agent = 'navigator' | 'admin';
type VoiceOptions = {
  onDisplay?: (display: Record<string, unknown>) => void;
  onToolResponse?: (response: ToolResponse) => void;
  clientTools?: Record<string, VoiceClientTool>;
};
type VoiceHook = (options: { agent: Agent; sessionId: string } & VoiceOptions) => Omit<Voice, 'available'>;
type BridgeProps = { agent: Agent; sessionId: string; publish: (voice: Voice) => void } & VoiceOptions;

const loadHook = Object.values(import.meta.glob('../voice/useBuildingVoice.ts'))[0] as (() => Promise<{ useBuildingVoice: VoiceHook }>) | undefined;

const unavailable = (message: string): Voice => ({
  available: false, status: 'disconnected', isSpeaking: false, error: message,
  start: async () => { throw new Error(message); }, stop: async () => undefined, sendContext: () => undefined,
  sendText: () => false, messages: [], inputLevel: 0, outputLevel: 0, isMuted: false, setMuted: () => undefined,
});
const notBuilt = unavailable('Voice is not part of this build yet. Text chat uses the same tools.');
const loading = { ...unavailable('Voice is still loading. Try again in a moment.'), error: null };

const Bridge = loadHook ? lazy(async () => {
  const [{ ConversationProvider }, { useBuildingVoice }] = await Promise.all([import('@elevenlabs/react'), loadHook()]);
  function Inner({ agent, sessionId, onDisplay, onToolResponse, clientTools, publish }: BridgeProps) {
    const voice = useBuildingVoice({ agent, sessionId, onDisplay, onToolResponse, clientTools });
    useEffect(() => { publish({ available: true, ...voice }); }, [voice.status, voice.isSpeaking, voice.error, voice.start, voice.stop, voice.sendContext, voice.sendText, voice.messages, voice.inputLevel, voice.outputLevel, voice.isMuted, voice.setMuted]); // eslint-disable-line react-hooks/exhaustive-deps
    return null;
  }
  return { default: (props: BridgeProps) => <ConversationProvider><Inner {...props}/></ConversationProvider> };
}) : null;

const VoiceContext = createContext<Voice>(notBuilt);
export const useVoice = () => useContext(VoiceContext);

export function VoiceProvider({ agent, sessionId, onDisplay, onToolResponse, clientTools, children }: { agent: Agent; sessionId: string | null; children: ReactNode } & VoiceOptions) {
  const binding = `${agent}:${sessionId ?? ''}`;
  const [published, setPublished] = useState<{ binding: string; voice: Voice } | null>(null);
  const [ready, setReady] = useState<string | null>(null);
  const activeBinding = useRef(binding);
  activeBinding.current = binding;
  const publish = useCallback((voice: Voice) => {
    if (activeBinding.current === binding) setPublished({ binding, voice });
  }, [binding]);
  // A previous building's callbacks and transcript are never exposed in a new session.
  const voice = sessionId && published?.binding === binding ? published.voice : Bridge ? loading : notBuilt;
  useEffect(() => {
    if (!Bridge || !sessionId) return;
    const timer = setTimeout(() => setReady(binding), 600);
    return () => clearTimeout(timer);
  }, [binding, sessionId]);
  return <VoiceContext.Provider value={voice}>
    {children}
    {Bridge && ready === binding && sessionId && <Suspense fallback={null}><Bridge key={binding} agent={agent} sessionId={sessionId} onDisplay={onDisplay} onToolResponse={onToolResponse} clientTools={clientTools} publish={publish}/></Suspense>}
  </VoiceContext.Provider>;
}

/** For screens that create their session themselves: register it (and the display handler) from inside. */
type Register = (sessionId: string | null, options: VoiceOptions) => void;
const RegisterContext = createContext<Register>(() => undefined);

export function VoiceRoot({ agent, children }: { agent: Agent; children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const handlers = useRef<VoiceOptions>({});
  const [clientTools, setClientTools] = useState<VoiceOptions['clientTools']>();
  const register = useCallback<Register>((id, options) => {
    setSessionId(id); handlers.current = options;
    setClientTools(current => current === options.clientTools ? current : options.clientTools);
  }, []);
  const onDisplay = useCallback((display: Record<string, unknown>) => handlers.current.onDisplay?.(display), []);
  const onToolResponse = useCallback((response: ToolResponse) => handlers.current.onToolResponse?.(response), []);
  return <RegisterContext.Provider value={register}><VoiceProvider agent={agent} sessionId={sessionId} onDisplay={onDisplay} onToolResponse={onToolResponse} clientTools={clientTools}>{children}</VoiceProvider></RegisterContext.Provider>;
}

export function useVoiceSession(sessionId: string | null, onDisplay?: VoiceOptions['onDisplay'], options: Omit<VoiceOptions, 'onDisplay'> = {}): Voice {
  const register = useContext(RegisterContext);
  useEffect(() => { register(sessionId, { ...options, onDisplay }); });
  return useVoice();
}

/** The orb starts a real two-way call; End and mute are in the conversation panel. */
export function VoiceButton({ voice, onUnavailable = () => undefined }: { voice: Voice; onUnavailable?: (message: string) => void }) {
  const live = voice.status === 'connected';
  const busy = voice.status === 'connecting';
  const phase = busy ? 'connecting' : live ? voice.isSpeaking ? 'speaking' : voice.isMuted ? 'muted' : 'listening' : voice.error && voice.available ? 'error' : 'idle';
  return <VoiceOrb phase={phase} level={voice.isSpeaking ? voice.outputLevel : voice.inputLevel}
    disabled={!voice.available || busy} label={live ? 'End voice conversation' : busy ? 'Connecting voice' : voice.available ? 'Talk to the building agent' : 'Voice is loading'}
    onClick={() => void (live ? voice.stop() : voice.start()).catch((error: unknown) => onUnavailable(error instanceof Error ? error.message : 'Voice is unavailable.'))}/>;
}

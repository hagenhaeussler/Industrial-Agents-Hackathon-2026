import type { CSSProperties } from 'react';
import './VoiceOrb.css';

export type VoiceOrbPhase = 'idle' | 'connecting' | 'listening' | 'speaking' | 'muted' | 'error';
export type VoiceOrbProps = {
  phase: VoiceOrbPhase;
  /** Real input/output level from the conversation; no audio is captured by this component. */
  level?: number;
  disabled?: boolean;
  label?: string;
  onClick: () => void;
};

const labels: Record<VoiceOrbPhase, string> = {
  idle: 'Talk to the building agent',
  connecting: 'Open voice conversation. Connecting to the building agent',
  listening: 'Open voice conversation. Listening',
  speaking: 'Open voice conversation. Agent is speaking',
  muted: 'Open voice conversation. Microphone is muted',
  error: 'Open voice conversation. Voice is unavailable',
};

/** Presentation only: the caller owns permissions, connection, mute state and audio metering. */
export function VoiceOrb({ phase, level = 0, disabled = false, label, onClick }: VoiceOrbProps) {
  const accessible = label?.trim() || labels[phase];
  const style = { '--orb-level': Number.isFinite(level) ? Math.max(0, Math.min(1, level)) : 0 } as CSSProperties;
  return <button type="button" className={`voice-orb-button voice-orb--${phase}`} style={style} disabled={disabled}
    aria-label={accessible} title={accessible} aria-busy={phase === 'connecting'} onClick={onClick}>
    <span className="voice-orb" aria-hidden="true">
      <span className="voice-orb-shape"/>
      <span className="voice-orb-bubble voice-orb-bubble-one"/>
      <span className="voice-orb-bubble voice-orb-bubble-two"/>
    </span>
  </button>;
}

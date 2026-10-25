import { Loader, Mic } from "lucide-react";
import type { VoicePhase } from "./useBuildingVoice";

/**
 * Starts or ends the voice conversation. Dark while off, accent while the microphone is open.
 * It always shows a plain mic: a crossed-out mic reads as "muted" while the agent is listening.
 */
export function MicButton({ phase, onStart, onStop }: { phase: VoicePhase; onStart: () => void; onStop: () => void }) {
  const live = phase === "listening" || phase === "speaking";
  const busy = phase === "connecting";
  return (
    <button
      type="button"
      onClick={live || busy ? onStop : onStart}
      aria-label={live ? "End conversation" : busy ? "Cancel" : "Talk to Locora"}
      aria-pressed={live}
      className={`grid size-[52px] shrink-0 place-items-center rounded-[15px] ${
        live ? "bg-accent text-ink ring-2 ring-ink" : "bg-ink text-white"
      }`}
    >
      {busy ? <Loader size={22} /> : <Mic size={22} />}
    </button>
  );
}

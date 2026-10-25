import { Download, Loader, Mic, MicOff, Square } from "lucide-react";
import type { BuildingVoice } from "./useBuildingVoice";

/**
 * Muting keeps the conversation. Ending it is a separate action.
 */
export function MicButton({ voice }: { voice: BuildingVoice }) {
  const { phase, isMuted } = voice;
  const live = phase === "listening" || phase === "speaking";
  const busy = phase === "connecting";
  return (
    <div className="flex shrink-0 items-center gap-1">
      <button
        type="button"
        onClick={busy ? voice.stop : live ? voice.toggleMute : () => void voice.start()}
        aria-label={busy ? "Cancel" : live ? isMuted ? "Unmute microphone" : "Mute microphone" : "Talk to Locora"}
        aria-pressed={live && !isMuted}
        className={`grid size-[52px] shrink-0 place-items-center rounded-[15px] ${
          live && !isMuted ? "bg-accent text-ink ring-2 ring-ink" : "bg-ink text-white"
        }`}
      >
        {busy ? <Loader size={22} /> : live && isMuted ? <MicOff size={22} /> : <Mic size={22} />}
      </button>
      {live && (
        <button type="button" onClick={voice.stop} aria-label="End conversation" title="End conversation"
          className="grid size-10 place-items-center rounded-[12px] text-danger hover:bg-field">
          <Square size={17} />
        </button>
      )}
      {voice.hasLog && (
        <button type="button" onClick={voice.downloadLog} aria-label="Download conversation log" title="Download conversation log"
          className="grid size-10 place-items-center rounded-[12px] text-muted hover:bg-field">
          <Download size={17} />
        </button>
      )}
    </div>
  );
}

import { Avatar } from "../avatar/Avatar";
import { MicButton } from "../voice/MicButton";
import type { BuildingVoice } from "../voice/useBuildingVoice";
import { ModeSwitch, type GuideMode } from "./ModeSwitch";

const HINTS = {
  off: "Ask Locora about rooms, equipment or routes.",
  connecting: "Connecting…",
  listening: "I'm listening.",
  speaking: "",
  error: "",
};

/** Avatar, the agent's latest words, the view switch and the mic. */
export function AgentDock({
  voice,
  mode,
  onMode,
  arrived,
  onOpenChat,
}: {
  voice: BuildingVoice;
  mode: GuideMode;
  onMode: (mode: GuideMode) => void;
  arrived: boolean;
  onOpenChat: () => void;
}) {
  const lastAgent = voice.entries.findLast((entry) => entry.kind === "message" && entry.role === "agent");
  const said = lastAgent?.kind === "message" ? lastAgent.text : undefined;
  // What the agent understood the person to say, so they can see it was received.
  const lastUser = voice.entries.findLast((entry) => entry.kind === "message" && entry.role === "user");
  const heard = voice.phase !== "off" && lastUser?.kind === "message" ? lastUser.text : undefined;
  const bubble = voice.error ?? (voice.phase === "off" ? HINTS.off : voice.isMuted ? "Microphone muted. You can type." : (said ?? HINTS[voice.phase]));
  return (
    <section
      aria-label="Locora assistant"
      className="absolute inset-x-3.5 bottom-[max(14px,env(safe-area-inset-bottom))] mx-auto max-w-[460px]"
    >
      {heard && (
        <p className="mb-1.5 ml-auto line-clamp-2 w-fit max-w-[80%] rounded-[15px_15px_5px_15px] bg-ink px-3.5 py-2.5 text-[12px] leading-snug font-[650] text-white shadow-[var(--shadow-float)]">
          {heard}
        </p>
      )}
      <button type="button" onClick={onOpenChat} className="flex w-full items-end text-left" aria-label="Open conversation">
        <Avatar phase={voice.phase} level={voice.level} arrived={arrived} size={96} />
        <span className="float mb-3 -ml-1 line-clamp-3 rounded-[15px_15px_15px_5px] px-3.5 py-2.5 text-[12px] leading-snug font-[650]">
          {bubble}
        </span>
      </button>
      <div className="float mt-1 flex items-center gap-1.5 rounded-[20px] p-1.5">
        <ModeSwitch mode={mode} onChange={onMode} />
        <MicButton voice={voice} />
      </div>
    </section>
  );
}

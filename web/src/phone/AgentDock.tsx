import { Avatar } from "../avatar/Avatar";
import { MicButton } from "../voice/MicButton";
import type { BuildingVoice } from "../voice/useBuildingVoice";
import { ModeSwitch, type GuideMode } from "./ModeSwitch";

const HINTS = {
  off: "Tap the mic and ask me anything about this building.",
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
  const bubble = voice.error ?? (voice.phase === "off" ? HINTS.off : (said ?? HINTS[voice.phase]));
  return (
    <section
      aria-label="Building assistant"
      className="absolute inset-x-3.5 bottom-[max(14px,env(safe-area-inset-bottom))] mx-auto max-w-[460px]"
    >
      <button type="button" onClick={onOpenChat} className="flex w-full items-end text-left" aria-label="Open conversation">
        <Avatar phase={voice.phase} level={voice.level} arrived={arrived} size={96} />
        <span className="float mb-3 -ml-1 line-clamp-3 rounded-[15px_15px_15px_5px] px-3.5 py-2.5 text-[12px] leading-snug font-[650]">
          {bubble}
        </span>
      </button>
      <div className="float mt-1 flex items-center gap-1.5 rounded-[20px] p-1.5">
        <ModeSwitch mode={mode} onChange={onMode} />
        <MicButton phase={voice.phase} onStart={() => void voice.start()} onStop={voice.stop} />
      </div>
    </section>
  );
}

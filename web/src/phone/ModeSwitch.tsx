import { Camera, List, Map } from "lucide-react";

export type GuideMode = "map" | "steps" | "camera";

const MODES = [
  { mode: "map", label: "Map", Icon: Map },
  { mode: "steps", label: "Steps", Icon: List },
  { mode: "camera", label: "Camera", Icon: Camera },
] as const;

/** Map, step list or camera. Voice and the avatar stay available in every mode. */
export function ModeSwitch({ mode, onChange }: { mode: GuideMode; onChange: (mode: GuideMode) => void }) {
  return (
    <div role="radiogroup" aria-label="View" className="flex flex-1 gap-1 rounded-[15px] bg-field p-1">
      {MODES.map(({ mode: value, label, Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mode === value}
          onClick={() => onChange(value)}
          className={`flex h-11 flex-1 items-center justify-center gap-1.5 rounded-[12px] text-xs font-[700] ${
            mode === value ? "float text-ink" : "text-muted"
          }`}
        >
          <Icon size={17} />
          {label}
        </button>
      ))}
    </div>
  );
}

import { Blobatar } from "@blobatar/react";
import { happy, idle, sad, surprised, unsure } from "blobatar/expression";
import { useEffect, useRef, useState } from "react";
import type { VoicePhase } from "../voice/useBuildingVoice";

const EXPRESSIONS = { off: idle, connecting: unsure, listening: surprised, speaking: happy, error: sad };

/**
 * The building's face: the `alain00` Blobatar from the phone prototype. It shows the conversation phase and
 * moves with the agent's voice level while it speaks. It owns no conversation logic.
 */
export function Avatar({
  phase,
  level,
  arrived = false,
  size = 112,
  name = "alain00",
}: {
  phase: VoicePhase;
  level?: () => number;
  arrived?: boolean;
  size?: number;
  name?: string;
}) {
  const wrap = useRef<HTMLSpanElement>(null);
  const hidden = usePageHidden();

  // Follow the voice level only while the agent speaks, so nothing repaints continuously otherwise.
  useEffect(() => {
    const element = wrap.current;
    if (phase !== "speaking" || !level || !element) return;
    let frame = requestAnimationFrame(function tick() {
      element.style.setProperty("--level", Math.min(1, level() * 2.5).toFixed(3));
      frame = requestAnimationFrame(tick);
    });
    return () => {
      cancelAnimationFrame(frame);
      element.style.setProperty("--level", "0");
    };
  }, [phase, level]);

  const expression = arrived && phase !== "speaking" ? happy : EXPRESSIONS[phase];
  return (
    <span
      ref={wrap}
      className={`avatar-voice inline-grid place-items-center ${hidden ? "avatar-paused" : ""}`}
      style={{ width: size, height: size }}
    >
      <Blobatar name={name} animate="always" size={size} expression={expression} title="Locora assistant" />
    </span>
  );
}

function usePageHidden() {
  const [hidden, setHidden] = useState(document.hidden);
  useEffect(() => {
    const update = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  return hidden;
}

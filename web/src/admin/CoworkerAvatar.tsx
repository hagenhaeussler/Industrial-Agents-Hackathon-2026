import { BOT_BODY_PATH, BOT_EYE_COLOR } from "@locora/view";
import { MEMBERS } from "./team";

/** One coworker color, with the same bot face used in the building. */
export function CoworkerAvatar({ id, color, size = 28 }: { id: string; color?: string; size?: number }) {
  const fill = color ?? MEMBERS.find((member) => member.id === id)?.color ?? "#397a91";
  return <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="shrink-0">
    <path d={BOT_BODY_PATH} fill={fill} />
    <g fill={BOT_EYE_COLOR}>
      <rect x="21" y="23" width="6" height="15" rx="3" />
      <rect x="37" y="23" width="6" height="15" rx="3" />
    </g>
  </svg>;
}

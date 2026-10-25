import { ArrowUp, ChevronsDown, ChevronsUp, CornerUpLeft, CornerUpRight, Flag, MapPin } from "lucide-react";
import type { Turn } from "../route/directions";

export function TurnIcon({ turn, size = 28 }: { turn: Turn; size?: number }) {
  const props = { size, strokeWidth: 2.4 };
  if (turn === "left") return <CornerUpLeft {...props} />;
  if (turn === "right") return <CornerUpRight {...props} />;
  if (turn === "up") return <ChevronsUp {...props} />;
  if (turn === "down") return <ChevronsDown {...props} />;
  if (turn === "arrive") return <Flag {...props} />;
  if (turn === "start") return <MapPin {...props} />;
  return <ArrowUp {...props} />;
}

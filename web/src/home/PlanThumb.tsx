import type { Space } from "@locora/view";
import { useMemo } from "react";
import { useBuildingDocument } from "../api/buildings";
import { groundPlan } from "./plan";
import { useInView } from "./useInView";

// Stairs and lifts use the accent so the way between floors stands out.
const FILLS: Record<Space["type"], string> = {
  room: "#ffffff",
  hall: "#faf8f2",
  corridor: "#e6e4dc",
  stair: "#dcff58",
  lift: "#dcff58",
  outdoor: "#d7e7cf",
};

/** The ground floor of a building, drawn from building.json once the thumbnail scrolls into view. */
export function PlanThumb({ buildingId, className = "" }: { buildingId: string; className?: string }) {
  const [ref, seen] = useInView<HTMLDivElement>();
  const building = useBuildingDocument(buildingId, seen);
  const plan = useMemo(() => building.data && groundPlan(building.data), [building.data]);
  return (
    <div ref={ref} className={className}>
      {plan && (
        <svg viewBox={plan.viewBox} className="size-full" role="img" aria-label="Ground floor plan">
          {plan.shapes.map((shape) => (
            <path
              key={shape.id}
              d={shape.d}
              fill={FILLS[shape.type]}
              stroke="#191c16b3"
              strokeWidth={0.8}
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>
      )}
    </div>
  );
}

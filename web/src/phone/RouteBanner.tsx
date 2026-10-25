import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Step } from "../route/directions";
import { TurnIcon } from "./TurnIcon";

/** The current step, the destination and the total length. Tap the text to see all steps. */
export function RouteBanner({
  step,
  index,
  count,
  destination,
  lengthM,
  onPrevious,
  onNext,
  onOpen,
}: {
  step: Step;
  index: number;
  count: number;
  destination: string;
  lengthM: number | null;
  onPrevious: () => void;
  onNext: () => void;
  onOpen: () => void;
}) {
  const arrived = step.turn === "arrive";
  return (
    <div className="float flex w-full items-center gap-2 rounded-[20px] p-2 pl-3">
      <button type="button" onClick={onOpen} className="flex min-w-0 flex-1 items-center gap-3 py-1.5 text-left">
        <span
          className={`grid size-12 shrink-0 place-items-center rounded-[14px] ${arrived ? "bg-accent" : "bg-field"}`}
        >
          <TurnIcon turn={step.turn} />
        </span>
        <span className="grid min-w-0 gap-1">
          <span className="text-[18px] leading-[1.2] font-[750] tracking-[-0.6px] min-[800px]:text-[21px]">
            {step.instruction}
          </span>
          <span className="truncate text-xs font-[650]">
            {destination}
            <span className="font-normal text-muted">
              {" "}
              · {step.floorName}
              {lengthM !== null && ` · ${Math.round(lengthM)} m total`}
            </span>
          </span>
        </span>
      </button>
      <div className="flex shrink-0 flex-col items-center gap-1">
        <button
          type="button"
          onClick={onNext}
          disabled={index >= count - 1}
          aria-label="Next step"
          className="grid size-11 place-items-center rounded-[13px] bg-ink text-white"
        >
          <ChevronRight size={22} />
        </button>
        <button
          type="button"
          onClick={onPrevious}
          disabled={index === 0}
          aria-label="Previous step"
          className="grid h-7 w-11 place-items-center rounded-[10px] bg-field text-muted"
        >
          <ChevronLeft size={16} />
        </button>
      </div>
    </div>
  );
}

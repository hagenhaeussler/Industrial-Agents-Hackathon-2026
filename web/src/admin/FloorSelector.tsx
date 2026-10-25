import type { FloorScene } from "@locora/view";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import type { View } from "./Sidebar";

/** Keep every floor reachable without pushing the other header controls out of view. */
export function FloorSelector({
  floors,
  view,
  focusFloor,
  onFocusFloor,
}: {
  floors: FloorScene[];
  view: View;
  focusFloor: string | null;
  onFocusFloor: (floorId: string | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  // Keep the preferred width independent of arrow padding so overflow cannot toggle itself.
  const [scroll, setScroll] = useState({ contentWidth: 0, overflowing: false, previous: false, next: false });

  useLayoutEffect(() => {
    const container = containerRef.current;
    const viewport = viewportRef.current;
    const content = contentRef.current;
    if (!container || !viewport || !content) return;

    const measure = () => {
      const next = {
        contentWidth: content.scrollWidth,
        overflowing: content.scrollWidth > container.clientWidth,
        previous: viewport.scrollLeft > 1,
        next: viewport.scrollLeft + viewport.clientWidth < viewport.scrollWidth - 1,
      };
      setScroll((current) =>
        current.contentWidth === next.contentWidth &&
        current.overflowing === next.overflowing &&
        current.previous === next.previous &&
        current.next === next.next
          ? current
          : next,
      );
    };
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    observer.observe(viewport);
    observer.observe(content);
    viewport.addEventListener("scroll", measure);
    measure();
    return () => {
      observer.disconnect();
      viewport.removeEventListener("scroll", measure);
    };
  }, []);

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    const selected = contentRef.current?.querySelector('[aria-checked="true"]');
    if (!viewport || !selected) return;
    const bounds = viewport.getBoundingClientRect();
    const floor = selected.getBoundingClientRect();
    if (floor.left < bounds.left) viewport.scrollLeft -= bounds.left - floor.left;
    else if (floor.right > bounds.right) viewport.scrollLeft += floor.right - bounds.right;
  }, [floors, focusFloor, view, scroll.overflowing]);

  function scrollFloors(direction: "previous" | "next") {
    const viewport = viewportRef.current;
    if (viewport) {
      viewport.scrollBy({ left: viewport.clientWidth * (direction === "previous" ? -1 : 1), behavior: "instant" });
    }
  }

  return (
    <div
      ref={containerRef}
      style={{ width: scroll.contentWidth || undefined }}
      className={`relative min-w-0 max-w-[50%] shrink rounded-full bg-field ${scroll.overflowing ? "px-7" : ""}`}
    >
      {scroll.overflowing && (
        <button
          type="button"
          aria-label="Previous floors"
          disabled={!scroll.previous}
          onClick={() => scrollFloors("previous")}
          className="absolute inset-y-1 left-1 grid w-6 place-items-center rounded-full"
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
      )}
      <div ref={viewportRef} className="overflow-x-auto overscroll-x-contain rounded-full [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div ref={contentRef} role="radiogroup" aria-label="Floor" className="flex w-max items-center gap-1 p-1">
          {view !== "plans" && (
            <FloorChip label="All" title="All floors" active={focusFloor === null} onClick={() => onFocusFloor(null)} />
          )}
          {floors.map((floor) => (
            <FloorChip
              key={floor.id}
              label={String(floor.level)}
              title={floor.name}
              active={focusFloor === floor.id}
              onClick={() => onFocusFloor(floor.id)}
            />
          ))}
        </div>
      </div>
      {scroll.overflowing && (
        <button
          type="button"
          aria-label="Next floors"
          disabled={!scroll.next}
          onClick={() => scrollFloors("next")}
          className="absolute inset-y-1 right-1 grid w-6 place-items-center rounded-full"
        >
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

function FloorChip({ label, title, active, onClick }: { label: string; title: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      title={title}
      aria-label={title}
      onClick={onClick}
      className={`grid h-7 min-w-7 shrink-0 place-items-center rounded-full px-2 text-xs font-[750] focus-visible:outline-none ${active ? "bg-ink text-white" : ""}`}
    >
      {label}
    </button>
  );
}

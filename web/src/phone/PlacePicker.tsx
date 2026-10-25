import type { Building } from "@building/view";
import { ChevronRight, DoorOpen, Package, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { searchPlaces, type PlaceOption } from "../route/places";
import { Sheet } from "../ui/Sheet";

/** Search rooms and equipment and pick one, for the start or the destination. */
export function PlacePicker({
  building,
  open,
  title,
  onClose,
  onPick,
}: {
  building: Building;
  open: boolean;
  title: string;
  onClose: () => void;
  onPick: (place: PlaceOption) => void;
}) {
  const [text, setText] = useState("");
  const results = useMemo(() => searchPlaces(building, text), [building, text]);
  return (
    <Sheet open={open} onClose={onClose} title={title} className="flex-col [&[open]]:flex [&[open]]:h-[min(680px,86svh)]">
      <label className="flex items-center gap-2 rounded-[15px] bg-field px-3.5">
        <Search size={18} className="text-muted" />
        <span className="sr-only">Search rooms and equipment</span>
        <input
          autoFocus
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Room, ref or equipment"
          className="min-w-0 flex-1 bg-transparent py-3.5 text-base outline-none"
        />
      </label>
      <ul className="mt-3 grid min-h-0 flex-1 content-start gap-1.5 overflow-y-auto">
        {results.map((place) => (
          <li key={place.key}>
            <button
              type="button"
              onClick={() => onPick(place)}
              className="flex w-full items-center gap-3 rounded-[15px] bg-[#f5f5f1] p-3 text-left"
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-[11px] bg-white">
                {place.kind === "asset" ? <Package size={19} /> : <DoorOpen size={19} />}
              </span>
              <span className="grid min-w-0 flex-1 gap-0.5">
                <strong className="truncate text-[13px]">{place.label}</strong>
                <span className="truncate text-[11px] text-muted">{place.detail}</span>
              </span>
              <ChevronRight size={18} className="text-muted" />
            </button>
          </li>
        ))}
        {results.length === 0 && <li className="py-6 text-center text-sm text-muted">Nothing matches "{text}".</li>}
      </ul>
    </Sheet>
  );
}

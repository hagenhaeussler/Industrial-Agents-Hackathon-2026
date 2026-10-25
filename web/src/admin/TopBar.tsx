import type { Building, FloorScene } from "@building/view";
import { Blobatar } from "@blobatar/react";
import { DoorOpen, Package, QrCode, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { searchPlaces } from "../route/places";
import { MEMBERS } from "./team";
import type { Selection } from "./Workspace";
import type { View } from "./Sidebar";

const TITLES: Record<View, string> = {
  model: "3D building",
  plans: "Floor plans",
  routes: "Routes",
  equipment: "Equipment",
};

/** Title, floor focus, search, who else is here, and sharing. */
export function TopBar({
  document,
  view,
  floors,
  focusFloor,
  onFocusFloor,
  onFind,
  onShare,
}: {
  document: Building;
  view: View;
  floors: FloorScene[];
  focusFloor: string | null;
  onFocusFloor: (floorId: string | null) => void;
  onFind: (selection: Selection) => void;
  onShare: () => void;
}) {
  return (
    <header className="flex items-center gap-3 border-b border-line bg-white px-4 py-2.5">
      <h1 className="shrink-0 text-[16px] font-[800] tracking-[-0.4px]">{TITLES[view]}</h1>
      <div role="radiogroup" aria-label="Floor" className="flex shrink-0 items-center gap-1 rounded-full bg-field p-1">
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
      <FindBox document={document} onFind={onFind} />
      <div className="ml-auto flex shrink-0 items-center gap-3">
        <div className="flex -space-x-2" aria-label={`${MEMBERS.length} people in this building`}>
          {MEMBERS.slice(0, 3).map((member) => (
            <span key={member.id} title={member.name} className="grid size-8 place-items-center rounded-full bg-white ring-2 ring-white">
              <Blobatar name={member.id} size={28} />
            </span>
          ))}
          <span className="grid size-8 place-items-center rounded-full bg-field text-[11px] font-[750] ring-2 ring-white">
            +{MEMBERS.length - 3}
          </span>
        </div>
        <button
          type="button"
          onClick={onShare}
          className="flex items-center gap-2 rounded-[11px] bg-ink px-3.5 py-2 text-[13px] font-[650] text-white"
        >
          <QrCode size={16} /> Send to phone
        </button>
      </div>
    </header>
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
      className={`grid h-7 min-w-7 place-items-center rounded-full px-2 text-xs font-[750] ${active ? "bg-ink text-white" : ""}`}
    >
      {label}
    </button>
  );
}

/** Search rooms and equipment. Choosing a result selects it in the view. */
function FindBox({ document, onFind }: { document: Building; onFind: (selection: Selection) => void }) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const results = useMemo(() => (text.trim() ? searchPlaces(document, text, 12) : []), [document, text]);
  const floorOf = (kind: "space" | "asset", id: string) =>
    (kind === "asset"
      ? document.assets.find((asset) => asset.id === id)?.floor_id
      : document.spaces.find((space) => space.id === id)?.floor_id) ?? "";
  return (
    <div className="relative w-full max-w-[360px] min-w-[180px]">
      <label className="flex items-center gap-2 rounded-[11px] bg-field px-3">
        <Search size={16} className="text-muted" />
        <span className="sr-only">Search rooms and equipment</span>
        <input
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Search rooms and equipment"
          className="min-w-0 flex-1 bg-transparent py-2 text-[13px] outline-none"
        />
      </label>
      {open && results.length > 0 && (
        <ul className="float absolute inset-x-0 top-full z-20 mt-1.5 grid max-h-[360px] overflow-y-auto rounded-[14px] p-1.5">
          {results.map((place) => (
            <li key={place.key}>
              <button
                type="button"
                onClick={() => {
                  onFind({ kind: place.kind, id: place.key, floorId: floorOf(place.kind, place.key) });
                  setText(place.label);
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-left hover:bg-field"
              >
                {place.kind === "asset" ? <Package size={16} /> : <DoorOpen size={16} />}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-[650]">{place.label}</span>
                  <span className="block truncate text-[11px] text-muted">{place.detail}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

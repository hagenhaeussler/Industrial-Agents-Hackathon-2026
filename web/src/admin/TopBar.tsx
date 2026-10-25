import type { Building, FloorScene } from "@locora/view";
import { CoworkerAvatar } from "./CoworkerAvatar";
import { DoorOpen, Package, QrCode, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { searchPlaces } from "../route/places";
import { FloorSelector } from "./FloorSelector";
import { MEMBERS } from "./team";
import type { Selection } from "./Workspace";
import type { View } from "./Sidebar";

/** Floor focus, search, AI coworkers and sharing. */
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
    <header className="@container min-w-0 shrink-0 border-b border-line bg-white px-4 py-2.5">
      <div className="flex min-w-0 items-center gap-3 @max-[520px]:flex-wrap">
        <FloorSelector floors={floors} view={view} focusFloor={focusFloor} onFocusFloor={onFocusFloor} />
        <FindBox document={document} onFind={onFind} />
        <div className="ml-auto flex shrink-0 items-center gap-3">
          <div className="hidden -space-x-2 xl:flex" aria-label={`${MEMBERS.length} AI coworkers in this building`}>
            {MEMBERS.slice(0, 3).map((member) => (
              <span key={member.id} title={`${member.name}, AI coworker`} className="grid size-8 place-items-center rounded-full bg-white ring-2 ring-white">
                <CoworkerAvatar id={member.id} size={28} />
              </span>
            ))}
            <span className="grid size-8 place-items-center rounded-full bg-field text-[11px] font-[750] ring-2 ring-white">
              +{MEMBERS.length - 3}
            </span>
          </div>
          <button
            type="button"
            onClick={onShare}
            aria-label="Send to phone"
            title="Send to phone"
            className="grid size-9 shrink-0 place-items-center rounded-[11px] bg-ink text-white"
          >
            <QrCode size={20} aria-hidden="true" />
          </button>
        </div>
      </div>
    </header>
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
    <div className="relative min-w-[180px] max-w-[360px] flex-1 @max-[520px]:order-last @max-[520px]:max-w-none @max-[520px]:basis-full">
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

import type { Building } from "@building/view";
import { ChevronRight, Search } from "lucide-react";
import { useMemo, useState } from "react";

/** Browse every equipment type and select an item by its name, ID or location. */
export function EquipmentBrowser({
  building,
  selectedId,
  onSelect,
}: {
  building: Building;
  selectedId: string | undefined;
  onSelect: (asset: Building["assets"][number]) => void;
}) {
  const [text, setText] = useState("");
  const [expandedType, setExpandedType] = useState<string>();
  const { groups, locations } = useMemo(() => {
    const floors = new Map(building.floors.map((floor) => [floor.id, floor.name]));
    const spaces = new Map(building.spaces.map((space) => [space.id, space]));
    const locations = new Map(building.assets.map((asset) => {
      const space = spaces.get(asset.space_id);
      return [asset.id, [space?.name, floors.get(asset.floor_id)].filter(Boolean).join(" · ")];
    }));
    const words = text.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const groups = new Map<string, Building["assets"]>();
    for (const asset of building.assets) {
      const fields = `${asset.name} ${asset.id} ${asset.type.replaceAll("_", " ")} ${spaces.get(asset.space_id)?.ref ?? ""} ${locations.get(asset.id)}`.toLowerCase();
      if (!words.every((word) => fields.includes(word))) continue;
      const items = groups.get(asset.type) ?? [];
      items.push(asset);
      groups.set(asset.type, items);
    }
    return { groups: [...groups].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0])), locations };
  }, [building, text]);

  return (
    <section aria-label="Equipment browser" className="my-2 text-[12px] text-[#b9bfb0]">
      <label className="mb-1 flex items-center gap-2 rounded-[8px] bg-side-hover px-2 focus-within:ring-2 focus-within:ring-accent">
        <Search size={14} aria-hidden="true" />
        <span className="sr-only">Search equipment</span>
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Name, ID or room"
          className="min-h-11 min-w-0 flex-1 bg-transparent text-white outline-none placeholder:text-[#9aa192]"
        />
      </label>
      {groups.length === 0 && <p role="status" className="px-2 py-3">{building.assets.length ? "No matching equipment." : "No equipment in this building."}</p>}
      {groups.map(([type, items]) => {
        const expanded = Boolean(text.trim()) || expandedType === type;
        const label = type.replaceAll("_", " ").toLowerCase();
        return (
          <div key={type}>
            <button
              type="button"
              aria-expanded={expanded}
              onClick={() => {
                setExpandedType(expandedType === type ? undefined : type);
                setText("");
              }}
              className="flex min-h-11 w-full items-center gap-1 rounded-[8px] px-2 text-left hover:bg-side-hover focus-visible:outline-2 focus-visible:outline-accent"
            >
              <ChevronRight size={14} aria-hidden="true" className={expanded ? "rotate-90" : ""} />
              <span className="min-w-0 flex-1 capitalize">{label}</span>
              <span className="text-[#9aa192]">{items.length}</span>
            </button>
            {expanded && (
              <ul aria-label={label} className="ml-3 border-l border-[#5d6455] pl-1">
                {items.map((asset) => (
                  <li key={asset.id}>
                    <button
                      type="button"
                      aria-pressed={selectedId === asset.id}
                      onClick={() => onSelect(asset)}
                      className={`min-h-11 w-full rounded-[8px] px-2 py-2 text-left break-words focus-visible:outline-2 focus-visible:outline-accent ${selectedId === asset.id ? "bg-accent font-[700] text-ink" : "hover:bg-side-hover"}`}
                    >
                      <span className="block">{asset.name}</span>
                      <span className="block text-[11px]">{asset.id}</span>
                      <span className="block text-[11px]">{locations.get(asset.id)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </section>
  );
}

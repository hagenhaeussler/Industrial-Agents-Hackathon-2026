import type { Building } from "@building/view";
import { Blobatar } from "@blobatar/react";
import { Box, ChevronDown, Hash, Layers, MapPin, Package, Plus, Route, Settings } from "lucide-react";
import type { ReactNode } from "react";
import { useBuildings } from "../api/buildings";
import { navigate } from "../router";
import { CHANNELS, MEMBERS, type Channel } from "./team";
import { EquipmentBrowser } from "./EquipmentBrowser";

export type View = "model" | "plans" | "routes" | "equipment";

const VIEWS: { view: View; label: string; Icon: typeof Box }[] = [
  { view: "model", label: "3D building", Icon: Box },
  { view: "plans", label: "Floor plans", Icon: Layers },
  { view: "routes", label: "Routes", Icon: Route },
  { view: "equipment", label: "Equipment", Icon: Package },
];

/** The dark left side: building switcher rail and the workspace sidebar. */
export function Sidebar({
  building,
  view,
  onView,
  selectedAssetId,
  onSelectEquipment,
  channel,
  onChannel,
  positionName,
  onSettings,
}: {
  building: Building;
  view: View;
  onView: (view: View) => void;
  selectedAssetId: string | undefined;
  onSelectEquipment: (asset: Building["assets"][number]) => void;
  channel: Channel | undefined;
  onChannel: (channel: Channel) => void;
  positionName: string | undefined;
  onSettings: () => void;
}) {
  return (
    <>
      <BuildingRail current={building.building.id} />
      <nav aria-label="Workspace" className="my-2 mr-2 flex min-h-0 flex-col rounded-[14px] bg-side py-2 text-[#e6e9df]">
        <button
          type="button"
          onClick={() => navigate("/")}
          className="mx-2 flex items-center gap-1 rounded-[10px] px-2 py-2 text-left hover:bg-side-hover"
        >
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[15px] font-[800] text-white">{building.building.name}</span>
            <span className="block truncate text-[11px] text-[#9aa192]">
              {building.floors.length} floors · {building.spaces.length} spaces
            </span>
          </span>
          <ChevronDown size={16} />
        </button>

        <div className="mt-3 min-h-0 flex-1 overflow-y-auto px-2">
          {VIEWS.map(({ view: value, label, Icon }) => (
            <SideItem key={value} active={view === value} onClick={() => onView(value)} icon={<Icon size={16} />}>
              {label}
            </SideItem>
          ))}

          {view === "equipment" && (
            <EquipmentBrowser building={building} selectedId={selectedAssetId} onSelect={onSelectEquipment} />
          )}

          <SectionTitle>Channels</SectionTitle>
          {CHANNELS.map((name) => (
            <SideItem key={name} active={channel === name} onClick={() => onChannel(name)} icon={<Hash size={15} />}>
              {name}
            </SideItem>
          ))}

          <SectionTitle>Direct messages</SectionTitle>
          {MEMBERS.map((member) => (
            <div key={member.id} className="flex items-center gap-2 rounded-[8px] px-2 py-1.5 text-[13px]">
              <span className="relative">
                <Blobatar name={member.id} size={20} />
                <span
                  className={`absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-side ${
                    member.status === "online" ? "bg-[#8bd450]" : "bg-[#8a8f84]"
                  }`}
                />
              </span>
              <span className="truncate">{member.name}</span>
            </div>
          ))}
        </div>

        <div className="mx-2 mt-2 flex items-center gap-2 rounded-[12px] bg-side-hover px-2.5 py-2">
          <MapPin size={16} className="shrink-0 text-accent" />
          <span className="min-w-0 flex-1">
            <span className="block text-[11px] text-[#9aa192]">You are at</span>
            <span className="block truncate text-[13px] font-[650] text-white">{positionName ?? "Not set"}</span>
          </span>
          <button type="button" onClick={onSettings} aria-label="Settings" className="grid size-8 place-items-center rounded-[8px] hover:bg-side">
            <Settings size={17} />
          </button>
        </div>
      </nav>
    </>
  );
}

/** Other buildings as tiles, like workspaces in a chat app. */
function BuildingRail({ current }: { current: string }) {
  const buildings = useBuildings();
  const others = (buildings.data ?? []).filter((building) => building.id !== current).slice(0, 4);
  const tile = (id: string, name: string, active: boolean) => (
    <button
      key={id}
      type="button"
      title={name}
      aria-label={`Open ${name}`}
      onClick={() => navigate(`/admin/${encodeURIComponent(id)}`)}
      className={`grid size-10 place-items-center rounded-[12px] text-[13px] font-[800] ${
        active ? "bg-accent text-ink ring-2 ring-white/80 ring-offset-2 ring-offset-rail" : "bg-side-hover text-white hover:bg-side"
      }`}
    >
      {initials(name)}
    </button>
  );
  return (
    <div className="flex flex-col items-center gap-2.5 py-3">
      {tile(current, buildings.data?.find((building) => building.id === current)?.name ?? current, true)}
      {others.map((building) => tile(building.id, building.name, false))}
      <button
        type="button"
        aria-label="All buildings"
        title="All buildings"
        onClick={() => navigate("/")}
        className="grid size-10 place-items-center rounded-[12px] border border-dashed border-[#5d6455] text-[#b9bfb0] hover:bg-side-hover"
      >
        <Plus size={18} />
      </button>
    </div>
  );
}

function SideItem({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`flex w-full items-center gap-2 rounded-[8px] px-2 py-1.5 text-left text-[13px] ${
        active ? "bg-accent font-[700] text-ink" : "hover:bg-side-hover"
      }`}
    >
      {icon}
      <span className="truncate">{children}</span>
    </button>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className="mt-5 mb-1 px-2 text-[11px] font-[750] tracking-wide text-[#9aa192] uppercase">{children}</h3>;
}

function initials(name: string) {
  const words = name.split(/\s+/).filter(Boolean);
  return ((words[0]?.[0] ?? "") + (words[1]?.[0] ?? "")).toUpperCase() || "?";
}

import type { Building } from "@building/view";
import { Fullscreen, LocateFixed, MousePointer2, Move, Navigation, Package, Tag, X } from "lucide-react";
import type { ReactNode } from "react";
import type { Selection } from "./Workspace";

export type Tool = "select" | "position" | "move";

const HINTS: Record<Tool, string | undefined> = {
  select: undefined,
  position: "Click the room where you are.",
  move: "Click the new place for the selected equipment.",
};

/** Floating tools over the building view. */
export function CanvasTools({
  onResetView,
  tool,
  onTool,
  canMove,
  labels,
  onLabels,
  assets,
  onAssets,
}: {
  onResetView?: () => void;
  tool: Tool;
  onTool: (tool: Tool) => void;
  canMove: boolean;
  labels: boolean;
  onLabels: (value: boolean) => void;
  assets: boolean;
  onAssets: (value: boolean) => void;
}) {
  const hint = HINTS[tool];
  return (
    <>
      <div className="float absolute top-3 left-3 z-10 flex flex-col gap-1 rounded-[14px] p-1">
        <ToolButton label="Select" active={tool === "select"} onClick={() => onTool("select")}>
          <MousePointer2 size={18} />
        </ToolButton>
        <ToolButton label="Set my position" active={tool === "position"} onClick={() => onTool(tool === "position" ? "select" : "position")}>
          <LocateFixed size={18} />
        </ToolButton>
        <ToolButton label="Move equipment" active={tool === "move"} disabled={!canMove} onClick={() => onTool(tool === "move" ? "select" : "move")}>
          <Move size={18} />
        </ToolButton>
        <span className="mx-2 my-0.5 h-px bg-line" />
        <ToolButton label="Room names" active={labels} onClick={() => onLabels(!labels)}>
          <Tag size={18} />
        </ToolButton>
        <ToolButton label="Equipment" active={assets} onClick={() => onAssets(!assets)}>
          <Package size={18} />
        </ToolButton>
        {onResetView && (
          <>
            <span className="mx-2 my-0.5 h-px bg-line" />
            <ToolButton label="Show the whole building" active={false} onClick={onResetView}>
              <Fullscreen size={18} />
            </ToolButton>
          </>
        )}
      </div>
      {hint && (
        <p className="float absolute top-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-accent px-4 py-2 text-[13px] font-[650] text-ink">
          {hint}{" "}
          <button type="button" onClick={() => onTool("select")} className="ml-1 text-ink underline">
            Cancel
          </button>
        </p>
      )}
    </>
  );
}

function ToolButton({
  label,
  active,
  disabled,
  onClick,
  children,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      aria-pressed={active}
      className={`grid size-10 place-items-center rounded-[10px] ${active ? "bg-accent text-ink" : "hover:bg-field"}`}
    >
      {children}
    </button>
  );
}

/** The selected room or equipment with what you can do with it. */
export function SelectionCard({
  document,
  selection,
  isPosition,
  onClose,
  onHere,
  onRoute,
  onMove,
}: {
  document: Building;
  selection: Selection;
  isPosition: boolean;
  onClose: () => void;
  onHere: (spaceId: string) => void;
  onRoute: (spaceId: string) => void;
  onMove: () => void;
}) {
  const asset = selection.kind === "asset" ? document.assets.find((item) => item.id === selection.id) : undefined;
  const space = document.spaces.find((item) => item.id === (asset ? asset.space_id : selection.id));
  if (!space) return null;
  const floor = document.floors.find((item) => item.id === space.floor_id);
  return (
    <section aria-label="Selection" className="float absolute bottom-3 left-3 z-10 w-[320px] rounded-[18px] p-4">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-[700] tracking-wide text-muted uppercase">{(asset ? asset.type : space.room_type).replaceAll("_", " ")}</p>
          <h2 className="truncate text-[17px] font-[800] tracking-[-0.4px]">{asset ? asset.name : space.name}</h2>
          <p className="truncate text-xs text-muted">
            {asset ? `${space.name} · ` : ""}
            {floor?.name}
          </p>
        </div>
        <button type="button" onClick={onClose} aria-label="Clear selection" className="grid size-8 place-items-center rounded-[9px] bg-field">
          <X size={16} />
        </button>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => onRoute(space.id)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-[11px] bg-ink px-3 py-2.5 text-[13px] font-[650] text-white"
        >
          <Navigation size={15} /> Route here
        </button>
        <button
          type="button"
          onClick={() => onHere(space.id)}
          disabled={isPosition}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-[11px] bg-field px-3 py-2.5 text-[13px] font-[650]"
        >
          <LocateFixed size={15} /> {isPosition ? "You are here" : "I'm here"}
        </button>
        {asset && (
          <button type="button" onClick={onMove} aria-label="Move equipment" title="Move equipment" className="grid size-10 place-items-center rounded-[11px] bg-field">
            <Move size={16} />
          </button>
        )}
      </div>
    </section>
  );
}

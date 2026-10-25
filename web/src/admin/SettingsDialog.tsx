import { RotateCcw } from "lucide-react";
import { Sheet } from "../ui/Sheet";

/** Workspace settings. The only place that says which parts of the workspace are a preview. */
export function SettingsDialog({
  open,
  onClose,
  movedCount,
  onResetMoves,
}: {
  open: boolean;
  onClose: () => void;
  movedCount: number;
  onResetMoves: () => void;
}) {
  return (
    <Sheet open={open} onClose={onClose} title="Settings">
      <div className="grid gap-4 pb-1 text-[13px]">
        <section className="grid gap-2">
          <h3 className="font-[750]">Moved equipment</h3>
          <p className="text-muted">
            {movedCount === 0 ? "Nothing moved." : `${movedCount} ${movedCount === 1 ? "item" : "items"} moved in this browser.`}
          </p>
          <button
            type="button"
            onClick={onResetMoves}
            disabled={movedCount === 0}
            className="flex w-fit items-center gap-2 rounded-[11px] bg-field px-3 py-2 font-[650]"
          >
            <RotateCcw size={15} /> Put everything back
          </button>
        </section>
        <section className="grid gap-1.5 rounded-[14px] bg-field p-3.5 text-xs leading-relaxed">
          <h3 className="text-[13px] font-[750]">Preview features</h3>
          <p>Team members, channels, messages and presence are sample content. Messages stay in this browser.</p>
          <p>Moving equipment changes only this browser's view. The building data and routes do not change.</p>
          <p>Routes, rooms and equipment come from the building data. The assistant answers from the same building tools.</p>
        </section>
      </div>
    </Sheet>
  );
}

import type { BuildingSummary } from "@locora/view";
import { Smartphone } from "lucide-react";
import { navigate } from "../router";
import { ImportBuilding } from "./ImportBuilding";

/** A demo slot, never fabricated geometry. A real named upload replaces the waiting state. */
export function DemoBuilding({ buildings }: { buildings: BuildingSummary[] }) {
  const demo = buildings.find((building) => building.name.trim().toLowerCase() === "demo");
  return <section aria-label="Demo building" className="float grid gap-3 rounded-[24px] p-5">
    <div className="flex items-center justify-between gap-3">
      <h2 className="text-xl font-[750]">Demo</h2>
      <span className="rounded-full bg-field px-3 py-1 text-xs font-[650]">{demo ? "Plan ready" : "Awaiting building.json"}</span>
    </div>
    <p className="text-sm leading-relaxed text-muted">{demo
      ? "Open the guide to navigate and take an object photo at your destination. Camera tracking needs the matching localization scan."
      : "Your new office will appear here when its JSON is ready. Name the building Demo in the file. Camera tracking also needs a scan of this office; the plan alone cannot locate you."}</p>
    {demo ? <div className="flex flex-wrap gap-2">
      <button type="button" onClick={() => navigate(`/admin/${encodeURIComponent(demo.id)}`)}
        className="rounded-xl bg-ink px-4 py-3 text-sm font-[700] text-white">Open Demo workspace</button>
      <button type="button" onClick={() => navigate(`/b/${encodeURIComponent(demo.id)}`)}
        className="flex items-center gap-2 rounded-xl bg-field px-4 py-3 text-sm font-[700]"><Smartphone size={17} /> Open Demo guide</button>
    </div> : <ImportBuilding label="Add Demo JSON" inputLabel="Demo building JSON file" />}
  </section>;
}

import { Building2, ChevronRight, Globe2, Monitor, Smartphone } from "lucide-react";
import { useMemo, useState } from "react";
import { useBuildings } from "../api/buildings";
import { Avatar } from "../avatar/Avatar";
import { navigate } from "../router";

/** Pick a building, then open it on the desktop workspace or as the phone guide. */
export function Home() {
  const buildings = useBuildings();
  const [text, setText] = useState("");
  const shown = useMemo(
    () =>
      (buildings.data ?? []).filter((building) =>
        `${building.name} ${building.id}`.toLowerCase().includes(text.trim().toLowerCase()),
      ),
    [buildings.data, text],
  );
  return (
    <main className="mx-auto grid max-w-[720px] gap-6 px-5 py-10">
      <header className="flex flex-wrap items-center gap-4">
        <Avatar phase="off" size={84} />
        <div className="min-w-0 flex-1">
          <h1 className="text-[30px] leading-tight font-[800] tracking-[-1.2px]">Locora</h1>
          <p className="mt-1 text-sm text-muted">Choose a building to explore, plan a route or send it to a phone.</p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/explore")}
          className="flex items-center justify-center gap-2 rounded-[13px] bg-accent px-4 py-3 text-sm font-[750] text-ink sm:ml-auto"
        >
          <Globe2 size={17} /> Explore on globe
        </button>
      </header>
      <input
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Search buildings"
        aria-label="Search buildings"
        className="float rounded-[16px] px-4 py-3.5 text-base outline-none"
      />
      {buildings.isError && <p className="text-sm text-danger">{buildings.error.message}</p>}
      <ul className="float grid overflow-hidden rounded-[20px]">
        {shown.slice(0, 60).map((building) => (
          <li key={building.id} className="flex items-center gap-3 border-b border-line px-4 py-3 last:border-0">
            <Building2 size={20} className="shrink-0 text-muted" />
            <span className="grid min-w-0 flex-1">
              <strong className="truncate text-sm">{building.name}</strong>
              <span className="truncate text-xs text-muted">
                {building.floors} {building.floors === 1 ? "floor" : "floors"} · {building.id}
              </span>
            </span>
            <button
              type="button"
              onClick={() => navigate(`/admin/${encodeURIComponent(building.id)}`)}
              className="flex items-center gap-1.5 rounded-[11px] bg-ink px-3 py-2 text-xs font-[650] text-white"
            >
              <Monitor size={15} /> Workspace
            </button>
            <button
              type="button"
              onClick={() => navigate(`/b/${encodeURIComponent(building.id)}`)}
              aria-label={`Open ${building.name} as phone guide`}
              className="flex items-center gap-1 rounded-[11px] bg-field px-3 py-2 text-xs font-[650]"
            >
              <Smartphone size={15} /> Guide <ChevronRight size={14} />
            </button>
          </li>
        ))}
        {buildings.isPending && <li className="px-4 py-6 text-center text-sm text-muted">Loading buildings…</li>}
      </ul>
    </main>
  );
}

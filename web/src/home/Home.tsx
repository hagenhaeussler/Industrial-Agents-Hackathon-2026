import type { BuildingSummary } from "@locora/view";
import { Building2, Check, Monitor, Search, Smartphone } from "lucide-react";
import { useMemo, useState } from "react";
import { useBuildings } from "../api/buildings";
import { Avatar } from "../avatar/Avatar";
import { navigate } from "../router";
import { floorLabel, groupBuildings, matches, type Collection } from "./collections";
import { PlanThumb } from "./PlanThumb";

const PAGE = 20;

/** Start from an illustrated collection, then pick a building by its floor plan. A search looks through all of them. */
export function Home() {
  const buildings = useBuildings();
  const [text, setText] = useState("");
  const [collectionId, setCollectionId] = useState<string>();
  const [limit, setLimit] = useState(PAGE);

  const collections = useMemo(() => groupBuildings(buildings.data ?? []), [buildings.data]);
  const collection = collections.find((item) => item.id === collectionId) ?? collections[0];
  const searching = text.trim() !== "";
  const shown = searching
    ? (buildings.data ?? []).filter((building) => matches(building, text))
    : (collection?.buildings ?? []);

  function open(id: string) {
    setCollectionId(id);
    setText("");
    setLimit(PAGE);
  }

  return (
    <main className="mx-auto grid max-w-[1240px] gap-10 px-6 pt-6 pb-16">
      <header className="flex flex-wrap items-center gap-4">
        <span className="flex items-center gap-3">
          <Avatar phase="off" size={48} />
          <strong className="text-xl font-[800] tracking-[-0.8px]">Locora</strong>
        </span>
        <label className="float ml-auto flex w-full items-center gap-2.5 rounded-[16px] px-4 py-3 focus-within:ring-2 focus-within:ring-accent-deep sm:w-[340px]">
          <Search size={17} className="text-muted" />
          <input
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              setLimit(PAGE);
            }}
            placeholder="Search all buildings"
            aria-label="Search buildings"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
          />
        </label>
      </header>

      <div className="grid items-end gap-4 lg:grid-cols-[1fr_380px]">
        <h1 className="text-[clamp(32px,4.4vw,52px)] leading-[1.02] font-[800] tracking-[-2px]">
          Which building are we in today?
        </h1>
        <p className="text-[15px] leading-relaxed text-muted">
          Pick a place. Plan a route in 3D on the big screen, then take it along on your phone.
        </p>
      </div>

      {buildings.isError && <p className="text-sm text-danger">{buildings.error.message}</p>}
      {buildings.isPending && <p className="text-sm text-muted">Loading buildings…</p>}

      <nav aria-label="Collections" className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {collections.map((item) => (
          <CollectionCard
            key={item.id}
            collection={item}
            active={!searching && item.id === collection?.id}
            onClick={() => open(item.id)}
          />
        ))}
      </nav>

      <section aria-labelledby="shelf-title" className="grid gap-5">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="shelf-title" className="text-[22px] font-[800] tracking-[-0.8px]">
            {searching ? `Results for "${text.trim()}"` : collection?.label}
          </h2>
          <span className="text-sm text-muted">
            {shown.length} {shown.length === 1 ? "building" : "buildings"}
          </span>
        </div>
        {searching && shown.length === 0 && <p className="text-sm text-muted">No building matches this search.</p>}
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
          {shown.slice(0, limit).map((building) => (
            <li key={building.id}>
              <BuildingCard building={building} />
            </li>
          ))}
        </ul>
        {shown.length > limit && (
          <button
            type="button"
            onClick={() => setLimit(limit + PAGE)}
            className="float mx-auto rounded-[14px] px-5 py-3 text-sm font-[650]"
          >
            Show {Math.min(PAGE, shown.length - limit)} more
          </button>
        )}
      </section>
    </main>
  );
}

function CollectionCard({
  collection,
  active,
  onClick,
}: {
  collection: Collection;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`group relative grid content-start gap-3 rounded-[28px] bg-white p-2.5 pb-4 text-left shadow-float ${
        active ? "ring-2 ring-ink" : "hover:-translate-y-0.5 hover:shadow-[0_14px_40px_#20251b1f]"
      } transition-[translate,box-shadow] duration-200`}
    >
      <span className="grid aspect-[5/4] place-items-center overflow-hidden rounded-[21px] bg-paper">
        {collection.art ? (
          <img
            src={collection.art}
            alt=""
            className="size-full scale-[1.08] object-cover transition-transform duration-300 group-hover:scale-[1.14]"
          />
        ) : (
          <Building2 size={56} strokeWidth={1.4} className="text-muted" />
        )}
      </span>
      {active && (
        <span className="absolute top-5 right-5 grid size-8 place-items-center rounded-full bg-accent text-ink">
          <Check size={17} strokeWidth={2.6} />
        </span>
      )}
      <span className="grid gap-1 px-2">
        <strong className="text-[17px] font-[750] tracking-[-0.4px]">{collection.label}</strong>
        <span className="text-[13px] leading-snug text-muted">{collection.blurb}</span>
        <span className="mt-1 text-xs font-[650]">
          {collection.buildings.length} buildings · {floorLabel(collection.buildings.map((b) => b.floors))}
        </span>
      </span>
    </button>
  );
}

function BuildingCard({ building }: { building: BuildingSummary }) {
  const id = encodeURIComponent(building.id);
  return (
    <article className="float grid gap-3 rounded-[24px] p-2.5">
      <PlanThumb buildingId={building.id} className="aspect-[4/3] rounded-[17px] bg-field p-3" />
      <div className="grid gap-0.5 px-1.5">
        <strong className="truncate text-sm font-[750]">{building.name}</strong>
        <span className="text-xs text-muted">{floorLabel([building.floors])}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => navigate(`/admin/${id}`)}
          className="flex items-center justify-center gap-1.5 rounded-[13px] bg-ink px-3 py-2.5 text-xs font-[700] text-white"
        >
          <Monitor size={15} className="shrink-0" /> Workspace
        </button>
        <button
          type="button"
          onClick={() => navigate(`/b/${id}`)}
          aria-label={`Open ${building.name} as phone guide`}
          className="flex items-center justify-center gap-1.5 rounded-[13px] bg-field px-3 py-2.5 text-xs font-[700]"
        >
          <Smartphone size={15} className="shrink-0" /> Guide
        </button>
      </div>
    </article>
  );
}

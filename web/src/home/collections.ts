import type { BuildingSummary } from "@locora/view";
import apartments from "./art/apartments.webp";
import campus from "./art/campus.webp";
import homes from "./art/homes.webp";
import places from "./art/places.webp";

/** A group of buildings by data source, with an illustration. Buildings from unknown sources go to "Other". */
export interface Collection {
  id: string;
  label: string;
  blurb: string;
  art?: string;
  buildings: BuildingSummary[];
}

const KNOWN: (Omit<Collection, "buildings"> & { sources: string[] })[] = [
  {
    id: "campus",
    label: "Campus and industry",
    blurb: "Labs, lecture halls and production sites",
    art: campus,
    sources: ["procedural"],
  },
  {
    id: "places",
    label: "Real places",
    blurb: "Mapped from OpenStreetMap or scanned on site",
    art: places,
    sources: ["osm_indoor", "scan"],
  },
  {
    id: "apartments",
    label: "Apartment blocks",
    blurb: "Stacked flats with stairs and lifts",
    art: apartments,
    sources: ["swiss_dwellings"],
  },
  { id: "homes", label: "Homes", blurb: "Single-floor residential plans", art: homes, sources: ["resplan"] },
];

/** Sort buildings into collections. Empty collections are left out. */
export function groupBuildings(buildings: BuildingSummary[]): Collection[] {
  const groups: Collection[] = KNOWN.map(({ sources, ...collection }) => ({
    ...collection,
    buildings: buildings.filter((building) => sources.includes(building.source)),
  }));
  const known = new Set(KNOWN.flatMap((collection) => collection.sources));
  groups.push({
    id: "other",
    label: "Other buildings",
    blurb: "Buildings from other sources",
    buildings: buildings.filter((building) => !known.has(building.source)),
  });
  return groups.filter((group) => group.buildings.length > 0);
}

/** "3 floors", or a range such as "1–7 floors" for a group. */
export function floorLabel(floors: number[]): string {
  const low = Math.min(...floors);
  const high = Math.max(...floors);
  if (low === high) return `${low} ${low === 1 ? "floor" : "floors"}`;
  return `${low}–${high} floors`;
}

export function matches(building: BuildingSummary, text: string): boolean {
  return `${building.name} ${building.id}`.toLowerCase().includes(text.trim().toLowerCase());
}

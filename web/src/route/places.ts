import type { Building } from "@locora/view";

/** A room or a piece of equipment the user can pick. Equipment leads to the space that holds it. */
export interface PlaceOption {
  key: string;
  spaceId: string;
  label: string;
  detail: string;
  kind: "space" | "asset";
}

const WALKABLE = new Set(["room", "corridor", "hall", "outdoor"]);

/** Spaces and equipment whose name, ref or type contains every word of `text`. */
export function searchPlaces(building: Building, text: string, limit = 40): PlaceOption[] {
  const words = text.toLowerCase().split(/\s+/).filter(Boolean);
  const floorName = new Map(building.floors.map((floor) => [floor.id, floor.name]));
  const spaceName = new Map(building.spaces.map((space) => [space.id, space.name]));
  const matches = (...fields: string[]) => {
    const haystack = fields.join(" ").toLowerCase();
    return words.every((word) => haystack.includes(word));
  };
  const spaces: PlaceOption[] = building.spaces
    .filter((space) => WALKABLE.has(space.type) && matches(space.name, space.ref, space.room_type))
    .map((space) => ({
      key: space.id,
      spaceId: space.id,
      label: space.name,
      detail: floorName.get(space.floor_id) ?? "",
      kind: "space",
    }));
  const assets: PlaceOption[] =
    words.length === 0
      ? []
      : building.assets
          .filter((asset) => matches(asset.name, asset.type))
          .map((asset) => ({
            key: asset.id,
            spaceId: asset.space_id,
            label: asset.name,
            detail: `${spaceName.get(asset.space_id) ?? ""} · ${floorName.get(asset.floor_id) ?? ""}`,
            kind: "asset",
          }));
  return [...spaces, ...assets].sort((a, b) => a.label.localeCompare(b.label, "en", { numeric: true })).slice(0, limit);
}

export function spaceName(building: Building, spaceId: string | undefined): string | undefined {
  return building.spaces.find((space) => space.id === spaceId)?.name;
}

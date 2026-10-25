// Vertical layout of the exploded view. Kept free of three.js, so it is easy to test and reuse.
import type { FloorScene } from "../scene/types";

/**
 * Height of each floor's base in the exploded view: its real elevation plus `gap` metres for every floor
 * below it. Floors must be ordered by level, as compileScene returns them.
 */
export function floorOffsets(floors: readonly Pick<FloorScene, "id" | "elevation">[], gap: number): Map<string, number> {
  return new Map(floors.map((floor, rank) => [floor.id, floor.elevation + rank * gap]));
}

/** Asset heights are not in building.json. These are display values per category. */
export function assetHeight(category: string): number {
  switch (category) {
    case "furniture":
      return 0.75;
    case "machine":
      return 1.8;
    case "fixture":
      return 1.2;
    default:
      return 1.0;
  }
}

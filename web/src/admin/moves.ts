import type { Building } from "@building/view";

/** A piece of equipment moved in the workspace preview. Kept in the browser only. */
export interface Move {
  assetId: string;
  floorId: string;
  spaceId: string;
  x: number;
  y: number;
}

/** The building with the moved equipment at its new places. The stored building does not change. */
export function applyMoves(building: Building, moves: Move[]): Building {
  if (moves.length === 0) return building;
  const latest = new Map(moves.map((move) => [move.assetId, move]));
  return {
    ...building,
    assets: building.assets.map((asset) => {
      const move = latest.get(asset.id);
      if (!move) return asset;
      const position: [number, number] = [move.x, move.y];
      return { ...asset, floor_id: move.floorId, space_id: move.spaceId, position };
    }),
  };
}

// Walls are not part of building.json. Every space edge becomes a wall, and every opening of the space cuts
// a gap of its width into the space's nearest edge. The same rule fits rooms that touch (procedural, OSM)
// and rooms with a wall-thick gap between them (Swiss Dwellings, ResPlan).
import { edges, projectOnSegment, roundPoint } from "./geometry";
import type { Point, Wall } from "./types";

/** An opening farther than this from every edge of a space cuts no gap into that space. */
export const OPENING_REACH_M = 1.0;
/** Wall pieces left shorter than this beside a gap are dropped. */
export const MIN_WALL_M = 0.05;

interface OpeningLike {
  id: string;
  position: Point;
  width: number;
}

/**
 * The walls of one space, and for each opening that cut a gap, the unit vector of the cut edge.
 * Openings must belong to the space.
 */
export function spaceWalls(
  spaceId: string,
  outline: readonly Point[],
  openings: readonly OpeningLike[],
): { walls: Wall[]; directions: Map<string, Point> } {
  const spaceEdges = edges(outline);
  const gaps: [number, number][][] = spaceEdges.map(() => []);
  const directions = new Map<string, Point>();

  for (const opening of openings) {
    let nearest: { index: number; distance: number; along: number } | undefined;
    spaceEdges.forEach(([start, end], index) => {
      const projection = projectOnSegment(opening.position, start, end);
      if (!nearest || projection.distance < nearest.distance) nearest = { index, ...projection };
    });
    if (!nearest || nearest.distance > OPENING_REACH_M) continue;
    gaps[nearest.index]!.push([nearest.along - opening.width / 2, nearest.along + opening.width / 2]);
    const [start, end] = spaceEdges[nearest.index]!;
    const length = Math.hypot(end[0] - start[0], end[1] - start[1]);
    directions.set(opening.id, roundPoint((end[0] - start[0]) / length, (end[1] - start[1]) / length));
  }

  const walls: Wall[] = [];
  spaceEdges.forEach(([start, end], index) => {
    const length = Math.hypot(end[0] - start[0], end[1] - start[1]);
    for (const [from, to] of remainingPieces(length, gaps[index]!)) {
      const at = (distance: number) =>
        roundPoint(start[0] + ((end[0] - start[0]) * distance) / length, start[1] + ((end[1] - start[1]) * distance) / length);
      walls.push({ spaceId, start: at(from), end: at(to) });
    }
  });
  return { walls, directions };
}

/** The parts of [0, length] that no gap covers, without pieces shorter than MIN_WALL_M. */
function remainingPieces(length: number, gaps: [number, number][]): [number, number][] {
  const pieces: [number, number][] = [];
  let cursor = 0;
  for (const [from, to] of [...gaps].sort((a, b) => a[0] - b[0])) {
    if (from > cursor) pieces.push([cursor, Math.min(from, length)]);
    cursor = Math.max(cursor, to);
  }
  if (cursor < length) pieces.push([cursor, length]);
  return pieces.filter(([from, to]) => to - from >= MIN_WALL_M);
}

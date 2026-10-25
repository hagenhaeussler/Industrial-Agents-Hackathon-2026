// Small planar helpers shared by the scene compiler. Results are rounded to millimetres, so the same
// building always gives the same numbers.
import type { Bounds, Point } from "./types";

export function round(value: number): number {
  return Math.round(value * 1000) / 1000 + 0; // + 0 turns -0 into 0
}

export function roundPoint(x: number, y: number): Point {
  return [round(x), round(y)];
}

/** Each polygon edge as [start, end], including the closing edge. */
export function edges(outline: readonly Point[]): [Point, Point][] {
  return outline.map((start, index) => [start, outline[(index + 1) % outline.length]!]);
}

/** Distance from `point` to the segment, and the distance along the segment to the closest point. */
export function projectOnSegment(point: Point, start: Point, end: Point): { distance: number; along: number } {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const length = Math.hypot(dx, dy);
  if (length === 0) return { distance: Math.hypot(point[0] - start[0], point[1] - start[1]), along: 0 };
  const along = Math.min(length, Math.max(0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length));
  const x = start[0] + (dx * along) / length;
  const y = start[1] + (dy * along) / length;
  return { distance: Math.hypot(point[0] - x, point[1] - y), along };
}

export function boundsOf(points: Iterable<Point>): Bounds {
  const bounds = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
  for (const [x, y] of points) {
    bounds.minX = Math.min(bounds.minX, x);
    bounds.minY = Math.min(bounds.minY, y);
    bounds.maxX = Math.max(bounds.maxX, x);
    bounds.maxY = Math.max(bounds.maxY, y);
  }
  return bounds;
}

/** Plain code-unit order. Unlike localeCompare it does not depend on the runtime's locale. */
export function byId<T extends { id: string }>(a: T, b: T): number {
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

import type { Point } from '../api/types';

/**
 * The one building → SVG transform for the 2D map (CONTRACTS §11): building metres, x right, y up;
 * SVG y grows down, so `screen_y = -y`. Rooms, assets, routes, positions and labels all go through it,
 * which keeps text upright without a separate un-flipped layer.
 */
export const toSvg = ([x, y]: Point): Point => [x, -y];

export const svgPoints = (points: readonly Point[]): string => points.map(point => toSvg(point).join(',')).join(' ');

export type Box = { minX: number; minY: number; maxX: number; maxY: number };

export function bounds(points: Iterable<Point>): Box | null {
  let box: Box | null = null;
  for (const [x, y] of points) {
    if (!box) box = { minX: x, minY: y, maxX: x, maxY: y };
    else { box.minX = Math.min(box.minX, x); box.minY = Math.min(box.minY, y); box.maxX = Math.max(box.maxX, x); box.maxY = Math.max(box.maxY, y); }
  }
  return box;
}

/** SVG viewBox of a building-space box, padded by `pad` metres. */
export function viewBox(box: Box, pad = 2): string {
  return `${box.minX - pad} ${-box.maxY - pad} ${box.maxX - box.minX + 2 * pad} ${box.maxY - box.minY + 2 * pad}`;
}

export function centroid(polygon: readonly Point[]): Point {
  let area = 0, cx = 0, cy = 0;
  for (let i = 0; i < polygon.length; i++) {
    const [x1, y1] = polygon[i]!;
    const [x2, y2] = polygon[(i + 1) % polygon.length]!;
    const cross = x1 * y2 - x2 * y1;
    area += cross; cx += (x1 + x2) * cross; cy += (y1 + y2) * cross;
  }
  if (Math.abs(area) < 1e-9) return polygon[0] ?? [0, 0];
  return [cx / (3 * area), cy / (3 * area)];
}

/** Direction of the polygon edge nearest to `point`, as a unit vector (for drawing door gaps along the wall). */
export function wallDirection(polygon: readonly Point[], point: Point): Point {
  let best = Infinity, dir: Point = [1, 0];
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i]!, b = polygon[(i + 1) % polygon.length]!;
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const len2 = dx * dx + dy * dy;
    if (len2 === 0) continue;
    const t = Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / len2));
    const ex = a[0] + t * dx - point[0], ey = a[1] + t * dy - point[1];
    const d = ex * ex + ey * ey;
    if (d < best) { best = d; const len = Math.sqrt(len2); dir = [dx / len, dy / len]; }
  }
  return dir;
}

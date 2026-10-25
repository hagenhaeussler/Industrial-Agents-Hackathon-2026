import type { Point } from '../api/types';
import { bounds, toSvg } from './transform';
import type { Box } from './transform';

/** Equal-length SVG plane axes at 30° and 150°; apply only after the normal toSvg y-flip. */
export const ISOMETRIC_COS = Math.sqrt(3) / 2;
export const ISOMETRIC_SIN = 0.5;

export type IsometricLayout = {
  /** Building footprint center after toSvg: [building center x, negative building center y]. */
  centerSvg: Point;
  floorCount: number;
  /** Centered plane bounds in projected screen coordinates, before the floor's vertical offset. */
  footprint: Box;
  /** Diagram separation and slab thickness, not measured building heights or route lengths. */
  gap: number;
  slab: number;
  /** Stable screen-space bounds, including slabs and spare room for a small focus pan. */
  scene: Box;
};

function finiteBox(box: Box): Box {
  if (![box.minX, box.minY, box.maxX, box.maxY].every(Number.isFinite)) throw new RangeError('Isometric bounds must be finite.');
  const result = { minX: Math.min(box.minX, box.maxX), minY: Math.min(box.minY, box.maxY), maxX: Math.max(box.minX, box.maxX), maxY: Math.max(box.minY, box.maxY) };
  if (!Number.isFinite(result.maxX - result.minX) || !Number.isFinite(result.maxY - result.minY)) throw new RangeError('Isometric bounds are too large.');
  return result;
}

const corners = (box: Box): Point[] => [[box.minX, box.minY], [box.maxX, box.minY], [box.maxX, box.maxY], [box.minX, box.maxY]];

function floorRank(layout: IsometricLayout, rank: number): number {
  if (!Number.isFinite(rank)) throw new RangeError('The visual floor rank must be finite.');
  return Math.max(0, Math.min(layout.floorCount - 1, Math.floor(rank)));
}

/**
 * One layout per building footprint/floor count. Pass floors in ascending physical order and use their
 * zero-based rank, including basements. Actual level numbers/elevations must not be used as array ranks.
 * Extra separation deliberately exposes the floors; it never changes core geometry or distance values.
 */
export function createIsometricLayout(box: Box, floorCount: number): IsometricLayout {
  const source = finiteBox(box);
  const width = source.maxX - source.minX, height = source.maxY - source.minY;
  const centerSvg: Point = [source.minX + width / 2, -(source.minY + height / 2)];
  const count = Number.isFinite(floorCount) ? Math.max(1, Math.floor(floorCount)) : 1;
  const maxSpan = Math.max(width, height, 1);
  const halfWidth = ISOMETRIC_COS * (width + height) / 2;
  const halfHeight = ISOMETRIC_SIN * (width + height) / 2;
  const footprint = { minX: -halfWidth, minY: -halfHeight, maxX: halfWidth, maxY: halfHeight };
  const slab = maxSpan * 0.025;
  const gap = Math.max(halfHeight * 2, 1) * 1.01 + slab;
  const padX = Math.max(halfWidth * 2 * 0.16, slab * 3, 1);
  const padY = Math.max(halfHeight * 2 * 0.38, slab * 3, 1);
  const scene = { minX: footprint.minX - padX, minY: footprint.minY - (count - 1) * gap - padY, maxX: footprint.maxX + padX, maxY: footprint.maxY + slab + padY };
  if (![...Object.values(scene), gap, slab].every(Number.isFinite)) throw new RangeError('The isometric scene is too large.');
  return { centerSvg, floorCount: count, footprint, gap, slab, scene };
}

/** SVG point → centered isometric screen point. Rank 0 is lowest; increasing ranks move upward. */
export function isometricSvgPoint(layout: IsometricLayout, svgPoint: Point, rank: number): Point {
  if (!svgPoint.every(Number.isFinite)) throw new RangeError('Isometric points must be finite.');
  const x = svgPoint[0] - layout.centerSvg[0], y = svgPoint[1] - layout.centerSvg[1];
  return [ISOMETRIC_COS * x - ISOMETRIC_COS * y, ISOMETRIC_SIN * x + ISOMETRIC_SIN * y - floorRank(layout, rank) * layout.gap];
}

/** Building point → the same isometric screen point used by room, asset and route geometry. */
export const isometricPoint = (layout: IsometricLayout, buildingPoint: Point, rank: number): Point => isometricSvgPoint(layout, toSvg(buildingPoint), rank);

/** Project all four building-space box corners, not just the diagonal: the axes are skewed. */
export function isometricBox(layout: IsometricLayout, buildingBox: Box, rank: number): Box {
  return bounds(corners(finiteBox(buildingBox)).map(point => isometricPoint(layout, point, rank)))!;
}

/** Transform an existing toSvg floor drawing without changing its raw polygons/routes. */
export function isometricMatrix(layout: IsometricLayout, rank: number): string {
  const [cx, cy] = layout.centerSvg;
  const e = -ISOMETRIC_COS * cx + ISOMETRIC_COS * cy;
  const f = -ISOMETRIC_SIN * cx - ISOMETRIC_SIN * cy - floorRank(layout, rank) * layout.gap;
  return `matrix(${ISOMETRIC_COS} ${ISOMETRIC_SIN} ${-ISOMETRIC_COS} ${ISOMETRIC_SIN} ${e} ${f})`;
}

/** Already screen-space: do not pass this box to the 2D viewBox helper (which flips y again). */
export function isometricViewBox(layout: Pick<IsometricLayout, 'scene'>): string {
  const { minX, minY, maxX, maxY } = layout.scene;
  return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;
}

export type IsometricFloorFrame = {
  scale: number;
  /** Center of the unshifted projected footprint in the full scene. */
  centerY: number;
  /** Includes the entire scaled slab, not just its top face. */
  box: Box;
};

/**
 * Pack real floors in physical order with clear gaps, emphasizing one without covering its neighbours.
 * The full canvas has the same bounds for every selection. Focusing is a separate pan/zoom operation:
 * cropping the SVG viewBox to the selected floor would permanently hide the other floors on zoom-out.
 */
export function createIsometricScene(layout: IsometricLayout, selectedRank: number) {
  const rank = floorRank(layout, selectedRank);
  const { footprint, slab, floorCount } = layout;
  const height = footprint.maxY - footprint.minY + slab;
  const gutter = Math.max(height * .055, slab);
  let bottom = 0;
  const floors: IsometricFloorFrame[] = Array.from({ length: floorCount }, (_, index) => {
    const scale = index === rank ? 1.4 : .76;
    const centerY = bottom - scale * (footprint.maxY + slab);
    const box = { minX: footprint.minX * scale, maxX: footprint.maxX * scale, minY: bottom - height * scale, maxY: bottom };
    bottom = box.minY - gutter;
    return { scale, centerY, box };
  });
  const active = floors[rank]!;
  const padX = Math.max((active.box.maxX - active.box.minX) * .065, slab * 3, 1);
  const padY = Math.max(height * 1.4 * .1, slab * 3, 1);
  const focus = { minX: active.box.minX - padX, minY: active.box.minY - padY, maxX: active.box.maxX + padX, maxY: active.box.maxY + padY };
  // Sum scales analytically so switching the active floor cannot resize the canvas through rounding.
  const fullHeight = height * (1.4 + .76 * (floorCount - 1)) + gutter * (floorCount - 1);
  const scenePadY = Math.max(height * 1.4 * .5, padY);
  const scene = { minX: footprint.minX * 1.4 - padX, maxX: footprint.maxX * 1.4 + padX, minY: -fullHeight - scenePadY, maxY: scenePadY };
  return { floors, focus, scene };
}

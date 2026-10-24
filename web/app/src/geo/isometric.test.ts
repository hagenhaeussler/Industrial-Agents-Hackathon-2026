import { describe, expect, test } from 'bun:test';
import type { Point } from '../api/types';
import type { Box } from './transform';
import { bounds, toSvg } from './transform';
import { createIsometricLayout, ISOMETRIC_COS, isometricBox, isometricMatrix, isometricPoint, isometricSvgPoint, isometricViewBox } from './isometric';

const footprint: Box = { minX: 0, minY: 0, maxX: 20, maxY: 10 };
const layout = createIsometricLayout(footprint, 3);
const pointClose = (actual: Point, expected: Point) => { expect(actual[0]).toBeCloseTo(expected[0], 10); expect(actual[1]).toBeCloseTo(expected[1], 10); };

describe('isometric exploded floor projection', () => {
  test('centers the SVG footprint and preserves the exact 30-degree plane axes', () => {
    pointClose(layout.centerSvg, [10, -5]);
    pointClose(isometricSvgPoint(layout, layout.centerSvg, 0), [0, 0]);
    const x = isometricSvgPoint(layout, [11, -5], 0);
    const y = isometricSvgPoint(layout, [10, -4], 0);
    expect(Math.hypot(...x)).toBeCloseTo(1, 10);
    expect(Math.hypot(...y)).toBeCloseTo(1, 10);
    expect(Math.atan2(x[1], x[0]) * 180 / Math.PI).toBeCloseTo(30, 10);
    expect(Math.atan2(y[1], y[0]) * 180 / Math.PI).toBeCloseTo(150, 10);
    expect(x[0] * y[1] - x[1] * y[0]).toBeGreaterThan(0); // no mirrored plane
  });

  test('building points apply the shared y-flip exactly once', () => {
    pointClose(isometricPoint(layout, [20, 10], 0), [15 * ISOMETRIC_COS, 2.5]);
    pointClose(isometricPoint(layout, [20, 10], 1), isometricSvgPoint(layout, toSvg([20, 10]), 1));
  });

  test('projects all box corners and every floor uses the same footprint dimensions', () => {
    const corners: Point[] = [[0, 0], [20, 0], [20, 10], [0, 10]];
    for (let rank = 0; rank < 3; rank += 1) {
      const box = isometricBox(layout, footprint, rank);
      const actual = bounds(corners.map(point => isometricPoint(layout, point, rank)))!;
      expect(box).toEqual(actual);
      expect(box.maxX - box.minX).toBeCloseTo(30 * ISOMETRIC_COS, 10);
      expect(box.maxY - box.minY).toBeCloseTo(15, 10);
      expect((box.minY + box.maxY) / 2).toBeCloseTo(-rank * layout.gap, 10);
    }
    // A diagonal-only bounds implementation would miss these two extrema.
    expect(isometricBox(layout, footprint, 0).minY).toBe(-7.5);
    expect(isometricBox(layout, footprint, 0).maxY).toBe(7.5);
    expect(isometricBox(layout, footprint, 1).maxY + layout.slab).toBeLessThan(isometricBox(layout, footprint, 0).minY);
  });

  test('SVG matrix and projected point agree for route vertices on every floor', () => {
    for (let rank = 0; rank < 3; rank += 1) {
      const [a, b, c, d, e, f] = isometricMatrix(layout, rank).slice(7, -1).split(' ').map(Number) as [number, number, number, number, number, number];
      for (const vertex of [[0, 0], [7, 3], [20, 10]] as Point[]) {
        const [x, y] = toSvg(vertex);
        pointClose([a * x + c * y + e, b * x + d * y + f], isometricPoint(layout, vertex, rank));
      }
    }
  });

  test('basements and skipped floor numbers are ordered by ordinal rank, never by level', () => {
    const realLevels = [-2, 0, 5];
    const centers = realLevels.map((_level, rank) => isometricPoint(layout, [10, 5], rank));
    pointClose(centers[0]!, [0, 0]);
    pointClose(centers[1]!, [0, -layout.gap]);
    pointClose(centers[2]!, [0, -2 * layout.gap]);
    expect(layout.gap).toBeCloseTo(15 * 1.05 + layout.slab, 10);
  });

  test('scene bounds include all floor planes, slabs and a small camera focus pan', () => {
    const original = isometricViewBox(layout);
    for (let rank = 0; rank < 3; rank += 1) {
      const box = isometricBox(layout, footprint, rank);
      for (const pan of [-1, 0, 1]) {
        expect(box.minX + pan).toBeGreaterThanOrEqual(layout.scene.minX);
        expect(box.maxX + pan).toBeLessThanOrEqual(layout.scene.maxX);
        expect(box.minY + pan).toBeGreaterThanOrEqual(layout.scene.minY);
        expect(box.maxY + layout.slab + pan).toBeLessThanOrEqual(layout.scene.maxY);
      }
    }
    expect(isometricViewBox(layout)).toBe(original); // selecting/projecting does not resize the scene
    const [x, y, width, height] = original.split(' ').map(Number);
    expect(x).toBe(layout.scene.minX); expect(y).toBe(layout.scene.minY);
    expect(width).toBeGreaterThan(0); expect(height).toBeGreaterThan(0);
    const taller = createIsometricLayout(footprint, 5);
    expect(taller.scene.maxX - taller.scene.minX).toBe(layout.scene.maxX - layout.scene.minX);
    expect(taller.scene.maxY - taller.scene.minY).toBeGreaterThan(layout.scene.maxY - layout.scene.minY);
  });

  test('zero-area and line footprints stay finite with positive gaps and viewBox dimensions', () => {
    for (const box of [{ minX: 3, maxX: 3, minY: -2, maxY: -2 }, { minX: 0, maxX: 0, minY: 0, maxY: 20 }, { minX: 20, maxX: 0, minY: 10, maxY: 0 }]) {
      const degenerate = createIsometricLayout(box, 0);
      expect(degenerate.floorCount).toBe(1);
      expect(degenerate.gap).toBeGreaterThan(0); expect(degenerate.slab).toBeGreaterThan(0);
      const values = isometricViewBox(degenerate).split(' ').map(Number);
      expect(values.every(Number.isFinite)).toBe(true);
      expect(values[2]).toBeGreaterThan(0); expect(values[3]).toBeGreaterThan(0);
      expect(isometricPoint(degenerate, [box.minX, box.minY], 0).every(Number.isFinite)).toBe(true);
    }
    expect(createIsometricLayout(footprint, NaN).floorCount).toBe(1);
    expect(() => createIsometricLayout({ ...footprint, maxX: Infinity }, 3)).toThrow(RangeError);
    expect(() => isometricPoint(layout, [NaN, 0], 0)).toThrow(RangeError);
  });
});

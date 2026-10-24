import { describe, expect, test } from 'bun:test';
import jsQR from 'jsqr';
import { createLatest } from '../api/latest';
import type { Snapshot, Tour } from '../api/types';
import { bounds, toSvg, viewBox, wallDirection } from '../geo/transform';
import { buildModel, routeBox, stopMarks, tourFloors } from '../map/model';
import snapshotJson from '../mocks/data/building_proc-factory-dev-003.json';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { match } from '../router';
import { qrPath } from './HandoffDialog';

const snapshot = snapshotJson as unknown as Snapshot;
const tour = tourJson as unknown as Tour;

describe('2D transform (CONTRACTS §11)', () => {
  test('flips y and nothing else', () => {
    expect(toSvg([3, 4])).toEqual([3, -4]);
    expect(viewBox({ minX: 0, minY: 0, maxX: 10, maxY: 5 }, 1)).toBe('-1 -6 12 7');
  });
  test('finds the wall a door sits on', () => {
    const square: [number, number][] = [[0, 0], [10, 0], [10, 10], [0, 10]];
    expect(wallDirection(square, [5, 0.1]).map(Math.abs)).toEqual([1, 0]);
    expect(wallDirection(square, [9.9, 4]).map(Math.abs)).toEqual([0, 1]);
  });
});

describe('map model on the factory fixture', () => {
  const model = buildModel(snapshot);
  test('indexes floors bottom-up and every space', () => {
    expect(model.floors.map(floor => floor.level)).toEqual([0, 1]);
    expect(model.space.size).toBe(snapshot.building.spaces.length);
  });
  test('stops are numbered in tour order and sit where the leg arrives', () => {
    const marks = stopMarks(model, tour);
    expect(marks.map(mark => mark.n)).toEqual([1, 2, 3]);
    expect(marks.map(mark => mark.stopId)).toEqual(tour.order);
    const firstLeg = tour.legs[0];
    if (!firstLeg?.reachable) throw new Error('fixture leg unreachable');
    const lastWalk = [...firstLeg.segments].reverse().find(segment => segment.kind === 'walk');
    expect(marks[0]?.point).toEqual(lastWalk?.points.at(-1) as [number, number]);
  });
  test('fit-to-route covers only what is drawn on that floor', () => {
    const box = routeBox(model, tour, tour.start.floor_id);
    const ground = tour.legs.flatMap(leg => (leg.reachable ? leg.segments : [])).filter(segment => segment.floor_id === tour.start.floor_id).flatMap(segment => segment.points);
    const expected = bounds(ground)!;
    expect(box!.minX).toBeLessThanOrEqual(expected.minX);
    expect(box!.maxY).toBeGreaterThanOrEqual(expected.maxY);
    expect(tourFloors(tour)[0]).toBe(tour.start.floor_id);
  });
});

describe('handoff QR', () => {
  test('decodes to exactly the tour URL', () => {
    const url = 'https://tyb.example/go/k3j9q2m7xa';
    const { size, d } = qrPath(url);
    const scale = 6, margin = 4, px = (size + 2 * margin) * scale;
    const dark = new Set([...d.matchAll(/M(\d+) (\d+)/g)].map(m => `${m[1]},${m[2]}`));
    const data = new Uint8ClampedArray(px * px * 4);
    for (let y = 0; y < px; y++) for (let x = 0; x < px; x++) {
      const mx = Math.floor(x / scale) - margin, my = Math.floor(y / scale) - margin;
      const v = dark.has(`${mx},${my}`) ? 0 : 255;
      data.set([v, v, v, 255], (y * px + x) * 4);
    }
    expect(jsQR(data, px, px)?.data).toBe(url);
  });
});

describe('request ordering', () => {
  test('a late response never overwrites a newer one', async () => {
    const latest = createLatest();
    const applied: string[] = [];
    const slow = latest.run(() => new Promise<string>(resolve => setTimeout(() => resolve('old'), 30)), value => applied.push(value));
    const fast = latest.run(async () => 'new', value => applied.push(value));
    await Promise.all([slow, fast]);
    expect(applied).toEqual(['new']);
  });
});

describe('routes', () => {
  test('match the five SPA routes', () => {
    expect(match('/')).toEqual({ name: 'home' });
    expect(match('/desk/')).toEqual({ name: 'desk' });
    expect(match('/go/k3j9q2m7xa')).toEqual({ name: 'go', tourId: 'k3j9q2m7xa' });
    expect(match('/m/mk_ab12cd34')).toEqual({ name: 'marker', markerId: 'mk_ab12cd34' });
    expect(match('/admin')).toEqual({ name: 'admin' });
    expect(match('/nope/x')).toEqual({ name: 'missing' });
  });
});

describe('desk ask fallback (text chat not connected)', () => {
  const model = buildModel(snapshot);
  test('splits a spoken list into one phrase per item', async () => {
    const { phrases } = await import('./matchParts');
    expect(phrases('I need the 3D printer H-A3-A, the tool cabinet and the UPS unit upstairs.')).toEqual(['the 3d printer h-a3-a', 'the tool cabinet', 'the ups unit upstairs.']);
  });
  test('selects unique parts, asks once for an ambiguous one, reports a missing one', async () => {
    const { fallbackReply } = await import('./matchParts');
    const answer = fallbackReply(model, 'I need the 3D printer H-A3-A, the tool cabinet and a unicorn');
    expect(answer.select.map(id => model.asset.get(id)?.name)).toEqual(['3D printer H-A3-A']);
    expect(answer.candidates.length).toBeGreaterThan(1);
    expect(answer.reply).toContain('searched the parts list');
    expect(answer.reply).toContain('Nothing in this building matches “unicorn”');
  });
  test('the demo sentence selects exactly the scenario parts', async () => {
    const { fallbackReply } = await import('./matchParts');
    // the Vite glob loader does not run under bun test, so read the scenario file directly
    const scenario = (await import('../../../../demo/scenario.json')).default as { say: string; items: string[] };
    expect(new Set(fallbackReply(model, scenario.say).select)).toEqual(new Set(scenario.items));
  });
  test('a single question focuses the part and names its place', async () => {
    const { fallbackReply } = await import('./matchParts');
    const answer = fallbackReply(model, 'Where is the 3D printer H-A3-A?');
    expect(answer.focus).toBe('proc-factory-dev-003-A00021');
    expect(answer.reply).toContain('Additive zone H-A3');
  });
});

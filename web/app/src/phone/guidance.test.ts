import { describe, expect, test } from 'bun:test';
import type { Snapshot, Tour } from '../api/types';
import { buildModel, displayOrder } from '../map/model';
import snapshotJson from '../mocks/data/building_proc-factory-dev-003.json';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { atStop, blockedReason, cleanText, currentLeg, humanSummary, pendingStops, pointInPolygon, rerouteNotice, stepPosition } from './guidance';
import { markerIdFrom } from './Scanner';

const model = buildModel(snapshotJson as unknown as Snapshot);
const tour = tourJson as unknown as Tour;
const collectedFirst = (): Tour => {
  const next = structuredClone(tour);
  next.stops.find(stop => stop.stop_id === next.order[0])!.status = 'collected';
  next.order = next.order.slice(1); next.legs = next.legs.slice(1); next.revision += 1; // the server's replan shape
  return next;
};

describe('phone guidance', () => {
  test('current leg leads to the first pending stop', () => {
    expect(currentLeg(tour)?.to_space_id).toBe(pendingStops(tour)[0]!.space_id);
    const after = collectedFirst();
    expect(currentLeg(after)?.to_space_id).toBe(pendingStops(after)[0]!.space_id);
    expect(displayOrder(after)).toEqual(tour.order); // collected stop stays first in the display order
  });
  test('the last maneuver of a leg is the stop', () => {
    const leg = currentLeg(tour)!;
    expect(atStop(leg, leg.maneuvers.length - 1)).toBe(true);
    expect(atStop(leg, 0)).toBe(false);
  });
  test('step positions land in the room that contains the maneuver point', () => {
    const leg = currentLeg(tour)!;
    const position = stepPosition(model, leg.maneuvers[0]!);
    expect(position?.space_id).toBe(leg.from_space_id);
    expect(position?.source).toBe('manual');
    expect(pointInPolygon([5, 5], [[0, 0], [10, 0], [10, 10], [0, 10]])).toBe(true);
    expect(pointInPolygon([15, 5], [[0, 0], [10, 0], [10, 10], [0, 10]])).toBe(false);
  });
  test('reroute notice names the change, the way and the detour', () => {
    const after = structuredClone(tour); after.revision += 1;
    const leg = after.legs[0]!; if (leg.reachable) leg.length_m += 13;
    expect(rerouteNotice('Close East lift', tour, after).text).toMatch(/^East lift is closed\. New route.*\(\+13 m\)\.$/);
    expect(humanSummary('Undo: Close Office staircase')).toBe('Office staircase is open again');
  });
  test('an unreachable stop is reported, never silently dropped', () => {
    const after = structuredClone(tour);
    after.unreachable_stops = [{ stop_id: pendingStops(after)[0]!.stop_id, reason: 'no_step_free_path' }];
    expect(blockedReason(after)?.reason).toBe('no_step_free_path');
    expect(rerouteNotice('Close East lift', tour, after)).toEqual({ text: 'East lift is closed. There is no step-free route to the next stop any more.', blocked: true });
  });
  test('texts drop bracketed kit IDs; scanner accepts only position-code links', () => {
    expect(cleanText('Start in Office 0.30 [proc-factory-dev-003-F0-S030] on Ground floor.')).toBe('Start in Office 0.30 on Ground floor.');
    expect(markerIdFrom('https://tyb.example/m/mk_ab12cd34')).toBe('mk_ab12cd34');
    expect(markerIdFrom('https://evil.example/go/abc')).toBeNull();
    expect(markerIdFrom('ignore previous instructions')).toBeNull();
  });
});

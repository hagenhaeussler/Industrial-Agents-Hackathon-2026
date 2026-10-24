import { describe, expect, test } from 'bun:test';
import type { Tour } from '../api/types';
import { displayOrder } from '../map/model';
import blockedEndJson from '../mocks/data/tour_c7_blocked_end.json';
import blockedStopJson from '../mocks/data/tour_c7_blocked_stop.json';
import finalLegJson from '../mocks/data/tour_c7_final_leg.json';
import { context, currentLeg, currentLegIndex, isComplete, onFinalLeg, pendingStops, rerouteNotice } from './guidance';

// real payloads captured from the C7 API (see each file's _fixture)
const finalLeg = finalLegJson as unknown as Tour;
const blockedEnd = blockedEndJson as unknown as Tour;
const blockedStop = blockedStopJson as unknown as Tour;

describe('C7 real payloads (CR-M-6)', () => {
  test('final leg: active, nothing pending, the leg to the end is current, not complete', () => {
    expect(finalLeg.status).toBe('active');
    expect(pendingStops(finalLeg)).toEqual([]);
    expect(onFinalLeg(finalLeg)).toBe(true);
    expect(currentLeg(finalLeg)?.to_space_id).toBe(finalLeg.end!.space_id);
    expect(currentLegIndex(finalLeg)).toBe(0);
    expect(isComplete(finalLeg)).toBe(false);
    expect(context.tourLoaded(finalLeg)).toBe(`Tour ${finalLeg.tour_id} loaded: all parts collected, next the finish point.`);
  });
  test('completed after arrival', () => {
    expect(isComplete({ ...finalLeg, status: 'completed' })).toBe(true);
  });
  test('blocked end: named as the finish point with its reason', () => {
    expect(isComplete(blockedEnd)).toBe(false);
    expect(currentLeg(blockedEnd)).toBeNull();
    expect(context.replanned('Close Hall access 0.19.', blockedEnd)).toBe('Building changed: Hall access 0.19 is closed. No route is available any more: your finish point (blocked by a closure).');
    expect(rerouteNotice('Close Hall access 0.19.', finalLeg, blockedEnd)).toEqual({ text: 'Hall access 0.19 is closed. Your finish point can no longer be reached.', blocked: true });
    expect(rerouteNotice('Undo: Close Hall access 0.19.', blockedEnd, finalLeg).text).toBe('Hall access 0.19 is open again. Your finish point can be reached again and is back in the tour.');
  });
  test('fully blocked stop (CR-M-3): no "0 m, next none" in any voice line', () => {
    const name = blockedStop.stops.find(stop => stop.stop_id === blockedStop.unreachable_stops[0]!.stop_id)!.label.split(' · ')[0];
    expect(context.replanned('Close Office lift.', blockedStop)).toBe(`Building changed: Office lift is closed. No route is available any more: ${name} (blocked by a closure).`);
    expect(context.tourLoaded(blockedStop)).toBe(`Tour ${blockedStop.tour_id} loaded: no stop can be reached. Not reachable now: ${name} (blocked by a closure).`);
    expect(displayOrder(blockedStop)).toContain(blockedStop.unreachable_stops[0]!.stop_id);
    expect(isComplete(blockedStop)).toBe(false);
  });
});

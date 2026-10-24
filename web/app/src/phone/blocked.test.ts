import { describe, expect, test } from 'bun:test';
import type { Tour } from '../api/types';
import { displayOrder } from '../map/model';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { blockedReason, context, currentLeg, currentLegIndex, isComplete, onFinalLeg, pendingStops, rerouteNotice } from './guidance';

const tour = tourJson as unknown as Tour;

describe('blocked tour shape (CR-M-2: status blocked, order empty)', () => {
  // the server's shape after the only remaining stop becomes unreachable step-free
  const blocked = (): Tour => {
    const next = structuredClone(tour);
    const last = next.order[next.order.length - 1]!;
    next.stops.forEach(stop => { if (stop.stop_id !== last) stop.status = 'collected'; });
    next.order = []; next.legs = []; next.status = 'blocked'; next.revision += 1;
    next.constraints = { ...next.constraints, step_free: true };
    next.unreachable_stops = [{ stop_id: last, reason: 'blocked_by_closure' }];
    return next;
  };
  test('the unreachable pending stop stays visible and nothing claims a route', () => {
    const after = blocked();
    expect(pendingStops(after)).toEqual([]);
    expect(currentLeg(after)).toBeNull();
    expect(displayOrder(after)).toContain(after.unreachable_stops[0]!.stop_id);
    expect(blockedReason(after)?.reason).toBe('blocked_by_closure');
  });
  test('the notice names the stop instead of a shorter "new route"', () => {
    const before = structuredClone(tour);
    const notice = rerouteNotice('Close Office lift', before, blocked());
    expect(notice.blocked).toBe(true);
    expect(notice.text).toContain('can no longer be reached step-free');
    expect(notice.text).not.toContain('New route');
  });
});

describe('voice context for blocked tours (CR-M-3 remainder)', () => {
  const blocked = (): Tour => {
    const next = structuredClone(tour);
    const last = next.order[next.order.length - 1]!;
    next.stops.forEach(stop => { if (stop.stop_id !== last) stop.status = 'collected'; });
    next.order = []; next.legs = []; next.status = 'blocked';
    next.unreachable_stops = [{ stop_id: last, reason: 'blocked_by_closure' }];
    return next;
  };
  test('a fully blocked tour names the stop and the reason and says there is no route', () => {
    const after = blocked();
    const name = after.stops.find(stop => stop.stop_id === after.unreachable_stops[0]!.stop_id)!.label.split(' · ')[0];
    const text = context.replanned('Close Office lift', after);
    expect(text).toBe(`Building changed: Office lift is closed. No route is available any more: ${name} (blocked by a closure).`);
    expect(text).not.toContain('0 m');
    expect(text).not.toContain('next none');
  });
  test('a partly blocked tour gives the new length, the next stop and what is missing', () => {
    const after = structuredClone(tour);
    const lost = after.order[after.order.length - 1]!;
    after.order = after.order.slice(0, -1); after.legs = after.legs.slice(0, -1);
    after.unreachable_stops = [{ stop_id: lost, reason: 'no_step_free_path' }];
    const text = context.replanned('Close Office lift', after);
    expect(text).toContain('The active tour was replanned:');
    expect(text).toContain(`next ${pendingStops(after)[0]!.label}`);
    expect(text).toContain('Not reachable now:');
    expect(text).toContain('(no step-free way)');
  });
});

describe('final leg to the end destination (C7)', () => {
  // the core's C7 shape: every part collected, end remains, status active, order empty, one leg to the end
  const lastLeg = (): Tour => {
    const next = structuredClone(tour);
    next.stops.forEach(stop => { stop.status = 'collected'; });
    const leg = structuredClone(next.legs[0]!);
    next.end = { ...next.start };
    if (leg.reachable) leg.to_space_id = next.end.space_id;
    next.order = []; next.legs = [leg]; next.status = 'active';
    return next;
  };
  test('guides the last leg instead of declaring the tour done', () => {
    const after = lastLeg();
    expect(onFinalLeg(after)).toBe(true);
    expect(currentLeg(after)?.to_space_id).toBe(after.end!.space_id);
    expect(currentLegIndex(after)).toBe(0);
    expect(isComplete(after)).toBe(false);
    expect(context.replanned('Close Office staircase', after)).toContain('next the finish point');
  });
  test('completed after arriving; an unreachable end is not complete', () => {
    const arrived = { ...lastLeg(), status: 'completed', legs: [] };
    expect(isComplete(arrived)).toBe(true);
    expect(onFinalLeg(arrived)).toBe(false);
    const stuck = { ...lastLeg(), status: 'blocked', legs: [], unreachable_stops: [{ stop_id: 'end', reason: 'blocked_by_closure' }] };
    expect(isComplete(stuck)).toBe(false);
    expect(context.replanned('Close Office lift', stuck)).toBe('Building changed: Office lift is closed. No route is available any more: your finish point (blocked by a closure).');
  });
  test('a tour without an end is complete once everything is collected', () => {
    const all = structuredClone(tour);
    all.stops.forEach(stop => { stop.status = 'collected'; });
    all.order = []; all.legs = []; all.status = 'completed';
    expect(isComplete(all)).toBe(true);
  });
  test('an active payload never becomes complete merely because every part is collected', () => {
    const all = structuredClone(tour);
    all.stops.forEach(stop => { stop.status = 'collected'; });
    all.order = []; all.legs = []; all.status = 'active';
    expect(isComplete(all)).toBe(false);
  });
  test('blocked pending parts cannot be skipped to navigate the optional finish', () => {
    const after = lastLeg();
    after.stops[0]!.status = 'pending';
    after.unreachable_stops = [{ stop_id: after.stops[0]!.stop_id, reason: 'blocked_by_closure' }];
    expect(pendingStops(after)).toEqual([]); // reachable order intentionally omits this pending part
    expect(onFinalLeg(after)).toBe(false);
    expect(currentLeg(after)).toBeNull();
    expect(isComplete(after)).toBe(false);
    expect(context.replanned('Close Office lift', after)).toContain('No route is available any more');
  });
});

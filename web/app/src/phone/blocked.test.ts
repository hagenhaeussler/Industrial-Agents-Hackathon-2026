import { describe, expect, test } from 'bun:test';
import type { Tour } from '../api/types';
import { displayOrder } from '../map/model';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { blockedReason, context, currentLeg, pendingStops, rerouteNotice } from './guidance';

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
  test('fully blocked voice context names the pending part and its reason', () => {
    const after = blocked();
    const name = after.stops.find(stop => stop.status === 'pending')!.label.split(' · ')[0]!;
    const text = context.replanned('Close Office lift', after);
    expect(text).toContain('No route is available any more: blocked_by_closure');
    expect(text).toContain(name);
    expect(text).not.toContain('replanned: 0 m');
    expect(context.tourLoaded(after)).toContain(name);
  });
});

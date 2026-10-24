import { describe, expect, test } from 'bun:test';
import { api } from '../api/client';
import type { Snapshot, Tour } from '../api/types';
import { buildModel } from '../map/model';
import snapshot from '../mocks/data/building_proc-factory-dev-003.json';
import payloads from './fixtures/final-destination-c7.json';
import { blockedReason, context, currentLeg, currentLegIndex, currentTarget, finalDestinationPending, pendingStops, rerouteNotice, tourDone } from './guidance';

// These are responses captured through the real C7 HTTP API, including progress,
// a destination closure, explicit reopen constraints and confirmed final arrival.
const before = payloads.before as unknown as Tour;
const finalLeg = payloads.finalLeg as unknown as Tour;
const blockedEnd = payloads.blockedEnd as unknown as Tour;
const reopenedEnd = payloads.reopenedEnd as unknown as Tour;
const arrived = payloads.arrived as unknown as Tour;
const model = buildModel(snapshot as unknown as Snapshot);

describe('C7 final destination guidance', () => {
  test('collecting the last part keeps the real final leg active', () => {
    expect(finalLeg.stops.every(stop => stop.status === 'collected')).toBe(true);
    expect(finalLeg.status).toBe('active');
    expect(tourDone(finalLeg)).toBe(false);
    expect(pendingStops(finalLeg)).toEqual([]);
    expect(finalDestinationPending(finalLeg)).toBe(true);
    expect(currentTarget(finalLeg, model)?.stop_id).toBe('end');
    expect(currentTarget(finalLeg, model)?.label).toBe(model.space.get(finalLeg.end!.space_id)!.name);
    expect(currentLegIndex(finalLeg)).toBe(finalLeg.legs.length - 1);
    expect(currentLeg(finalLeg)?.to_space_id).toBe(finalLeg.end!.space_id);
    expect(currentLeg(finalLeg)?.segments.length).toBeGreaterThan(0);
  });

  test('the final leg does not replace a part that still needs collecting', () => {
    expect(before.order.length).toBe(1);
    expect(before.legs.length).toBe(2);
    expect(finalDestinationPending(before)).toBe(false);
    expect(currentTarget(before)?.stop_id).toBe(before.order[0]);
    expect(currentLegIndex(before)).toBe(0);
  });

  test('an unreachable final destination remains blocked and names its reason', () => {
    expect(blockedEnd.status).toBe('blocked');
    expect(tourDone(blockedEnd)).toBe(false);
    expect(currentLeg(blockedEnd)).toBeNull();
    expect(blockedReason(blockedEnd)?.reason).toBe('blocked_by_closure');
    const voice = context.replanned('Final destination closed.', blockedEnd, model);
    expect(voice).toContain('No route is available');
    expect(voice).toContain(model.space.get(blockedEnd.end!.space_id)!.name);
    expect(voice).toContain('blocked by a closure');
    expect(voice).not.toContain('replanned: 0 m');
  });

  test('reopening resumes directions and only explicit arrival finishes the tour', () => {
    expect(reopenedEnd.stops).toEqual(finalLeg.stops);
    expect(tourDone(reopenedEnd)).toBe(false);
    expect(currentLeg(reopenedEnd)?.to_space_id).toBe(reopenedEnd.end!.space_id);
    expect(rerouteNotice('Reopen destination', blockedEnd, reopenedEnd, model).text).toContain('can be reached again');
    expect(arrived.status).toBe('completed');
    expect(tourDone(arrived)).toBe(true);
    expect(currentTarget(arrived)).toBeNull();
    expect(currentLeg(arrived)).toBeNull();
    expect(arrived.stops).toEqual(finalLeg.stops);
  });

  test('final confirmation uses the reserved end ID and the calling phone session', async () => {
    const previousFetch = globalThis.fetch;
    let request: { input: string; init?: RequestInit } | undefined;
    globalThis.fetch = (async (input, init) => {
      request = { input: String(input), init };
      return Response.json(arrived);
    }) as typeof fetch;
    try {
      await api.progress(finalLeg.tour_id, 'end', 'collected', 'calling-phone-session');
      expect(request?.input).toBe(`/api/tours/${encodeURIComponent(finalLeg.tour_id)}/progress`);
      expect(request?.init?.method).toBe('POST');
      expect(JSON.parse(String(request?.init?.body))).toEqual({ stop_id: 'end', status: 'collected' });
      expect(new Headers(request?.init?.headers).get('X-Session-ID')).toBe('calling-phone-session');
    } finally { globalThis.fetch = previousFetch; }
  });
});

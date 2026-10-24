import { describe, expect, test } from 'bun:test';
import type { ReachableRoute, Tour } from '../api/types';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { arrowState, nextWaypoint } from './cameraArrow';
import type { Anchor } from './cameraArrow';

const leg = (tourJson as unknown as Tour).legs[0] as ReachableRoute;
const start = leg.maneuvers[0]!;
const target = nextWaypoint(leg, 0)!;
const facing = Math.atan2(target[1] - start.at[1], target[0] - start.at[0]) * 180 / Math.PI; // building heading towards the waypoint
const anchor = (heading: number, alphaAtScan: number | null = 0): Anchor => ({ point: start.at, heading_deg: heading, floor_id: start.floor_id, alphaAtScan });
const bearing = (state: ReturnType<typeof arrowState>) => (state.kind === 'arrow' ? Math.round(state.bearing) : NaN);

describe('camera arrow (direction only)', () => {
  test('points to the next maneuver on the same floor', () => {
    expect(target).not.toEqual(start.at);
    expect(leg.maneuvers.some(item => item.at === target || (item.at[0] === target[0] && item.at[1] === target[1])) || leg.segments.some(segment => segment.points.some(point => point[0] === target[0] && point[1] === target[1]))).toBe(true);
  });
  test('straight ahead when facing the waypoint, sideways when turned away', () => {
    expect(bearing(arrowState(leg, 0, start.at, start.floor_id, anchor(facing), 0))).toBe(0);
    expect(Math.abs(bearing(arrowState(leg, 0, start.at, start.floor_id, anchor(facing + 90), 0)))).toBe(90);
  });
  test('turning the phone after the scan turns the arrow back', () => {
    // scanned facing 90° away; the phone has since turned the same 90° back
    const turned = arrowState(leg, 0, start.at, start.floor_id, anchor(facing + 90, 10), 10 - 90);
    expect(bearing(turned)).toBe(0);
  });
  test('asks for a position code instead of guessing', () => {
    expect(arrowState(leg, 0, start.at, start.floor_id, null, 0)).toEqual({ kind: 'scan', reason: 'no_anchor' });
    expect(arrowState(leg, 0, start.at, start.floor_id, anchor(facing, null), 5)).toEqual({ kind: 'scan', reason: 'no_anchor' });
    expect(arrowState(leg, 0, start.at, 'another-floor', anchor(facing), 0)).toEqual({ kind: 'scan', reason: 'other_floor' });
  });
  test('without a motion sensor the arrow is relative to the code direction', () => {
    const state = arrowState(leg, 0, start.at, start.floor_id, anchor(facing, null), null);
    expect(state.kind === 'arrow' && state.relative).toBe(true);
  });
  test('shows arrival at the last maneuver', () => {
    expect(arrowState(leg, leg.maneuvers.length - 1, start.at, start.floor_id, anchor(facing), 0)).toEqual({ kind: 'arrived' });
  });
});

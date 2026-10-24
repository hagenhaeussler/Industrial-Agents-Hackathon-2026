import { describe, expect, test } from 'bun:test';
import { sameBuildingState } from './buildingState';

describe('reset-safe building freshness', () => {
  test('matching numeric versions cannot validate a different edit history', () => {
    expect(sameBuildingState({ building_version: 2, building_state_id: 'after-reset' }, { building_version: 2, building_state_id: 'before-reset' })).toBe(false);
    expect(sameBuildingState({ building_version: 2, building_state_id: 'after-reset' }, { building_version: 2 })).toBe(false);
    expect(sameBuildingState({ building_version: 2 }, { building_version: 2, building_state_id: 'after-reset' })).toBe(false);
  });
  test('a lower reset version is stale; legacy fixtures compare for equality, not ordering', () => {
    expect(sameBuildingState({ building_version: 0 }, { building_version: 3 })).toBe(false);
    expect(sameBuildingState({ building_version: 3 }, { building_version: 0 })).toBe(false);
    expect(sameBuildingState({ building_version: 0 }, { building_version: 0 })).toBe(true);
  });
  test('fresh opaque IDs and versions match without parsing the identity', () => {
    expect(sameBuildingState({ building_version: 2, building_state_id: 'opaque:state' }, { building_version: 2, building_state_id: 'opaque:state' })).toBe(true);
    expect(sameBuildingState({ building_version: 3, building_state_id: 'opaque:state' }, { building_version: 2, building_state_id: 'opaque:state' })).toBe(false);
  });
});

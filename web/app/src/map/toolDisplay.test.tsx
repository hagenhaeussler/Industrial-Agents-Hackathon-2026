import { describe, expect, test } from 'bun:test';
import { renderToStaticMarkup } from 'react-dom/server';
import type { ReachableRoute, Snapshot, Tour } from '../api/types';
import buildingJson from '../mocks/data/building_proc-factory-dev-003.json';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { FloorMap } from './FloorMap';
import { buildModel } from './model';
import { displayedRoute, displayedSpaces, routeIsCurrent } from './toolDisplay';
import { RoutePreview } from './RoutePreview';

const snapshot = buildingJson as unknown as Snapshot;
const model = buildModel(snapshot);
const fixture = (tourJson as unknown as Tour).legs.find((leg): leg is ReachableRoute => leg.reachable)!;
const route: ReachableRoute = { ...fixture, building_version: snapshot.building_version, content_hash: snapshot.content_hash };

describe('shared tool displays', () => {
  test('draws the exact standalone route supplied by a server tool', () => {
    expect(displayedRoute({ kind: 'route', route }, model)).toBe(route);
    const floor = route.segments.find(segment => segment.kind === 'walk')!.floor_id;
    const html = renderToStaticMarkup(<FloorMap model={model} floorId={floor} route={route}/>);
    expect(html).toContain('class="map-route"');
    expect(html).toContain('stroke="#dcff58"');
    const first = route.segments.find(segment => segment.kind === 'walk' && segment.floor_id === floor)!;
    expect(html).toContain(`M${first.points[0]![0]},${-first.points[0]![1]}`);
    expect(html).not.toContain('class="map-stop"');
  });

  test('does not display geometry for a different building or an old snapshot', () => {
    for (const patch of [{ building_id: 'another-building' }, { building_version: route.building_version - 1 }, { content_hash: 'old-content' }]) {
      const stale = { ...route, ...patch };
      expect(displayedRoute({ kind: 'route', route: stale }, model)).toBeNull();
      expect(routeIsCurrent(stale, model)).toBe(false);
    }
  });

  test('a reused version and unchanged content hash do not validate a route from before reset', () => {
    const live = buildModel({ ...snapshot, building_state_id: 'current-history' });
    for (const building_state_id of ['old-history', undefined, null]) {
      const stale = { ...route, building_state_id };
      expect(displayedRoute({ kind: 'route', route: stale }, live)).toBeNull();
      expect(routeIsCurrent(stale, live)).toBe(false);
    }
    expect(displayedRoute({ kind: 'route', route: { ...route, building_state_id: 'current-history' } }, live)).not.toBeNull();
  });

  test('never invents lines for malformed or unreachable responses', () => {
    expect(displayedRoute({ kind: 'route', route: { ...route, reachable: false } }, model)).toBeNull();
    expect(displayedRoute({ kind: 'route', route: { ...route, segments: [{ kind: 'walk', floor_id: model.floors[0]!.id, points: [[NaN, 1]] }] } }, model)).toBeNull();
    expect(displayedRoute({ kind: 'route', route: { ...route, segments: undefined } }, model)).toBeNull();
    expect(displayedRoute({ kind: 'highlight', route }, model)).toBeNull();
  });

  test('supports multiple spatial-query rooms and asset positions without duplicates', () => {
    const asset = [...model.asset.values()][0]!;
    const other = model.floors.flatMap(floor => model.spacesOn.get(floor.id) ?? []).find(space => space.id !== asset.space_id)!;
    expect(displayedSpaces({ kind: 'highlight', space_ids: [other.id, 'missing'], space_id: asset.space_id, asset_ids: [asset.id] }, model)).toEqual([other.id, asset.space_id]);
  });

  test('provides textual directions while keeping collection progress separate', () => {
    const before = JSON.stringify(route);
    const html = renderToStaticMarkup(<RoutePreview model={model} route={route} collection onClose={() => undefined}/>);
    expect(html).toContain('Back to collection tour');
    expect(html).toContain('does not change your position or collection progress');
    expect(html).toContain(route.maneuvers[0]!.text.replaceAll('&', '&amp;').replaceAll('>', '&gt;').replaceAll('<', '&lt;'));
    expect(JSON.stringify(route)).toBe(before);
  });
});

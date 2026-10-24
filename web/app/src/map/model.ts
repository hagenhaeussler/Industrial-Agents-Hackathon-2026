import type { Asset, Connector, Floor, Opening, Point, ReachableRoute, Snapshot, Space, Tour } from '../api/types';
import { bounds, centroid } from '../geo/transform';
import type { Box } from '../geo/transform';

/** Read-only indexes over one snapshot; built once per `content_hash`/`building_version`. */
export type Model = {
  snapshot: Snapshot;
  floors: Floor[]; // lowest level first
  floor: Map<string, Floor>;
  space: Map<string, Space>;
  asset: Map<string, Asset>;
  connector: Map<string, Connector>;
  spacesOn: Map<string, Space[]>;
  openingsOn: Map<string, Opening[]>;
  assetsIn: Map<string, Asset[]>;
  closed: Set<string>;
  box: Box;
  /** label font size in metres, scaled to the building so the factory and a flat both read well */
  unit: number;
};

const group = <T, K>(items: readonly T[], key: (item: T) => K) => {
  const map = new Map<K, T[]>();
  for (const item of items) { const k = key(item); const list = map.get(k); if (list) list.push(item); else map.set(k, [item]); }
  return map;
};

export function buildModel(snapshot: Snapshot): Model {
  const b = snapshot.building;
  const floors = [...b.floors].sort((x, y) => x.level - y.level);
  const box = bounds(b.spaces.flatMap(space => space.polygon)) ?? { minX: 0, minY: 0, maxX: 10, maxY: 10 };
  const extent = Math.max(box.maxX - box.minX, box.maxY - box.minY);
  return {
    snapshot, floors,
    floor: new Map(floors.map(floor => [floor.id, floor])),
    space: new Map(b.spaces.map(space => [space.id, space])),
    asset: new Map(b.assets.map(asset => [asset.id, asset])),
    connector: new Map(b.vertical_connectors.map(connector => [connector.id, connector])),
    spacesOn: group(b.spaces, space => space.floor_id),
    openingsOn: group(b.openings, opening => opening.floor_id),
    assetsIn: group(b.assets, asset => asset.space_id),
    closed: new Set(snapshot.closed),
    box,
    unit: Math.min(1.6, Math.max(0.32, extent / 95)),
  };
}

export const anchorOf = (model: Model, spaceId: string): Point => model.snapshot.derived.anchors[spaceId] ?? centroid(model.space.get(spaceId)?.polygon ?? [[0, 0]]);
export const floorName = (model: Model, floorId: string) => model.floor.get(floorId)?.name ?? floorId;
export const spaceName = (model: Model, spaceId: string) => model.space.get(spaceId)?.name ?? spaceId;
export const assetPlace = (model: Model, asset: Asset) => `${spaceName(model, asset.space_id)} · ${floorName(model, asset.floor_id)}`;

/** Parts shown in the desk list by default; furniture stays searchable but does not crowd the list. */
export const isPart = (asset: Asset) => asset.category !== 'furniture';

export type StopMark = { stopId: string; n: number; spaceId: string; floorId: string; point: Point; collected: boolean; label: string };

export const reachableLegs = (tour: Tour | null): ReachableRoute[] => (tour?.legs ?? []).filter((leg): leg is ReachableRoute => leg.reachable);

/** Numbered stop positions: the end of the leg that arrives there (what the core drew), else the room anchor. */
export function stopMarks(model: Model, tour: Tour | null): StopMark[] {
  if (!tour) return [];
  const byId = new Map(tour.stops.map(stop => [stop.stop_id, stop]));
  const arrivals = new Map<string, { point: Point; floorId: string }>();
  for (const leg of reachableLegs(tour)) {
    const walk = [...leg.segments].reverse().find(segment => segment.kind === 'walk');
    const last = walk?.points[walk.points.length - 1];
    if (walk && last) arrivals.set(leg.to_space_id, { point: last, floorId: walk.floor_id });
  }
  return tour.order.flatMap((stopId, index) => {
    const stop = byId.get(stopId);
    if (!stop) return [];
    const arrival = arrivals.get(stop.space_id);
    const space = model.space.get(stop.space_id);
    return [{ stopId, n: index + 1, spaceId: stop.space_id, floorId: arrival?.floorId ?? space?.floor_id ?? '', point: arrival?.point ?? anchorOf(model, stop.space_id), collected: stop.status === 'collected', label: stop.label }];
  });
}

/** Building-space box of everything the tour draws on one floor (for "fit to route"). */
export function routeBox(model: Model, tour: Tour | null, floorId: string): Box | null {
  const points: Point[] = [];
  for (const leg of reachableLegs(tour)) for (const segment of leg.segments) if (segment.floor_id === floorId) points.push(...segment.points);
  if (tour?.start.floor_id === floorId) points.push(tour.start.point);
  for (const mark of stopMarks(model, tour)) if (mark.floorId === floorId) points.push(mark.point);
  return bounds(points);
}

/** Floors in the order the tour visits them (first floor first). */
export function tourFloors(tour: Tour | null): string[] {
  const floors: string[] = [];
  const add = (id: string) => { if (!floors.includes(id)) floors.push(id); };
  if (tour) add(tour.start.floor_id);
  for (const leg of reachableLegs(tour)) for (const segment of leg.segments) { add(segment.floor_id); if (segment.kind !== 'walk') add(segment.to_floor_id); }
  return floors;
}

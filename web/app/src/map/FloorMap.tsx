import { memo, useMemo } from 'react';
import type { Point, ReachableRoute, Segment, Space, Tour } from '../api/types';
import { svgPoints, toSvg, viewBox, wallDirection } from '../geo/transform';
import type { Box } from '../geo/transform';
import { anchorOf, floorName, isPart, reachableLegs, stopMarks } from './model';
import type { Model, Place } from './model';

export type FloorMapProps = {
  model: Model;
  floorId: string;
  tour?: Tour | null;
  selected?: ReadonlySet<string>; // asset ids
  focusAssetId?: string | null;
  highlightSpaceIds?: readonly string[];
  you?: Place | null;
  showParts?: boolean;
  compact?: boolean; // phone minimap: fewer labels, no asset dots
  onAsset?: (assetId: string) => void;
  onSpace?: (spaceId: string) => void;
  onFloor?: (floorId: string) => void;
  fit?: { id: string; box: Box | null };
  /** phone: index into `tour.legs` drawn bold; the other legs are drawn quietly */
  focusLeg?: number;
};

const CIRCULATION = new Set(['corridor', 'lobby', 'hallway', 'entrance_hall', 'foyer', 'hall_access']);
const VERTICAL = new Set(['stairwell', 'lift', 'stair', 'elevator']);
const WET = new Set(['toilet', 'bathroom', 'kitchen', 'washroom', 'shower', 'locker_room']);
const ZONE = /_zone$|warehouse|production|assembly|logistics|workshop|hall$/;

export function roomFill(space: Space): string {
  if (VERTICAL.has(space.room_type) || space.type === 'stair' || space.type === 'lift') return '#e2e7d1';
  if (CIRCULATION.has(space.room_type) || space.type === 'corridor') return '#fcfcf9';
  if (WET.has(space.room_type)) return '#e9ece8';
  if (space.type === 'hall' || ZONE.test(space.room_type)) return '#ecebe3';
  return '#f7f6f1';
}

const fmt = (n: number) => Math.round(n * 100) / 100;

const Rooms = memo(function Rooms({ model, floorId, onSpace }: { model: Model; floorId: string; onSpace?: (id: string) => void }) {
  const spaces = model.spacesOn.get(floorId) ?? [];
  return <g className="map-rooms">
    {spaces.map(space => <polygon key={space.id} points={svgPoints(space.polygon)} fill={roomFill(space)} stroke="#b4b8aa" strokeWidth={1} vectorEffect="non-scaling-stroke" strokeLinejoin="round"
      className={onSpace ? 'map-room clickable' : 'map-room'} onClick={onSpace ? () => onSpace(space.id) : undefined}>
      <title>{space.name}</title>
    </polygon>)}
  </g>;
});

const Ghost = memo(function Ghost({ model, floorId }: { model: Model; floorId: string }) {
  const others = model.floors.filter(floor => floor.id !== floorId);
  if (!others.length) return null;
  const d = others.flatMap(floor => (model.spacesOn.get(floor.id) ?? []).map(space => `M${svgPoints(space.polygon)}Z`)).join('');
  return <path d={d} fill="none" stroke="#c9cbbf" strokeWidth={1} vectorEffect="non-scaling-stroke" strokeDasharray="3 3" opacity={0.35} pointerEvents="none"/>;
});

const Doors = memo(function Doors({ model, floorId }: { model: Model; floorId: string }) {
  const openings = model.openingsOn.get(floorId) ?? [];
  const gap = model.unit * 0.32;
  return <g className="map-doors" pointerEvents="none">
    {openings.map(opening => {
      const space = model.space.get(opening.space_ids[0] ?? '');
      if (!space) return null;
      const [dx, dy] = wallDirection(space.polygon, opening.position);
      const half = Math.min(opening.width_m, opening.kind === 'opening' ? 40 : 2.4) / 2;
      const a = toSvg([opening.position[0] - dx * half, opening.position[1] - dy * half]);
      const b = toSvg([opening.position[0] + dx * half, opening.position[1] + dy * half]);
      const closed = model.closed.has(opening.id);
      return <g key={opening.id}>
        <line x1={fmt(a[0])} y1={fmt(a[1])} x2={fmt(b[0])} y2={fmt(b[1])} stroke={closed ? '#c83432' : '#fdfdfb'} strokeWidth={gap} strokeLinecap="butt"/>
        {opening.kind !== 'opening' && <>
          <circle cx={fmt(a[0])} cy={fmt(a[1])} r={gap * 0.38} fill={opening.kind === 'entrance' ? '#191c16' : '#8f9485'}/>
          <circle cx={fmt(b[0])} cy={fmt(b[1])} r={gap * 0.38} fill={opening.kind === 'entrance' ? '#191c16' : '#8f9485'}/>
        </>}
      </g>;
    })}
  </g>;
});

/** Room labels: full name where it fits, else the short ref, else nothing; the step list is the text alternative. */
const Labels = memo(function Labels({ model, floorId, compact }: { model: Model; floorId: string; compact?: boolean }) {
  const spaces = model.spacesOn.get(floorId) ?? [];
  const size = model.unit * (compact ? 1.25 : 0.82);
  return <g className="map-labels" pointerEvents="none">
    {spaces.map(space => {
      const xs = space.polygon.map(p => p[0]), ys = space.polygon.map(p => p[1]);
      const width = Math.max(...xs) - Math.min(...xs), height = Math.max(...ys) - Math.min(...ys);
      if (height < size * 1.6) return null;
      const fits = (text: string, s: number) => text.length * s * 0.56 < width * 0.9;
      const text = !compact && fits(space.name, size) ? space.name : space.ref && fits(space.ref, size) ? space.ref : null;
      if (!text) return null;
      const [x, y] = toSvg(anchorOf(model, space.id));
      return <text key={space.id} x={fmt(x)} y={fmt(y)} fontSize={size} textAnchor="middle" dominantBaseline="central" className="map-label">{text}</text>;
    })}
  </g>;
});

const Parts = memo(function Parts({ model, floorId, onAsset }: { model: Model; floorId: string; onAsset?: (id: string) => void }) {
  const spaces = model.spacesOn.get(floorId) ?? [];
  const r = model.unit * 0.24;
  return <g className="map-parts">
    {spaces.flatMap(space => (model.assetsIn.get(space.id) ?? []).filter(isPart).map(asset => {
      const [x, y] = toSvg(asset.position);
      return <circle key={asset.id} cx={fmt(x)} cy={fmt(y)} r={r} className={onAsset ? 'map-part clickable' : 'map-part'} onClick={onAsset ? () => onAsset(asset.id) : undefined}><title>{asset.name}</title></circle>;
    }))}
  </g>;
});

function Pill({ at, text, unit, dark = true, onClick }: { at: Point; text: string; unit: number; dark?: boolean; onClick?: () => void }) {
  const size = unit * 0.78;
  const w = text.length * size * 0.56 + size * 1.4, h = size * 1.9;
  const [x, y] = toSvg(at);
  return <g transform={`translate(${fmt(x)} ${fmt(y)})`} className={onClick ? 'map-pill clickable' : 'map-pill'} onClick={onClick}>
    <rect x={-w / 2} y={-h - unit * 0.9} width={w} height={h} rx={h / 2} fill={dark ? '#191c16' : '#fff'} stroke={dark ? 'none' : '#191c16'} strokeWidth={unit * 0.06}/>
    <text y={-h / 2 - unit * 0.9} fontSize={size} textAnchor="middle" dominantBaseline="central" fill={dark ? '#fff' : '#191c16'} fontWeight={700}>{text}</text>
  </g>;
}

function walkPath(segments: Segment[], floorId: string): string {
  // contiguous segments continue one subpath, so the line has no caps or gaps at room boundaries
  let d = '';
  let last: Point | undefined;
  for (const segment of segments) {
    if (segment.kind !== 'walk' || segment.floor_id !== floorId) { last = undefined; continue; }
    const [first, ...rest] = segment.points;
    if (!first) continue;
    const joined = last && Math.abs(last[0] - first[0]) < 1e-6 && Math.abs(last[1] - first[1]) < 1e-6;
    d += `${joined ? 'L' : 'M'}${svgPoints(joined ? rest : segment.points)}`;
    last = segment.points[segment.points.length - 1];
  }
  return d.replace(/L(?=M|$)/g, '');
}

function RouteLayer({ model, floorId, tour, focusLeg, onFloor }: { model: Model; floorId: string; tour: Tour; focusLeg?: number; onFloor?: (id: string) => void }) {
  const focused = focusLeg === undefined ? reachableLegs(tour) : [tour.legs[focusLeg]].filter((leg): leg is ReachableRoute => !!leg?.reachable);
  const others = focusLeg === undefined ? [] : tour.legs.filter((leg, index): leg is ReachableRoute => index !== focusLeg && leg.reachable);
  const d = walkPath(focused.flatMap(leg => leg.segments), floorId);
  const rest = others.map(leg => walkPath(leg.segments, floorId)).join('');
  // one pill per connector and other floor: "Stairs to Floor 1", "Stairs from Floor 1" or "Stairs to and from Floor 1"
  const pills = new Map<string, { at: Point; kind: string; other: string; to: boolean; from: boolean }>();
  for (const segment of focused.flatMap(leg => leg.segments)) {
    if (segment.kind === 'walk') continue;
    const connector = model.connector.get(segment.element_id);
    const kind = segment.kind === 'lift' ? 'Lift' : 'Stairs';
    const here = segment.floor_id === floorId ? 'to' : segment.to_floor_id === floorId ? 'from' : null;
    if (!here) continue;
    const other = here === 'to' ? segment.to_floor_id : segment.floor_id;
    const space = connector?.space_ids[connector.floor_ids.indexOf(floorId)];
    const at = here === 'to' && segment.points[0] ? segment.points[0] : space ? anchorOf(model, space) : segment.points[0];
    if (!at) continue;
    const key = `${segment.element_id}:${other}`;
    const pill = pills.get(key) ?? { at, kind, other, to: false, from: false };
    pill[here] = true;
    pills.set(key, pill);
  }
  const vertical = [...pills.values()].map(pill => ({ at: pill.at, go: pill.other, text: `${pill.kind} ${pill.to && pill.from ? 'to and from' : pill.to ? 'to' : 'from'} ${floorName(model, pill.other)}` }));
  const w = model.unit * 0.5;
  return <g className="map-route" pointerEvents="none">
    {rest && <path d={rest} fill="none" stroke="#8f9485" strokeWidth={w * 0.55} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${w} ${w * 1.2}`} opacity={0.8}/>}
    {d && <>
      <path d={d} pathLength={1} className="route-draw" fill="none" stroke="#2b3420" strokeWidth={w * 1.9} strokeLinecap="round" strokeLinejoin="round"/>
      <path d={d} pathLength={1} className="route-draw" fill="none" stroke="#dcff58" strokeWidth={w} strokeLinecap="round" strokeLinejoin="round"/>
    </>}
    <g pointerEvents="auto">{vertical.map((item, i) => <Pill key={i} at={item.at} text={item.text} unit={model.unit} dark={false} onClick={onFloor ? () => onFloor(item.go) : undefined}/>)}</g>
  </g>;
}

export function FloorMap({ model, floorId, tour, selected, focusAssetId, highlightSpaceIds, you, showParts = true, compact, onAsset, onSpace, onFloor, fit, focusLeg }: FloorMapProps) {
  const vb = useMemo(() => viewBox(model.box, model.unit * 3), [model]);
  const marks = useMemo(() => (tour ? stopMarks(model, tour).filter(mark => mark.floorId === floorId) : []), [model, tour, floorId]);
  const closedSpaces = useMemo(() => {
    const ids = new Set<string>();
    for (const id of model.closed) {
      if (model.space.has(id)) ids.add(id);
      const connector = model.connector.get(id);
      if (connector) connector.space_ids.forEach(space => ids.add(space));
    }
    return [...ids].map(id => model.space.get(id)).filter((space): space is Space => !!space && space.floor_id === floorId);
  }, [model, floorId]);
  const chosen = useMemo(() => [...(selected ?? [])].map(id => model.asset.get(id)).filter(asset => asset?.floor_id === floorId), [model, selected, floorId]);
  const highlighted = (highlightSpaceIds ?? []).map(id => model.space.get(id)).filter((space): space is Space => !!space && space.floor_id === floorId);
  const u = model.unit;

  return <svg className="floor-map-svg" viewBox={vb} role="img" aria-label={`Floor map: ${floorName(model, floorId)}`} preserveAspectRatio="xMidYMid meet">
    <defs>
      <pattern id="closed-hatch" width={u * 0.9} height={u * 0.9} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width={u * 0.9} height={u * 0.9} fill="#fbe9e7"/><line x1={0} y1={0} x2={0} y2={u * 0.9} stroke="#c83432" strokeWidth={u * 0.22}/>
      </pattern>
    </defs>
    {fit?.box && <rect id={fit.id} x={fit.box.minX - u * 5} y={-fit.box.maxY - u * 5} width={fit.box.maxX - fit.box.minX + u * 10} height={fit.box.maxY - fit.box.minY + u * 10} fill="none" pointerEvents="none"/>}
    <Ghost model={model} floorId={floorId}/>
    <Rooms model={model} floorId={floorId} onSpace={onSpace}/>
    {highlighted.map(space => <polygon key={space.id} points={svgPoints(space.polygon)} fill="#f0fbc4" stroke="#191c16" strokeWidth={2} vectorEffect="non-scaling-stroke" pointerEvents="none" className="map-highlight"/>)}
    {closedSpaces.map(space => <polygon key={space.id} points={svgPoints(space.polygon)} fill="url(#closed-hatch)" stroke="#c83432" strokeWidth={2} vectorEffect="non-scaling-stroke" pointerEvents="none"><title>Closed</title></polygon>)}
    <Doors model={model} floorId={floorId}/>
    <Labels model={model} floorId={floorId} compact={compact}/>
    {showParts && !compact && <Parts model={model} floorId={floorId} onAsset={onAsset}/>}
    {tour && <RouteLayer key={`${tour.tour_id}:${tour.revision}:${floorId}:${focusLeg ?? ''}`} model={model} floorId={floorId} tour={tour} focusLeg={focusLeg} onFloor={onFloor}/>}
    {chosen.map(asset => asset && <g key={asset.id} className="map-chosen" onClick={onAsset ? () => onAsset(asset.id) : undefined}>
      <circle cx={fmt(toSvg(asset.position)[0])} cy={fmt(toSvg(asset.position)[1])} r={u * 0.55} fill="#191c16" stroke="#fff" strokeWidth={u * 0.18}/>
      {(asset.id === focusAssetId || chosen.length <= 6) && <Pill at={asset.position} text={asset.name} unit={u}/>}
    </g>)}
    {marks.map(mark => {
      const [x, y] = toSvg(mark.point);
      return <g key={mark.stopId} className="map-stop" transform={`translate(${fmt(x)} ${fmt(y)})`}>
        <circle r={u * 1.05} fill={mark.collected ? '#64685f' : '#191c16'} stroke="#fff" strokeWidth={u * 0.2}/>
        <text fontSize={u * 1.15} textAnchor="middle" dominantBaseline="central" fill={mark.collected ? '#fff' : '#dcff58'} fontWeight={800}>{mark.collected ? '✓' : mark.n}</text>
      </g>;
    })}
    {you && you.floor_id === floorId && (() => {
      const [x, y] = toSvg(you.point);
      return <g className="map-you" transform={`translate(${fmt(x)} ${fmt(y)})`} pointerEvents="none">
        <circle r={u * 1.6} fill="#191c16" opacity={0.08}/>
        <circle r={u * 0.78} fill="#fff" stroke="#191c16" strokeWidth={u * 0.16}/>
        <circle r={u * 0.42} fill="#191c16"/>
        <text y={u * 2} fontSize={u * 0.86} textAnchor="middle" dominantBaseline="central" fontWeight={800} className="map-you-label">You</text>
      </g>;
    })()}
  </svg>;
}

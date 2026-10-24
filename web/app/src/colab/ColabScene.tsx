import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { Asset, Point } from '../api/types';
import type { ColabPosition, ColabState } from '../api/colab';
import { epochMs, movementPoint, positionLabel } from '../api/colab';
import { createIsometricLayout, isometricMatrix, isometricPoint, isometricViewBox } from '../geo/isometric';
import type { IsometricLayout } from '../geo/isometric';
import { bounds, toSvg } from '../geo/transform';
import { FloorDrawing } from '../map/FloorMap';
import { anchorOf } from '../map/model';
import type { Model } from '../map/model';

type Props = {
  model: Model;
  state: ColabState | null;
  floorId: string;
  selectedAsset: string | null;
  selectedPosition: string | null;
  now: number;
  reducedMotion: boolean;
  zoom: number;
  focused: boolean;
  onFloor: (id: string) => void;
  onAsset: (id: string) => void;
  onPosition: (id: string) => void;
};

const points = (list: Point[]) => list.map(point => point.join(',')).join(' ');

function boxPolygon(point: Point, width: number, depth: number, rotation: number): Point[] {
  const angle = rotation * Math.PI / 180;
  return [[-width / 2, -depth / 2], [width / 2, -depth / 2], [width / 2, depth / 2], [-width / 2, depth / 2]].map(([x, y]) => [point[0] + x * Math.cos(angle) - y * Math.sin(angle), point[1] + x * Math.sin(angle) + y * Math.cos(angle)]);
}

function Furniture({ asset, point, layout, rank, selected, moving, onSelect }: { asset: Asset; point: Point; layout: IsometricLayout; rank: number; selected: boolean; moving: boolean; onSelect: () => void }) {
  const kind = `${asset.type} ${asset.name}`.toLowerCase();
  const coffee = /coffee|espresso/.test(kind);
  const plant = /plant/.test(kind);
  const chair = /chair|seat|sofa/.test(kind);
  const desk = /table|desk|bench/.test(kind);
  const width = asset.footprint?.width_m ?? (desk ? 2.1 : chair ? .8 : .9);
  const depth = asset.footprint?.depth_m ?? (desk ? 1.05 : .7);
  const lift = plant ? 1.4 : coffee ? 1.5 : chair ? .65 : desk ? .85 : 1.0;
  const base = boxPolygon(point, width, depth, asset.footprint?.rotation_deg ?? 0).map(p => isometricPoint(layout, p, rank));
  const top: Point[] = base.map(([x, y]) => [x, y - lift]);
  const [cx, cy] = isometricPoint(layout, point, rank);
  const fill = selected ? '#dcff58' : coffee ? '#343c36' : chair ? '#97a68e' : desk ? '#e4d6bd' : '#d2d7cc';
  return <g className={`colab-furniture${selected ? ' selected' : ''}${moving ? ' moving' : ''}`} role="button" tabIndex={0} aria-label={`${asset.name}${moving ? ', simulated move in progress' : ''}`} onClick={event => { event.stopPropagation(); onSelect(); }} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(); } }}>
    <title>{asset.name}{moving ? ' · simulated shared movement' : ''}</title>
    <ellipse cx={cx + .3} cy={cy + .2} rx={Math.max(width, depth) * .7} ry={Math.max(width, depth) * .25} fill="#273b2115"/>
    {[0, 1, 2, 3].map(edge => <polygon key={edge} points={points([base[edge], base[(edge + 1) % 4], top[(edge + 1) % 4], top[edge]])} fill={edge % 2 ? '#a8b09f' : '#bbc1b2'} stroke="#78856d" strokeWidth={.35} vectorEffect="non-scaling-stroke"/>)}
    <polygon points={points(top)} fill={fill} stroke={selected ? '#344520' : '#88957c'} strokeWidth={selected ? 1.5 : .55} vectorEffect="non-scaling-stroke"/>
    {coffee && <><rect x={cx - .25} y={cy - lift - .22} width={.5} height={.35} rx={.07} fill="#dcff58"/><circle cx={cx + .36} cy={cy - lift + .08} r={.09} fill="#fff"/></>}
    {plant && <><circle cx={cx - .35} cy={cy - lift - .3} r={.7} fill="#6c8661"/><circle cx={cx + .3} cy={cy - lift - .4} r={.65} fill="#819b71"/><circle cx={cx} cy={cy - lift - .85} r={.55} fill="#a3b792"/></>}
    {moving && <circle cx={cx} cy={cy - lift - .7} r={.3} fill="#dcff58" stroke="#344520" strokeWidth={.1}/>}
    <circle cx={cx} cy={cy - lift / 2} r={1.2} fill="transparent" className="colab-asset-hit"/>
  </g>;
}

function PositionPin({ position, layout, rank, selected, onSelect }: { position: ColabPosition; layout: IsometricLayout; rank: number; selected: boolean; onSelect: () => void }) {
  const p: Point = [position.x, position.y];
  const [x, y] = isometricPoint(layout, p, rank);
  const color = position.source === 'wifi_fingerprint' ? '#497bbd' : position.source === 'simulated' ? '#ba7b31' : '#55784a';
  const [sx, sy] = toSvg(p);
  return <g className={`colab-position${position.stale ? ' stale' : ''}`} role="button" tabIndex={0} aria-label={`${position.label}: ${positionLabel(position)}`} onClick={event => { event.stopPropagation(); onSelect(); }} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(); } }}>
    {position.accuracy_m !== null && position.accuracy_m > 0 && <g transform={isometricMatrix(layout, rank)}><circle cx={sx} cy={sy} r={position.accuracy_m} fill={color} fillOpacity={.08} stroke={color} strokeOpacity={.4} strokeWidth={1} strokeDasharray="3 3" vectorEffect="non-scaling-stroke"/></g>}
    <ellipse cx={x} cy={y} rx={1.25} ry={.65} fill={color} opacity={.18}/>
    <path d={`M${x} ${y} L${x} ${y - 3.4}`} stroke={color} strokeWidth={1.2} vectorEffect="non-scaling-stroke"/>
    <circle cx={x} cy={y - 4.2} r={selected ? 1.3 : 1.05} fill={color} stroke="#fff" strokeWidth={.45}/>
    <circle cx={x} cy={y - 4.2} r={.32} fill="#fff"/>
    <text x={x} y={y - 6.2} textAnchor="middle" className="colab-map-label" fontSize={1.65}>{position.label}</text>
    <title>{positionLabel(position)}{position.accuracy_m ? ` · indicative radius ${position.accuracy_m.toFixed(1)} m, unvalidated` : ''}</title>
  </g>;
}

/** Uses the exact shared isometric projection and room/door layers, adding only showcase furniture. */
export function ColabScene({ model, state, floorId, selectedAsset, selectedPosition, now, reducedMotion, zoom, focused, onFloor, onAsset, onPosition }: Props) {
  const [phone, setPhone] = useState(() => window.matchMedia('(max-width: 760px)').matches);
  useEffect(() => {
    const query = window.matchMedia('(max-width: 760px)');
    const update = () => setPhone(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  const layout = useMemo(() => {
    const base = createIsometricLayout(model.box, model.floors.length);
    if (focused) return base;
    // Compact overview spacing is purely diagram layout, never a change to building heights.
    const gap = base.gap * .65;
    return { ...base, gap, scene: { ...base.scene, minY: base.scene.minY + (base.gap - gap) * (model.floors.length - 1), maxX: base.scene.maxX + 10 } };
  }, [model, focused]);
  const moving = new Map((state?.movements ?? []).map(movement => [movement.asset_id, movement]));
  const current = new Map((state?.assets ?? []).map(asset => [asset.asset_id, asset]));
  const focus = model.floors.findIndex(floor => floor.id === floorId);
  const height = layout.footprint.maxY - layout.footprint.minY;
  const focusBox = phone
    ? `${layout.footprint.minX - 4} ${-focus * layout.gap - height * .6} ${layout.footprint.maxX - layout.footprint.minX + 16} ${height * 1.25}`
    : `${layout.scene.minX - 4} ${-focus * layout.gap - height * .82} ${layout.scene.maxX - layout.scene.minX + 16} ${height * 1.7}`;
  const camera: CSSProperties = { transform: `scale(${zoom})`, transformOrigin: `0px ${focused ? -focus * layout.gap : -(model.floors.length - 1) * layout.gap / 2}px` };
  return <svg className={`colab-building-scene${focused ? ' focused' : ''}`} viewBox={focused ? focusBox : isometricViewBox(layout)} aria-label={`Interactive schematic ${model.floors.length}-level Munich Urban Colab building. Select a floor, furnishing or location marker.`} role="group">
    <defs>
      <filter id="colab-shadow" x="-30%" y="-30%" width="170%" height="180%"><feDropShadow dx="1.5" dy="3" stdDeviation="2.1" floodColor="#435239" floodOpacity=".11"/></filter>
    </defs>
    <g className="colab-scene-camera" style={camera}>
      {model.floors.map((floor, rank) => {
        const active = floor.id === floorId;
        if (phone && focused && !active) return null;
        const spaces = model.spacesOn.get(floor.id) ?? [];
        const all = spaces.flatMap(space => space.polygon.map(point => isometricPoint(layout, point, rank)));
        const box = bounds(all)!;
        const assets = model.snapshot.building.assets.filter(asset => (current.get(asset.id)?.floor_id ?? asset.floor_id) === floor.id).sort((a, b) => {
          const ap = current.get(a.id)?.position ?? a.position, bp = current.get(b.id)?.position ?? b.position;
          return isometricPoint(layout, ap, rank)[1] - isometricPoint(layout, bp, rank)[1];
        });
        const connectors = model.snapshot.building.vertical_connectors.filter(connector => connector.floor_ids.includes(floor.id));
        return <g key={floor.id} className={`colab-scene-floor${active ? ' active' : ''}${floor.level < 3 ? ' contextual' : ''}`} data-floor-id={floor.id} onClick={() => onFloor(floor.id)}>
          <g filter="url(#colab-shadow)">
            {spaces.flatMap(space => space.polygon.map((p, i) => {
              const a = isometricPoint(layout, p, rank), b = isometricPoint(layout, space.polygon[(i + 1) % space.polygon.length], rank);
              return <polygon key={`${space.id}:${i}`} points={points([a, b, [b[0], b[1] + layout.slab], [a[0], a[1] + layout.slab]])} fill={b[0] > a[0] ? '#b8c1ad' : '#d1d8c6'} stroke="#a1ac96" strokeWidth={.4} vectorEffect="non-scaling-stroke"/>;
            }))}
            <g transform={isometricMatrix(layout, rank)}><FloorDrawing model={model} floorId={floor.id} showParts={false} showLabels={false}/></g>
          </g>
          {assets.map(asset => {
            const movement = moving.get(asset.id);
            const point = movement ? movementPoint(movement, now, reducedMotion) : current.get(asset.id)?.position ?? asset.position;
            const isMoving = !!movement && now >= epochMs(movement.started_at) && now < epochMs(movement.started_at) + movement.duration_s * 1000;
            return <Furniture key={asset.id} asset={asset} point={point} layout={layout} rank={rank} selected={asset.id === selectedAsset} moving={isMoving} onSelect={() => { onFloor(floor.id); onAsset(asset.id); }}/>;
          })}
          {connectors.map(connector => {
            const spaceId = connector.space_ids[connector.floor_ids.indexOf(floor.id)];
            if (!spaceId) return null;
            const [x, y] = isometricPoint(layout, anchorOf(model, spaceId), rank);
            return <g key={connector.id} className="colab-connector" pointerEvents="none" transform={`translate(${x} ${y})`}>
              <rect x={-1.9} y={-1.6} width={3.8} height={3.2} rx={.6} fill="#eff4e5" stroke="#6d7e60" strokeWidth={.15}/>
              {connector.kind === 'lift' ? <><path d="M-.7 -.7V.7M.7 -.7V.7M-1 -.3L-.7-.7-.4-.3M.4.3L.7.7 1 .3" fill="none" stroke="#526748" strokeWidth={.24}/></> : <path d="M-1 .8H-.5V.3H0V-.2H.5V-.7H1" fill="none" stroke="#526748" strokeWidth={.25}/>}
              <title>{connector.name || connector.kind}</title>
            </g>;
          })}
          {active && spaces.filter(space => {
            const b = bounds(space.polygon);
            return space.room_type === 'kitchen' || (!!b && (b.maxX - b.minX) * (b.maxY - b.minY) > 65 && !/corridor|hallway|lift|stair/.test(space.room_type));
          }).map(space => {
            const [x, y] = isometricPoint(layout, anchorOf(model, space.id), rank);
            return <text key={space.id} x={x} y={y + 2.2} fontSize={1.5} textAnchor="middle" className="colab-room-name" pointerEvents="none">{space.name.replace(/\s+\d+\.\d+$/, '')}</text>;
          })}
          {(state?.positions ?? []).filter(position => position.floor_id === floor.id).map(position => <PositionPin key={position.device_id} position={position} layout={layout} rank={rank} selected={selectedPosition === position.device_id} onSelect={() => { onFloor(floor.id); onPosition(position.device_id); }}/>) }
          <g className="colab-slab-label" role="button" tabIndex={0} aria-label={`Focus ${floor.name}`} aria-pressed={active} onClick={event => { event.stopPropagation(); onFloor(floor.id); }} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onFloor(floor.id); } }} transform={`translate(${box.maxX + 3} ${(box.minY + box.maxY) / 2})`}>
            <line x1={-5} y1={0} x2={1.5} y2={0} stroke={active ? '#687952' : '#bbc3b0'} strokeWidth={.2}/>
            <rect x={1} y={-3} width={7} height={6} rx={2} fill={active ? '#191c16' : '#ffffff'} stroke={active ? '#191c16' : '#d5dacd'} strokeWidth={.15}/>
            <text x={4.5} y={.2} textAnchor="middle" dominantBaseline="middle" fontSize={2.7} fontWeight={750} fill={active ? '#dcff58' : '#6b7563'}>{floor.level.toString().padStart(2, '0')}</text>
          </g>
        </g>;
      })}
    </g>
  </svg>;
}

import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import { createIsometricLayout, isometricBox, isometricMatrix, isometricPoint, isometricViewBox } from '../geo/isometric';
import { bounds } from '../geo/transform';
import { FloorDrawing } from './FloorMap';
import type { FloorMapProps } from './FloorMap';
import { anchorOf } from './model';

/** Exploded, roofless floor slabs. The projection changes the drawing, never the core coordinates. */
export function IsometricBuilding(props: FloorMapProps) {
  const { model, floorId, onFloor, fit } = props;
  const layout = useMemo(() => createIsometricLayout(model.box, model.floors.length), [model]);
  const rank = Math.max(0, model.floors.findIndex(floor => floor.id === floorId));
  const height = layout.footprint.maxY - layout.footprint.minY;
  // A bounded camera nudge draws attention to the chosen level without losing the other floors.
  const focusPan = Math.max(-height * .16, Math.min(height * .16, (rank - (model.floors.length - 1) / 2) * layout.gap * .18));
  const target = fit?.box ? isometricBox(layout, fit.box, rank) : null;
  const titleSize = Math.max(1, (layout.footprint.maxX - layout.footprint.minX) * .038);
  const labelSize = titleSize * .48;
  const cameraStyle: CSSProperties = { transform: `translateY(${focusPan}px)` };

  return <svg className="floor-map-svg isometric-building" viewBox={isometricViewBox(layout)} role="group" aria-label={`Exploded 3D building: ${model.floors.length} floors`} preserveAspectRatio="xMidYMid meet">
    <g className="isometric-camera" style={cameraStyle}>
      {model.floors.map((floor, index) => {
        const active = floor.id === floorId;
        const spaces = model.spacesOn.get(floor.id) ?? [];
        const floorY = -index * layout.gap;
        const floorBounds = bounds(spaces.flatMap(space => space.polygon.map(point => isometricPoint(layout, point, index))));
        const emphasis: CSSProperties = { transform: `translate(${active ? layout.slab * 2 : 0}px, ${floorY}px) scale(${active ? 1.08 : 1}) translateY(${-floorY}px)` };
        return <g key={floor.id} className={`isometric-floor${active ? ' active' : ''}`} data-floor-id={floor.id} style={emphasis} onClick={() => onFloor?.(floor.id)}>
          {active && target && <rect id={fit!.id} x={target.minX - layout.slab * 2} y={target.minY - layout.slab * 2} width={target.maxX - target.minX + layout.slab * 4} height={target.maxY - target.minY + layout.slab * 4} fill="none" pointerEvents="none"/>}
          <g className="isometric-slab" pointerEvents="none">
            {spaces.flatMap(space => space.polygon.map((point, edge) => {
              const next = space.polygon[(edge + 1) % space.polygon.length]!;
              const a = isometricPoint(layout, point, index), b = isometricPoint(layout, next, index);
              return <polygon key={`${space.id}:${edge}`} points={`${a[0]},${a[1]} ${b[0]},${b[1]} ${b[0]},${b[1] + layout.slab} ${a[0]},${a[1] + layout.slab}`} fill={b[0] > a[0] ? '#bac4ae' : '#d0d7c5'} stroke="#adb6a2" strokeWidth={.35} vectorEffect="non-scaling-stroke"/>;
            }))}
          </g>
          <g transform={isometricMatrix(layout, index)}>
            <FloorDrawing {...props} floorId={floor.id} fit={undefined} compact={!active} showLabels={false}/>
          </g>
          {active && <g className="isometric-room-labels" pointerEvents="none">
            {spaces.map(space => {
              const [x, y] = isometricPoint(layout, anchorOf(model, space.id), index);
              return space.ref ? <text key={space.id} x={x} y={y} fontSize={labelSize} textAnchor="middle" dominantBaseline="central">{space.ref}</text> : null;
            })}
          </g>}
          <g className="isometric-floor-label" role="button" tabIndex={0} aria-label={`Focus ${floor.name}`} aria-pressed={active} onClick={event => { event.stopPropagation(); onFloor?.(floor.id); }} onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); onFloor?.(floor.id); }
          }} transform={`translate(${floorBounds?.minX ?? layout.footprint.minX} ${(floorBounds?.minY ?? floorY + layout.footprint.minY) - titleSize * .7})`}>
            <rect x={-titleSize * .55} y={-titleSize * .85} width={Math.max(4, floor.name.length * .62 + 2) * titleSize} height={titleSize * 1.7} rx={titleSize * .55}/>
            <text fontSize={titleSize} fontWeight={750} dominantBaseline="central">{floor.name}</text>
          </g>
        </g>;
      })}
    </g>
  </svg>;
}

import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import { createIsometricLayout, isometricBox, isometricFocusViewBox, isometricMatrix, isometricPoint } from '../geo/isometric';
import { FloorDrawing } from './FloorMap';
import type { FloorMapProps } from './FloorMap';

/** Focused exploded slabs; projection and emphasis never change measured route geometry. */
export function IsometricBuilding(props: FloorMapProps) {
  const { model, floorId, onFloor, fit } = props;
  const layout = useMemo(() => createIsometricLayout(model.box, model.floors.length), [model]);
  const rank = Math.max(0, model.floors.findIndex(floor => floor.id === floorId));
  const target = fit?.box ? isometricBox(layout, fit.box, rank) : null;
  const cameraStyle: CSSProperties = { transform: `translateY(${rank * layout.gap}px)` };
  // Draw the active plane last, so neighbouring context never covers its parts or route.
  const layers = model.floors.map((floor, index) => ({ floor, index })).sort((a, b) =>
    Number(a.index === rank) - Number(b.index === rank) || Math.abs(b.index - rank) - Math.abs(a.index - rank));

  return <svg className="floor-map-svg isometric-building" viewBox={isometricFocusViewBox(layout)} role="group" aria-label={`Exploded 3D building: ${model.floors.length} floors`} preserveAspectRatio="xMidYMid meet">
    <g className="isometric-camera" style={cameraStyle}>
      {layers.map(({ floor, index }) => {
        const active = index === rank;
        const spaces = model.spacesOn.get(floor.id) ?? [];
        const floorY = -index * layout.gap;
        const difference = index - rank;
        // Compress distant context like an accordion while keeping physical floor order.
        const distance = Math.abs(difference);
        const contextY = distance ? -Math.sign(difference) * layout.gap * (1 + .2 * Math.log2(distance)) : 0;
        const adjustment = contextY - (floorY + rank * layout.gap);
        const emphasis: CSSProperties = { transform: `translate(0px, ${floorY + adjustment}px) scale(${active ? 1.4 : .76}) translateY(${-floorY}px)` };
        return <g key={floor.id} className={`isometric-floor${active ? ' active' : ''}`} data-floor-id={floor.id} style={emphasis}
          role="button" tabIndex={0} aria-label={`Focus ${floor.name}`} aria-pressed={active}
          onClick={() => onFloor?.(floor.id)} onKeyDown={event => {
            if (event.target !== event.currentTarget) return;
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onFloor?.(floor.id); }
          }}>
          {active && target && <rect id={fit!.id} x={target.minX - layout.slab * 2} y={target.minY - layout.slab * 2} width={target.maxX - target.minX + layout.slab * 4} height={target.maxY - target.minY + layout.slab * 4} fill="none" pointerEvents="none"/>}
          <g className="isometric-slab" pointerEvents="none">
            {spaces.flatMap(space => space.polygon.map((point, edge) => {
              const next = space.polygon[(edge + 1) % space.polygon.length]!;
              const a = isometricPoint(layout, point, index), b = isometricPoint(layout, next, index);
              return <polygon key={`${space.id}:${edge}`} points={`${a[0]},${a[1]} ${b[0]},${b[1]} ${b[0]},${b[1] + layout.slab} ${a[0]},${a[1] + layout.slab}`} fill={b[0] > a[0] ? '#bac4ae' : '#d0d7c5'} stroke="#adb6a2" strokeWidth={.35} vectorEffect="non-scaling-stroke"/>;
            }))}
          </g>
          <g transform={isometricMatrix(layout, index)}>
            <FloorDrawing {...props} floorId={floor.id} fit={undefined} compact={!active} showLabels={false} showAssetLabels={false}/>
          </g>
        </g>;
      })}
    </g>
  </svg>;
}

import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import { createIsometricLayout, createIsometricScene, isometricMatrix, isometricPoint, isometricViewBox } from '../geo/isometric';
import { FloorDrawing } from './FloorMap';
import type { FloorMapProps } from './FloorMap';

/** Focused exploded slabs; projection and emphasis never change measured route geometry. */
export function IsometricBuilding(props: FloorMapProps) {
  const { model, floorId, onFloor, fit } = props;
  const layout = useMemo(() => createIsometricLayout(model.box, model.floors.length), [model]);
  const rank = Math.max(0, model.floors.findIndex(floor => floor.id === floorId));
  const scene = createIsometricScene(layout, rank);
  // Draw the active plane last, so neighbouring context never covers its parts or route.
  const layers = model.floors.map((floor, index) => ({ floor, index })).sort((a, b) =>
    Number(a.index === rank) - Number(b.index === rank) || Math.abs(b.index - rank) - Math.abs(a.index - rank));

  return <svg className="floor-map-svg isometric-building" viewBox={isometricViewBox(scene)} role="group" aria-label={`Exploded 3D building: ${model.floors.length} floors`} preserveAspectRatio="xMidYMid meet">
    {fit && <rect id={fit.id} x={scene.focus.minX} y={scene.focus.minY} width={scene.focus.maxX - scene.focus.minX} height={scene.focus.maxY - scene.focus.minY} fill="none" pointerEvents="none" aria-hidden="true"/>}
    <g className="isometric-camera">
      {layers.map(({ floor, index }) => {
        const active = index === rank;
        const spaces = model.spacesOn.get(floor.id) ?? [];
        const frame = scene.floors[index]!;
        const emphasis: CSSProperties = { transform: `translateY(${frame.centerY}px) scale(${frame.scale}) translateY(${index * layout.gap}px)` };
        return <g key={floor.id} className={`isometric-floor${active ? ' active' : ''}`} data-floor-id={floor.id} style={emphasis}
          role="button" tabIndex={0} aria-label={`Focus ${floor.name}`} aria-pressed={active}
          onClick={() => onFloor?.(floor.id)} onKeyDown={event => {
            if (event.target !== event.currentTarget) return;
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onFloor?.(floor.id); }
          }}>
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

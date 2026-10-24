import { Maximize, Minus, Plus } from 'lucide-react';
import { useEffect, useId, useMemo, useRef } from 'react';
import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch';
import type { ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';
import { bounds } from '../geo/transform';
import type { Box } from '../geo/transform';
import { FloorMap } from './FloorMap';
import type { FloorMapProps } from './FloorMap';
import { routeBox, stopMarks } from './model';

type Props = FloorMapProps & {
  /** changes of this key re-frame the map: a new tour revision fits the route, a new focus fits the room */
  frameKey?: string;
  frame?: 'route' | 'space' | 'all';
  frameSpaceIds?: readonly string[];
};

const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export function MapView({ frameKey, frame = 'all', frameSpaceIds, ...map }: Props) {
  const { model, floorId, tour, route, onFloor } = map;
  const ref = useRef<ReactZoomPanPinchRef>(null);
  const fitId = `fit-${useId().replace(/:/g, '')}`;
  const box: Box | null = useMemo(() => {
    if (frame === 'route' && route) return bounds(route.segments.filter(segment => segment.floor_id === floorId).flatMap(segment => segment.points));
    if (frame === 'route' && tour) return routeBox(model, tour, floorId, map.focusLeg);
    if (frame === 'space' && frameSpaceIds?.length) return bounds(frameSpaceIds.flatMap(id => (model.space.get(id)?.floor_id === floorId ? model.space.get(id)?.polygon ?? [] : [])));
    return null;
  }, [frame, tour, route, model, floorId, frameSpaceIds, map.focusLeg]);

  const fitNow = (animate = true) => {
    const controls = ref.current;
    if (!controls) return;
    const time = animate && !reducedMotion() ? 500 : 0;
    if (box) void controls.zoomToElement(fitId, { maxScale: frame === 'space' ? 3 : 5, animationTime: time });
    else controls.resetTransform(time);
  };

  useEffect(() => {
    // fit now and once more after layout settles (lazy chunks, fonts, a dock that changes height)
    const id = requestAnimationFrame(() => fitNow());
    const again = setTimeout(() => fitNow(false), 350);
    return () => { cancelAnimationFrame(id); clearTimeout(again); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frameKey, floorId, box ? 1 : 0]);

  // re-frame when the visible map area changes size (phone dock grows or shrinks, rotation)
  const view = useRef<HTMLDivElement>(null);
  const fitRef = useRef(fitNow);
  fitRef.current = fitNow;
  useEffect(() => {
    const element = view.current;
    if (!element || typeof ResizeObserver === 'undefined') return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let first = true;
    const observer = new ResizeObserver(() => {
      if (first) { first = false; return; }
      clearTimeout(timer);
      timer = setTimeout(() => fitRef.current(false), 120);
    });
    observer.observe(element);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, []);

  const stopsOn = (id: string) => stopMarks(model, tour ?? null).filter(mark => mark.floorId === id).length;
  const floors = [...model.floors].reverse();

  return <div className="map-view" ref={view}>
    <TransformWrapper ref={ref} minScale={0.6} maxScale={12} limitToBounds={false} doubleClick={{ mode: 'zoomIn', step: 0.7 }} wheel={{ step: 0.12 }} centerOnInit>
      <TransformComponent wrapperClass="map-wrapper" contentClass="map-content">
        <FloorMap {...map} fit={{ id: fitId, box }}/>
      </TransformComponent>
    </TransformWrapper>
    {floors.length > 1 && <nav className="floor-switch surface" aria-label="Floors">
      {floors.map(floor => {
        const n = stopsOn(floor.id);
        return <button key={floor.id} className={floor.id === floorId ? 'active' : ''} aria-pressed={floor.id === floorId} onClick={() => onFloor?.(floor.id)} title={floor.name}>
          <span>{floor.name}</span>{n > 0 && <span className="floor-stops" aria-label={`${n} stops`}>{n}</span>}
        </button>;
      })}
    </nav>}
    <div className="map-controls surface" role="group" aria-label="Map zoom">
      <button onClick={() => ref.current?.zoomIn(0.5)} aria-label="Zoom in"><Plus size={18}/></button>
      <button onClick={() => ref.current?.zoomOut(0.5)} aria-label="Zoom out"><Minus size={18}/></button>
      <button onClick={() => fitNow()} aria-label={tour || route ? 'Fit route' : 'Fit building'} title={tour || route ? 'Fit route' : 'Fit building'}><Maximize size={17}/></button>
    </div>
  </div>;
}

import { Maximize, Minus, Plus } from 'lucide-react';
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch';
import type { ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';
import { bounds } from '../geo/transform';
import type { Box } from '../geo/transform';
import { FloorMap } from './FloorMap';
import { IsometricBuilding } from './IsometricBuilding';
import type { FloorMapProps } from './FloorMap';
import { routeBox } from './model';

type Props = FloorMapProps & {
  /** Desk-only building overview; phone guidance and admin keep their flat floor maps. */
  isometric?: boolean;
  /** changes of this key re-frame the map: a new tour revision fits the route, a new focus fits the room */
  frameKey?: string;
  frame?: 'route' | 'space' | 'all';
  frameSpaceIds?: readonly string[];
};

const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export function MapView({ frameKey, frame = 'all', frameSpaceIds, isometric = false, ...map }: Props) {
  const { model, floorId, tour, route, onFloor } = map;
  const [desktop, setDesktop] = useState(() => typeof matchMedia === 'undefined' || matchMedia('(min-width: 1101px)').matches);
  useEffect(() => {
    if (typeof matchMedia === 'undefined') return;
    const media = matchMedia('(min-width: 1101px)');
    const update = () => setDesktop(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  const stacked = isometric && desktop && model.floors.length > 1;
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
    if (stacked && frame !== 'space') { controls.resetTransform(time); return; }
    if (box) void controls.zoomToElement(fitId, { maxScale: stacked ? 2 : frame === 'space' ? 3 : 5, animationTime: time });
    else controls.resetTransform(time);
  };

  useEffect(() => {
    // fit now and once more after layout settles (lazy chunks, fonts, a dock that changes height)
    const id = requestAnimationFrame(() => fitNow());
    const again = setTimeout(() => fitNow(false), 350);
    return () => { cancelAnimationFrame(id); clearTimeout(again); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frameKey, floorId, stacked, box ? 1 : 0]);

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

  const floors = [...model.floors].reverse();

  return <div className={`map-view${stacked ? ' isometric-view' : ''}`} ref={view}>
    <TransformWrapper ref={ref} minScale={0.6} maxScale={12} limitToBounds={false} doubleClick={{ mode: 'zoomIn', step: 0.7 }} wheel={{ step: 0.12 }} centerOnInit>
      <TransformComponent wrapperClass="map-wrapper" contentClass="map-content">
        {stacked ? <IsometricBuilding {...map} fit={{ id: fitId, box }}/> : <FloorMap {...map} fit={{ id: fitId, box }}/>}
      </TransformComponent>
    </TransformWrapper>
    {floors.length > 1 && <nav className="floor-switch" aria-label="Floors">
      {floors.map(floor => <button key={floor.id} className={floor.id === floorId ? 'active' : ''} aria-label={floor.name} aria-pressed={floor.id === floorId} onClick={() => onFloor?.(floor.id)}>
        <span className="floor-level" aria-hidden="true">{floor.level}</span>
      </button>)}
    </nav>}
    <div className="map-controls surface" role="group" aria-label="Map zoom">
      <button onClick={() => ref.current?.zoomIn(0.5)} aria-label="Zoom in"><Plus size={18}/></button>
      <button onClick={() => ref.current?.zoomOut(0.5)} aria-label="Zoom out"><Minus size={18}/></button>
      <button onClick={() => fitNow()} aria-label={tour || route ? 'Fit route' : 'Fit building'} title={tour || route ? 'Fit route' : 'Fit building'}><Maximize size={17}/></button>
    </div>
  </div>;
}

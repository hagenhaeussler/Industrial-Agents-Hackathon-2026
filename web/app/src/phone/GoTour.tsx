import { LoaderCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { ApiError, api, ensureSession, mockMode } from '../api/client';
import type { Session, Tour } from '../api/types';
import { policyLabel } from '../desk/TourPanel';
import { MapView } from '../map/MapView';
import { buildModel, floorName, spaceName } from '../map/model';
import type { Model } from '../map/model';
import { DemoBadge } from '../ui/DemoBadge';

/**
 * `/go/:tourId` (C01 slice): loads the handed-off tour, creates the phone session at the tour start
 * (source `tour_start`, confidence low; CONTRACTS §10) and shows the same stops and route.
 * The full walking journey (start confirmation, directions, progress, voice, reroute) is C02.
 */
export function GoTour({ tourId }: { tourId: string }) {
  const [tour, setTour] = useState<Tour | null>(null);
  const [model, setModel] = useState<Model | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [floorId, setFloorId] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        const loaded = await api.tour(tourId);
        const snapshot = await api.building(loaded.building_id);
        if (!live) return;
        setTour(loaded); setModel(buildModel(snapshot)); setFloorId(loaded.start.floor_id);
        let phone = await ensureSession(loaded.building_id, 'phone');
        phone = await api.updateSession(phone.session_id, { active_tour_id: loaded.tour_id, position: { ...loaded.start, source: 'tour_start', confidence: 'low', heading_deg: null, marker_id: null } });
        if (live) setSession(phone);
      } catch (reason) {
        if (live) setError(reason instanceof ApiError && reason.status === 404 ? 'This tour does not exist any more. Plan it again on the desk.' : reason instanceof Error ? reason.message : 'The tour did not load.');
      }
    })();
    return () => { live = false; };
  }, [tourId]);

  if (error) return <main className="desk-message"><div className="surface notice"><h1>Tour not available</h1><p>{error}</p></div></main>;
  if (!tour || !model) return <main className="desk-message"><p className="loading"><LoaderCircle className="spin" size={20}/>Opening your tour…</p></main>;
  const stops = new Map(tour.stops.map(stop => [stop.stop_id, stop]));

  return <main className="go">
    <MapView model={model} floorId={floorId} onFloor={setFloorId} tour={tour} you={session?.position ?? tour.start} frame="route" frameKey={`tour:${tour.tour_id}:${tour.revision}`}/>
    <section className="go-sheet surface" aria-labelledby="go-title">
      <div className="sheet-handle"/>
      <p className="policy">{policyLabel(tour)} {mockMode && <DemoBadge reason="Mock mode"/>}</p>
      <h1 id="go-title">{tour.order.length} stops · {Math.round(tour.length_m)} m</h1>
      <p className="muted">Starts at {spaceName(model, tour.start.space_id)} · {floorName(model, tour.start.floor_id)}</p>
      <ol className="stop-list compact">
        {tour.order.map((stopId, index) => {
          const stop = stops.get(stopId);
          return stop && <li key={stopId} className={stop.status}><span className="stop-n" aria-hidden="true">{stop.status === 'collected' ? '✓' : index + 1}</span><span className="stop-copy"><strong>{stop.label.split(' · ')[0]}</strong><span>{stop.label.split(' · ').slice(1).join(' · ')}</span></span></li>;
        })}
      </ol>
    </section>
  </main>;
}

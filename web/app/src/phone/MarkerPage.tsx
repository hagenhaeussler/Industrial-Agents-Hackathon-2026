import { ArrowRight, LoaderCircle, MapPin } from 'lucide-react';
import { useEffect, useState } from 'react';
import { ApiError, api, ensureSession } from '../api/client';
import type { Marker, Session } from '../api/types';
import { navigate } from '../router';

/**
 * `/m/:markerId`, opened by the phone's camera app from a printed position code (CONTRACTS §10):
 * the stored phone session (or a fresh one) gets the marker's standing point with high confidence.
 * With an active tour it replans from here and continues it.
 */
export function MarkerPage({ markerId }: { markerId: string }) {
  const [marker, setMarker] = useState<Marker | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        const found = await api.marker(markerId);
        if (!live) return;
        setMarker(found);
        const phone = await ensureSession(found.building_id, 'phone');
        const position = { space_id: found.space_id, floor_id: found.floor_id, point: found.point, heading_deg: found.heading_deg, source: 'marker' as const, marker_id: found.marker_id, confidence: 'high' as const };
        const updated = await api.updateSession(phone.session_id, { position });
        if (updated.active_tour_id) {
          await api.replan(updated.active_tour_id, { session_id: updated.session_id, from: position, reason: `marker ${found.marker_id}` }).catch(() => undefined);
          try { localStorage.setItem(`tyb.confirmed.${updated.active_tour_id}`, '1'); } catch { /* ignore */ }
        }
        if (live) setSession(updated);
      } catch (reason) {
        if (live) setError(reason instanceof ApiError && reason.status === 404 ? 'This position code is not known. Choose your room in the tour instead.' : reason instanceof Error ? reason.message : 'The position code did not load.');
      }
    })();
    return () => { live = false; };
  }, [markerId]);

  if (error) return <main className="desk-message"><div className="surface notice"><h1>Position code not found</h1><p>{error}</p></div></main>;
  if (!marker || !session) return <main className="desk-message"><p className="loading"><LoaderCircle className="spin" size={20}/>Reading the position code…</p></main>;
  return <main className="desk-message"><div className="surface notice marker-notice">
    <span className="brand-mark"><MapPin size={20}/></span>
    <h1>You are at {marker.label}</h1>
    <p>Stand on the floor sticker facing the code. Your position is saved for this phone.</p>
    {session.active_tour_id
      ? <button className="primary-button" onClick={() => navigate(`/go/${session.active_tour_id}`)}>Continue your tour<ArrowRight size={18}/></button>
      : <p className="fineprint">No tour is active on this phone. Scan the code on the desk screen to start one.</p>}
  </div></main>;
}

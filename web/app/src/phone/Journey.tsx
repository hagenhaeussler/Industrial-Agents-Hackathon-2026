import { Blobatar } from '@blobatar/react';
import { happy, idle } from 'blobatar/expression';
import { ArrowLeft, ArrowRight, ArrowUp, ArrowUpDown, Check, CornerUpLeft, CornerUpRight, DoorOpen, Flag, Footprints, ListOrdered, LoaderCircle, MapPin, Mic, MicOff, MoveUpLeft, MoveUpRight, Navigation, ScanQrCode, TriangleAlert, Undo2, WifiOff, X } from 'lucide-react';
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, api, ensureSession, mockMode } from '../api/client';
import { useLatest } from '../api/latest';
import type { Display, ManeuverKind, Marker, Position, ServerMessage, Session, Tour, TourStop } from '../api/types';
import { useBuildingSocket } from '../api/ws';
import { StartPicker } from '../desk/StartPicker';
import { MapView } from '../map/MapView';
import { anchorOf, buildModel, displayOrder, floorName, isProvisional, placeOf, spaceName } from '../map/model';
import type { Model } from '../map/model';
import { navigate } from '../router';
import { DemoBadge } from '../ui/DemoBadge';
import { ChatSheet } from './ChatSheet';
import { atStop, blockedReason, cleanText, clampStep, collectedCount, context, currentLeg, currentLegIndex, currentTarget, destinationLabel, finalDestinationPending, metresToNext, pendingStops, rerouteNotice, stepPosition, stopLabel, tourDone } from './guidance';
import { VoiceRoot, useVoiceSession } from './voice';

const Scanner = lazy(() => import('./Scanner').then(module => ({ default: module.Scanner })));

const ICONS: Record<ManeuverKind, typeof ArrowUp> = {
  depart: Navigation, straight: ArrowUp, enter: DoorOpen, turn_left: CornerUpLeft, turn_right: CornerUpRight,
  slight_left: MoveUpLeft, slight_right: MoveUpRight, u_turn: Undo2, take_lift: ArrowUpDown, take_stairs: Footprints, arrive: Flag,
};
export const ManeuverIcon = ({ kind, size = 34 }: { kind: ManeuverKind; size?: number }) => { const Icon = ICONS[kind] ?? ArrowUp; return <Icon size={size} strokeWidth={2.4} aria-hidden="true"/>; };

const message = (error: unknown) => error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong.';
const storage = {
  get: (key: string) => { try { return localStorage.getItem(key); } catch { return null; } },
  set: (key: string, value: string) => { try { localStorage.setItem(key, value); } catch { /* ignore */ } },
};

type Notice = { text: string; blocked: boolean; tone: 'change' | 'info' };

/** `/go/:tourId`: the walking journey on the phone (UX J4b–J7). */
export function Journey({ tourId }: { tourId: string }) {
  const [session, setSession] = useState<Session | null>(null);
  return <VoiceRoot agent="navigator"><JourneyScreen tourId={tourId} session={session} setSession={setSession}/></VoiceRoot>;
}

function JourneyScreen({ tourId, session, setSession }: { tourId: string; session: Session | null; setSession: (session: Session) => void }) {
  const displayRef = useRef<(display: Display | null) => void>(() => undefined);
  const voice = useVoiceSession(session?.session_id ?? null, display => displayRef.current(display as Display));
  const [highlight, setHighlight] = useState<string[]>([]);
  const latestTour = useLatest();
  const latestAction = useLatest();
  const [tour, setTourState] = useState<Tour | null>(null);
  const tourRef = useRef<Tour | null>(null);
  const [model, setModel] = useState<Model | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(() => storage.get(`tyb.confirmed.${tourId}`) === '1');
  const [step, setStepState] = useState(0);
  const [floorId, setFloorId] = useState('');
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [sheet, setSheet] = useState<'steps' | 'chat' | null>(null);
  const [picker, setPicker] = useState(false);
  const [scanner, setScanner] = useState(false);
  const stepsRef = useRef<HTMLDialogElement>(null);
  /** a building change waiting for its replanned tour; whichever request delivers it shows the notice */
  const change = useRef<{ summary: string; before: Tour; at: number } | null>(null);
  const voiceRef = useRef(voice);
  const modelRef = useRef<Model | null>(null);
  voiceRef.current = voice;

  /**
   * Only a newer (or equal, refreshed) revision may replace the tour on screen. The step resets when the
   * route changed (new target or new revision); a refresh for the same leg (voice "next") keeps it.
   */
  const applyTour = useCallback((next: Tour, refresh = false) => {
    const current = tourRef.current;
    if (current && current.tour_id === next.tour_id && next.revision < current.revision) return false;
    const sameTarget = !!current && currentLeg(current)?.to_space_id === currentLeg(next)?.to_space_id;
    const reset = !current || !sameTarget || (!refresh && current.revision !== next.revision);
    tourRef.current = next;
    setTourState(next);
    if (reset) setStep(0, next);
    const pending = change.current;
    if (pending && next.revision > pending.before.revision) {
      change.current = null;
      const result = rerouteNotice(pending.summary, pending.before, next, modelRef.current ?? undefined);
      setNotice({ text: result.text, blocked: result.blocked, tone: 'change' });
      voiceRef.current.sendContext(context.replanned(pending.summary, next, modelRef.current ?? undefined));
      console.info(`[timing] building change → new route on phone: ${Math.round(performance.now() - pending.at)} ms after the event arrived (revision ${next.revision})`);
    }
    const index = (next as { navigation_index?: number }).navigation_index;
    if (!reset && refresh && typeof index === 'number') setStepState(step => Math.max(step, index - 1));
    return true;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setStep = (value: number, forTour = tourRef.current) => {
    const leg = forTour ? currentLeg(forTour) : null;
    const next = clampStep(leg, value);
    setStepState(next);
    if (forTour) storage.set(`tyb.step.${forTour.tour_id}`, `${forTour.revision}:${next}`);
    const maneuver = leg?.maneuvers[next];
    if (maneuver) setFloorId(maneuver.floor_id);
  };

  // load tour → building → phone session (CONTRACTS §10)
  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        const loaded = await api.tour(tourId);
        const snapshot = await api.building(loaded.building_id);
        if (!live) return;
        const nextModel = buildModel(snapshot);
        setModel(nextModel);
        tourRef.current = loaded; setTourState(loaded);
        const saved = storage.get(`tyb.step.${tourId}`)?.split(':');
        const savedStep = saved && Number(saved[0]) === loaded.revision ? Number(saved[1]) : 0;
        const leg = currentLeg(loaded);
        setStepState(clampStep(leg, savedStep));
        setFloorId(leg?.maneuvers[clampStep(leg, savedStep)]?.floor_id ?? loaded.start.floor_id);
        let phone = await ensureSession(loaded.building_id, 'phone');
        // a tour this phone has not confirmed yet starts at the tour start (tour_start, low confidence; CONTRACTS §10)
        const startHere = storage.get(`tyb.confirmed.${loaded.tour_id}`) !== '1';
        if (phone.active_tour_id !== loaded.tour_id || (startHere && phone.position?.space_id !== loaded.start.space_id)) {
          phone = await api.updateSession(phone.session_id, { active_tour_id: loaded.tour_id, ...(startHere ? { position: { ...loaded.start, source: 'tour_start' as const, confidence: 'low' as const, heading_deg: null, marker_id: null } } : {}) });
        }
        if (live) setSession(phone);
        if (live && snapshot.building_version > loaded.building_version && !tourDone(loaded)) {
          const missed = (await api.events(loaded.building_id).catch(() => [])).filter(event => event.building_version > loaded.building_version);
          change.current = { summary: missed.length === 1 ? missed[0]!.summary : 'The building changed since this tour was planned', before: loaded, at: performance.now() };
          // before this phone confirmed a position for this tour, its session may still hold another tour's position
          const confirmedHere = storage.get(`tyb.confirmed.${loaded.tour_id}`) === '1';
          const from: Position = (confirmedHere && phone.position) || { ...loaded.start, source: 'tour_start', confidence: 'low' };
          const after = await api.replan(loaded.tour_id, { session_id: phone.session_id, from, reason: 'building changed before the tour was opened' });
          if (live) applyTour(after);
        }
      } catch (reason) {
        if (live) setError(reason instanceof ApiError && reason.status === 404 ? 'This tour does not exist any more. Plan it again on the desk.' : message(reason));
      }
    })();
    return () => { live = false; };
  }, [tourId, setSession]);

  modelRef.current = model;
  const leg = tour ? currentLeg(tour) : null;
  const legIndex = tour ? currentLegIndex(tour) : -1;
  const shown = clampStep(leg, step);
  const maneuver = leg?.maneuvers[shown] ?? null;
  const next = tour ? currentTarget(tour, model ?? undefined) : null;
  const done = !!tour && tourDone(tour);
  const finalLeg = !!tour && finalDestinationPending(tour);
  const blocked = tour ? blockedReason(tour) : null;

  /** Where the person is now: the shown step's point once they have started walking, else the session position. */
  const here = useCallback((): Position | null => {
    if (model && maneuver && shown > 0) { const position = stepPosition(model, maneuver); if (position) return position; }
    const start: Position | null = tour ? { ...tour.start, source: 'tour_start', confidence: 'low' } : null;
    return (confirmed && session?.position) || start;
  }, [model, maneuver, shown, session, tour, confirmed]);

  const replan = useCallback(async (from: Position, reason: string) => {
    if (!session || !tourRef.current) return;
    const tourId = tourRef.current.tour_id;
    await latestAction(() => api.replan(tourId, { session_id: session.session_id, from, reason }), after => { applyTour(after); },
      failure => setNotice({ text: `Could not update the route: ${message(failure)}`, blocked: false, tone: 'info' }));
  }, [session, latestAction, applyTour]);

  const onSocket = useCallback((event: ServerMessage) => {
    const current = tourRef.current;
    if ((event.type === 'building_changed' || event.type === 'building_reset') && model && event.building_version !== model.snapshot.building_version) {
      void api.building(event.building_id).then(snapshot => setModel(buildModel(snapshot)));
      const from = here();
      const summary = event.type === 'building_changed' ? event.event.summary : 'The building was reset';
      if (from && current && !done) { change.current = { summary, before: current, at: performance.now() }; void replan(from, summary); }
    }
    if (event.type === 'tour_updated' && current && event.tour_id === current.tour_id && event.revision > current.revision) void latestTour(() => api.tour(current.tour_id), loaded => applyTour(loaded, true));
  }, [model, here, replan, done, latestTour, applyTour]);
  /** After a reconnect (U11): reload the snapshot; if the building changed while offline, replan from here. */
  const onReconnect = useCallback(async () => {
    const current = tourRef.current;
    if (!current) return;
    try {
      const snapshot = await api.building(current.building_id);
      const known = Math.min(modelRef.current?.snapshot.building_version ?? snapshot.building_version, current.building_version);
      setModel(buildModel(snapshot));
      const from = here();
      if (snapshot.building_version > known && from && !done) {
        const missed = (await api.events(current.building_id).catch(() => [])).filter(event => event.building_version > known);
        const summary = missed.length === 1 ? missed[0]!.summary : missed.length ? `${missed.length} changes while you were offline` : 'The building changed while you were offline';
        change.current = { summary, before: current, at: performance.now() };
        await replan(from, summary);
      } else await latestTour(() => api.tour(current.tour_id), loaded => applyTour(loaded, true));
    } catch { /* the next reconnect tries again */ }
  }, [here, done, replan, latestTour, applyTour]);
  const link = useBuildingSocket(tour?.building_id ?? null, onSocket, () => void onReconnect());

  // voice context when the tour loads
  useEffect(() => { if (tour && voice.status === 'connected') voice.sendContext(context.tourLoaded(tour, model ?? undefined)); }, [voice.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const confirmAt = async (position: Position, from?: Marker) => {
    if (!session || !model || !tour) return;
    setBusy(true);
    try {
      const updated = await api.updateSession(session.session_id, { position });
      setSession(updated);
      setConfirmed(true); storage.set(`tyb.confirmed.${tourId}`, '1');
      voice.sendContext(context.position(model, position));
      if (position.space_id !== tour.start.space_id || from) await replan(position, from ? `marker ${from.marker_id}` : 'position confirmed');
    } catch (reason) { setNotice({ text: `Could not save your position: ${message(reason)}`, blocked: false, tone: 'info' }); }
    setBusy(false);
  };
  const confirmStart = () => tour && model && void confirmAt({ space_id: tour.start.space_id, floor_id: tour.start.floor_id, point: tour.start.point, source: 'manual', confidence: 'medium', heading_deg: null, marker_id: null });
  const chooseRoom = (spaceId: string) => { setPicker(false); if (model) void confirmAt({ space_id: spaceId, floor_id: model.space.get(spaceId)?.floor_id, point: anchorOf(model, spaceId), source: 'manual', confidence: 'medium', heading_deg: null, marker_id: null }); };
  const onMarker = useCallback(async (markerId: string) => {
    setScanner(false);
    try {
      const marker = await api.marker(markerId);
      if (marker.building_id !== tourRef.current?.building_id) { setNotice({ text: 'That position code belongs to another building.', blocked: false, tone: 'info' }); return; }
      await confirmAt({ space_id: marker.space_id, floor_id: marker.floor_id, point: marker.point, heading_deg: marker.heading_deg, source: 'marker', marker_id: marker.marker_id, confidence: 'high' }, marker);
    } catch (reason) { setNotice({ text: `Unknown position code: ${message(reason)}`, blocked: false, tone: 'info' }); }
  }, [session, model, tour]); // eslint-disable-line react-hooks/exhaustive-deps

  const gotIt = async () => {
    if (!tour || !next || !session) return;
    setBusy(true);
    await latestAction(() => api.progress(tour.tour_id, next.stop_id, 'collected', session.session_id), updated => {
      applyTour(updated);
      setNotice(null);
      voice.sendContext(next.stop_id === 'end' ? `Final destination reached: ${next.label}. Tour complete.` : context.collected(next.label, updated));
      void api.session(session.session_id).then(setSession, () => undefined);
    }, failure => setNotice({ text: `Could not mark it collected: ${message(failure)}`, blocked: false, tone: 'info' }));
    setBusy(false);
  };

  /** Explicit "route with stairs" for step-free profiles (UX J6b): never applied silently. */
  const withStairs = async () => {
    if (!session || !tourRef.current) return;
    setBusy(true);
    try {
      const updated = await api.updateSession(session.session_id, { profile: 'walk', constraints: { ...session.constraints, step_free: false } });
      setSession(updated);
      if (updated.profile !== 'walk' || updated.constraints?.step_free) throw new Error('this phone still asks for step-free routes');
      const from = here();
      const before = tourRef.current;
      if (from) {
        const after = await api.replan(before.tour_id, { session_id: session.session_id, from, reason: 'route with stairs requested', constraints: { step_free: false } });
        if (after.constraints.step_free) throw new Error('the route still requires step-free access');
        change.current = { summary: 'Route with stairs', before, at: performance.now() }; applyTour(after);
      }
    } catch (reason) { setNotice({ text: `Could not plan a route with stairs: ${message(reason)}`, blocked: false, tone: 'info' }); }
    setBusy(false);
  };

  /** Tool displays from voice and text chat: a new tour opens, instructions refresh the step, found places light up. */
  const onDisplay = useCallback((display: Display | null) => {
    if (!display) return;
    if (display.kind === 'tour' && display.tour_id && display.tour_id !== tourRef.current?.tour_id) { storage.set(`tyb.confirmed.${display.tour_id}`, '1'); navigate(`/go/${display.tour_id}`); return; }
    if (display.kind === 'instruction' || display.kind === 'tour' || display.kind === 'route') void latestTour(() => api.tour(tourId), loaded => applyTour(loaded, true));
    const current = modelRef.current;
    const space = display.space_id ?? display.space_ids?.[0] ?? (display.asset_ids?.[0] ? current?.asset.get(display.asset_ids[0])?.space_id : undefined);
    if (current && space && current.space.has(space)) {
      setHighlight([space]); setFloorId(current.space.get(space)!.floor_id);
      setTimeout(() => setHighlight(ids => (ids[0] === space ? [] : ids)), 8000);
    }
  }, [latestTour, applyTour, tourId]);
  displayRef.current = onDisplay;

  useEffect(() => {
    const dialog = stepsRef.current;
    if (!dialog) return;
    if (sheet === 'steps' && !dialog.open) dialog.showModal();
    if (sheet !== 'steps' && dialog.open) dialog.close();
  }, [sheet]);

  const you = useMemo(() => {
    if (!model) return null;
    if (maneuver && shown > 0) return { space_id: '', floor_id: maneuver.floor_id, point: maneuver.at };
    return placeOf(model, (confirmed && session?.position) || tour?.start);
  }, [model, maneuver, shown, session, tour, confirmed]);

  if (error) return <main className="desk-message"><div className="surface notice"><h1>Tour not available</h1><p>{error}</p></div></main>;
  if (!tour || !model) return <main className="desk-message"><p className="loading"><LoaderCircle className="spin" size={20}/>Opening your tour…</p></main>;

  const total = tour.stops.length;
  const collected = collectedCount(tour);
  const startLabel = `${spaceName(model, tour.start.space_id)}`;
  const provisional = isProvisional(tour);
  const arrived = atStop(leg, shown);
  const routeTargets: TourStop[] = [...pendingStops(tour)];
  if (tour.end && !done) routeTargets.push({ stop_id: 'end', space_id: tour.end.space_id, asset_ids: [], status: 'pending', label: destinationLabel(tour, model) });
  const unavailable = tour.unreachable_stops.map(item => stopLabel(tour, item.stop_id, model).split(' · ')[0]).join(', ');

  return <main className="journey">
    <MapView model={model} floorId={floorId || tour.start.floor_id} onFloor={setFloorId} tour={done ? null : tour} focusLeg={legIndex >= 0 ? legIndex : undefined} you={you} showParts={false}
      highlightSpaceIds={highlight} frame={highlight.length ? 'space' : 'route'} frameSpaceIds={highlight} frameKey={highlight.length ? `find:${highlight[0]}` : `leg:${tour.revision}:${legIndex}:${floorId}`}/>

    <div className="journey-top">
      {!done && confirmed && leg && maneuver && <button className="route-banner surface" onClick={() => setSheet('steps')} aria-label={`Current step: ${cleanText(maneuver.text)}. Open all steps`}>
        <span className="turn-icon"><ManeuverIcon kind={maneuver.kind}/></span>
        <span className="route-copy"><span className="route-instruction">{cleanText(maneuver.text)}</span><span className="route-destination">{next?.label.split(' · ')[0]} <span>· {next ? floorName(model, model.space.get(next.space_id)?.floor_id ?? '') : ''}</span></span></span>
        {!arrived && metresToNext(leg, shown) > 0 && <span className="route-distance">{metresToNext(leg, shown)}<span>metres</span></span>}
      </button>}
      {notice && <div className={`journey-notice surface ${notice.tone}`} role="alert">
        <TriangleAlert size={20} aria-hidden="true"/>
        <div><p>{notice.text}</p>{notice.blocked && tour.constraints.step_free && <button className="secondary-button" disabled={busy} onClick={() => void withStairs()}>Show the route with stairs</button>}</div>
        <button className="icon-button" onClick={() => setNotice(null)} aria-label="Dismiss"><X size={18}/></button>
      </div>}
      {(blocked || tour.unreachable_stops.length > 0) && !notice && !done && <div className="journey-notice surface change" role="status"><TriangleAlert size={20} aria-hidden="true"/><div>
        <p>{blocked ? `${finalLeg ? `The final destination (${destinationLabel(tour, model)})` : unavailable || 'The next stop'} cannot be reached${blocked.reason === 'no_step_free_path' || tour.constraints.step_free ? ' step-free' : ''} right now.` : `${unavailable} cannot be reached${tour.constraints.step_free ? ' step-free' : ''} right now.`}</p>
        {tour.constraints.step_free && <button className="secondary-button" disabled={busy} onClick={() => void withStairs()}>Show the route with stairs</button>}
      </div></div>}
      {link === 'offline' && <p className="journey-offline surface" role="status"><WifiOff size={15}/>Offline · reconnecting</p>}
      {(mockMode || provisional) && <div className="journey-badges">{mockMode ? <DemoBadge reason="Mock mode"/> : <DemoBadge label="Provisional route" reason="Route lines are straight provisional segments"/>}</div>}
    </div>

    <section className="journey-dock" aria-label="Guidance">
      {done
        ? <div className="done-card surface">
          <span className="avatar-wrap"><Blobatar name="alain00" animate="always" size={116} expression={happy} title="Alain, your building guide"/></span>
          <h1>{total === 1 ? 'Your part is collected' : `All ${total} parts collected`}</h1>
          {tour.end && <p>Final destination reached: {destinationLabel(tour, model)}.</p>}
          <ul>{tour.stops.map(stop => <li key={stop.stop_id}><Check size={16}/>{stop.label}</li>)}</ul>
        </div>
        : !confirmed
          ? <div className="confirm-card surface" role="dialog" aria-labelledby="confirm-title">
            <p className="policy">{total} stops · {Math.round(tour.length_m)} m</p>
            <h1 id="confirm-title">Are you at {startLabel}?</h1>
            <p className="muted">{floorName(model, tour.start.floor_id)}. The tour starts here.</p>
            <button className="primary-button" disabled={busy || !session} onClick={confirmStart}><Check size={18}/>Yes, I am here</button>
            <div className="confirm-alt">
              <button className="secondary-button" disabled={busy || !session} onClick={() => setScanner(true)}><ScanQrCode size={18}/>Scan a position code</button>
              <button className="secondary-button" disabled={busy || !session} onClick={() => setPicker(true)}><MapPin size={18}/>Choose my room</button>
            </div>
          </div>
          : <>
            <div className="agent-line">
              <button className="agent-presence" onClick={() => setSheet('chat')} aria-label="Ask the building">
                <span className="avatar-wrap small"><Blobatar name="alain00" animate="always" size={72} expression={arrived ? happy : idle} title="Alain, your building guide"/></span>
                <span className="agent-bubble surface"><strong>{!next || !leg ? 'No route right now' : arrived ? `Here: ${next.label.split(' · ')[0]}` : finalLeg ? `Final destination: ${next.label}` : `Stop ${collected + 1} of ${total}`}</strong><span>{voice.status === 'connected' ? (voice.isSpeaking ? 'Speaking…' : 'Listening') : 'Tap to ask'}</span></span>
              </button>
              {voice.available && <button className={`icon-button voice-toggle ${voice.status === 'connected' ? 'on' : ''}`} onClick={() => void (voice.status === 'connected' ? voice.stop() : voice.start().catch(() => setSheet('chat')))} aria-label={voice.status === 'connected' ? 'Stop voice guidance' : 'Start voice guidance'}>{voice.status === 'connected' ? <Mic size={20}/> : <MicOff size={20}/>}</button>}
            </div>
            <div className="progress-dots" aria-label={`${collected} of ${total} parts collected${tour.end ? '; final destination remains' : ''}`}>{displayOrder(tour).filter(id => id !== 'end').map(id => <span key={id} className={tour.stops.find(stop => stop.stop_id === id)?.status === 'collected' ? 'done' : id === next?.stop_id ? 'now' : tour.unreachable_stops.some(item => item.stop_id === id) ? 'blocked' : ''}/>)}{tour.end && <span aria-label="Final destination" className={tour.unreachable_stops.some(item => item.stop_id === 'end') ? 'blocked' : finalLeg ? 'now' : ''}/>}</div>
            <div className="dock-actions">
              <button className="icon-button" onClick={() => setSheet('steps')} aria-label="All steps"><ListOrdered size={20}/></button>
              {shown > 0 && !arrived && <button className="icon-button" onClick={() => setStep(shown - 1)} aria-label="Previous step"><ArrowLeft size={20}/></button>}
              {(!next || !leg) && tour.unreachable_stops.length > 0
                ? <button className="primary-button" onClick={() => setSheet('chat')}>Ask the building</button>
                : arrived || !leg
                ? <button className="primary-button got-it" disabled={busy || !next || !leg} onClick={() => void gotIt()}>{busy ? <LoaderCircle className="spin" size={18}/> : <Check size={20}/>} {finalLeg ? 'I have arrived' : `Got it${next ? `: ${next.label.split(' · ')[0]}` : ''}`}</button>
                : <button className="primary-button" onClick={() => setStep(shown + 1)}>Next step<ArrowRight size={18}/></button>}
            </div>
            {!next && tour.unreachable_stops.length > 0 && tour.constraints.step_free && <button className="link-button" disabled={busy} onClick={() => void withStairs()}>Show the route with stairs</button>}
            {!arrived && leg && !finalLeg && <button className="link-button" disabled={busy || !next} onClick={() => void gotIt()}>Already have it? Mark {next?.label.split(' · ')[0]} collected</button>}
          </>}
    </section>

    <dialog ref={stepsRef} className="sheet route-sheet" aria-labelledby="steps-title" onClose={() => setSheet(null)} onCancel={() => setSheet(null)}>
      <div className="sheet-handle"/>
      <header className="sheet-header"><div><h2 id="steps-title">Your route</h2><p>{collected} of {total} collected · {Math.round(tour.legs.reduce((sum, item) => sum + (item.reachable ? item.length_m : 0), 0))} m to go</p></div><button className="icon-button" onClick={() => setSheet(null)} aria-label="Close steps"><X size={22}/></button></header>
      <div className="route-steps">
        {routeTargets.map(stop => {
          const currentTarget = stop.stop_id === next?.stop_id;
          const candidate = stop.stop_id === 'end' ? tour.legs[tour.legs.length - 1] : tour.legs.find(item => item.to_space_id === stop.space_id);
          const stopLeg = tour.unreachable_stops.some(item => item.stop_id === stop.stop_id) || candidate?.to_space_id !== stop.space_id ? undefined : candidate;
          return <section key={stop.stop_id}>
            <h3>{currentTarget ? 'Now: ' : ''}{stop.stop_id === 'end' ? 'Final destination: ' : ''}{stop.label}</h3>
            {stopLeg?.reachable ? <ol>{stopLeg.maneuvers.map((item, index) => {
              const current = currentTarget && index === shown;
              return <li key={item.i} className={current ? 'current' : ''}>
                <span className="step-symbol">{currentTarget && index < shown ? <Check size={16}/> : <ManeuverIcon kind={item.kind} size={16}/>}</span>
                <span>{currentTarget ? <button className="step-jump" onClick={() => { setStep(index); setSheet(null); }}>{cleanText(item.text)}</button> : <strong>{cleanText(item.text)}</strong>}<span>{floorName(model, item.floor_id)}</span></span>
                {item.distance_m > 0 && <span className="step-meters">{Math.round(item.distance_m)} m</span>}
              </li>;
            })}</ol> : <p className="plan-error">No route to this stop right now.</p>}
          </section>;
        })}
      </div>
      {tour.unreachable_stops.length > 0 && <section><h3>Cannot be reached right now</h3><ul className="blocked-list">{tour.unreachable_stops.map(item => <li key={item.stop_id}>{stopLabel(tour, item.stop_id, model)} · {item.reason.replaceAll('_', ' ')}</li>)}</ul></section>}
      <p className="demo-explanation">Your position follows the steps you confirm and the position codes you scan. There is no automatic location tracking.</p>
    </dialog>

    <ChatSheet open={sheet === 'chat'} sessionId={session?.session_id ?? null} onClose={() => setSheet(null)} onDisplay={onDisplay} voiceError={voice.error}/>
    <StartPicker model={model} open={picker} current={session?.position?.space_id ?? null} onPick={chooseRoom} onClose={() => setPicker(false)}/>
    {scanner && <Suspense fallback={null}><Scanner open={scanner} onMarker={onMarker} onClose={() => setScanner(false)}/></Suspense>}
  </main>;
}

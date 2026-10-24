import { ArrowUp, Building2, LoaderCircle, MapPin, Route } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, api, ensureSession, mockMode } from '../api/client';
import { useLatest } from '../api/latest';
import type { Candidate, ChatReply, Display, ServerMessage, Session, Tour } from '../api/types';
import { useBuildingSocket } from '../api/ws';
import { MapView } from '../map/MapView';
import { anchorOf, assetPlace, buildModel, floorName, spaceName } from '../map/model';
import type { Model } from '../map/model';
import { navigate, useLocation } from '../router';
import { DemoBadge } from '../ui/DemoBadge';
import { scenario } from '../demo/scenario';
import { HandoffDialog } from './HandoffDialog';
import { PartsList } from './PartsList';
import { StartPicker } from './StartPicker';
import { TourPanel } from './TourPanel';

type Agent = { text: string; candidates: Candidate[]; tone: 'info' | 'error' } | null;

const message = (error: unknown) => error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong.';

/** Default start: the scenario start in demo mode, else a room by a ground-floor entrance, a lobby or a corridor. */
function defaultStart(model: Model, demo: boolean): string {
  if (demo && model.space.has(scenario.start.space_id)) return scenario.start.space_id;
  const ground = model.floors.find(floor => floor.level === 0) ?? model.floors[0];
  const spaces = model.spacesOn.get(ground?.id ?? '') ?? [];
  const entrance = (model.openingsOn.get(ground?.id ?? '') ?? []).find(opening => opening.kind === 'entrance')?.space_ids.find(id => model.space.has(id));
  return entrance ?? (spaces.find(space => space.room_type === 'lobby') ?? spaces.find(space => space.type === 'corridor') ?? spaces[0])?.id ?? '';
}

export function Desk() {
  const { query } = useLocation();
  const demo = query.get('demo') === 'hero';
  const buildingId = query.get('building') ?? scenario.building_id;
  const latest = useLatest();
  const latestTour = useLatest();
  const [model, setModel] = useState<Model | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [floorId, setFloorId] = useState('');
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [focusId, setFocusId] = useState<string | null>(null);
  const [frameSpaces, setFrameSpaces] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [keepOrder, setKeepOrder] = useState(false);
  const [tour, setTour] = useState<Tour | null>(null);
  const [plannedMs, setPlannedMs] = useState<number | null>(null);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [ask, setAsk] = useState('');
  const [asking, setAsking] = useState(false);
  const [agent, setAgent] = useState<Agent>(null);
  const [picker, setPicker] = useState(false);
  const [handoff, setHandoff] = useState(false);
  const [openedOnPhone, setOpenedOnPhone] = useState(false);
  const askRef = useRef<HTMLInputElement>(null);

  const loadBuilding = useCallback(() => latest(() => api.building(buildingId), snapshot => {
    const next = buildModel(snapshot);
    setModel(current => (current && current.snapshot.content_hash === snapshot.content_hash && current.snapshot.building_version === snapshot.building_version ? current : next));
    setFloorId(current => current && next.floor.has(current) ? current : (next.floors.find(floor => floor.level === 0) ?? next.floors[0])?.id ?? '');
    setLoadError(null);
  }, error => setLoadError(message(error))), [buildingId, latest]);

  useEffect(() => { void loadBuilding(); }, [loadBuilding]);

  // desk session with a start position (CONTRACTS §10)
  useEffect(() => {
    if (!model || session?.building_id === buildingId) return;
    let live = true;
    void (async () => {
      try {
        let next = await ensureSession(buildingId, 'desk');
        if (!next.position) {
          const start = defaultStart(model, demo);
          if (start) next = await api.updateSession(next.session_id, { position: { space_id: start, floor_id: model.space.get(start)?.floor_id, point: anchorOf(model, start), source: 'desk', confidence: 'medium', heading_deg: null, marker_id: null } });
        }
        if (live) { setSession(next); if (next.position) setFloorId(next.position.floor_id); }
      } catch (error) {
        if (live) setAgent({ text: `Could not start a desk session: ${message(error)}`, candidates: [], tone: 'error' });
      }
    })();
    return () => { live = false; };
  }, [model, buildingId, demo, session?.building_id]);

  useEffect(() => {
    if (demo && model) setSelected(new Set(scenario.items.filter(id => model.asset.has(id))));
  }, [demo, model?.snapshot.content_hash]); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshTour = useCallback((id: string) => latestTour(() => api.tour(id), setTour), [latestTour]);
  const onSocket = useCallback((event: ServerMessage) => {
    if (event.type === 'building_changed' || event.type === 'building_reset') {
      if (!model || event.building_version !== model.snapshot.building_version) void loadBuilding();
      if (tour) void refreshTour(tour.tour_id);
    }
    if (event.type === 'tour_updated' && tour && event.tour_id === tour.tour_id && event.revision > tour.revision) void refreshTour(tour.tour_id);
    if (event.type === 'tour_opened' && tour && event.tour_id === tour.tour_id && event.device === 'phone') setOpenedOnPhone(true);
  }, [model, tour, loadBuilding, refreshTour]);
  const link = useBuildingSocket(model ? buildingId : null, onSocket, () => { void loadBuilding(); if (tour) void refreshTour(tour.tour_id); });

  const focusAsset = (id: string) => {
    const asset = model?.asset.get(id);
    if (!asset) return;
    setFocusId(id);
    setFrameSpaces([asset.space_id]);
    setFloorId(asset.floor_id);
  };
  const toggle = (id: string) => setSelected(current => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const plan = async () => {
    if (!session || !selected.size) return;
    setPlanning(true); setPlanError(null);
    const started = performance.now();
    await latestTour(() => api.planTour({ session_id: session.session_id, items: [...selected], keep_order: keepOrder }), next => {
      setPlannedMs(performance.now() - started);
      setTour(next); setOpenedOnPhone(false); setFocusId(null); setFrameSpaces([]);
      setFloorId(next.start.floor_id);
      console.info(`[timing] plan → route visible: ${Math.round(performance.now() - started)} ms (tour ${next.tour_id})`);
    }, error => setPlanError(message(error)));
    setPlanning(false);
  };

  const applyDisplay = (display: Display | null | undefined) => {
    if (!display || !model) return;
    if (display.kind === 'tour' && display.tour_id) {
      const started = performance.now();
      void latestTour(() => api.tour(display.tour_id!), next => { setTour(next); setFocusId(null); setFrameSpaces([]); setPlannedMs(performance.now() - started); setFloorId(next.start.floor_id); setSelected(new Set(next.stops.flatMap(stop => stop.asset_ids))); });
      return;
    }
    const assets = (display.asset_ids ?? []).filter(id => model.asset.has(id));
    const first = assets[0];
    if (first) { focusAsset(first); setSelected(current => new Set([...current, ...assets])); }
    else if (display.space_id && model.space.has(display.space_id)) { setFrameSpaces([display.space_id]); setFloorId(model.space.get(display.space_id)!.floor_id); }
  };

  const sendAsk = async (text: string) => {
    if (!session || !text.trim()) return;
    setAsking(true);
    await latest(() => api.chat(session.session_id, text.trim()), (reply: ChatReply) => {
      const failed = reply.tool_calls.find(call => !call.ok && call.error?.candidates?.length);
      setAgent({ text: reply.reply, candidates: failed?.error?.candidates?.slice(0, 4) ?? [], tone: 'info' });
      applyDisplay(reply.display ?? reply.tool_calls.find(call => call.ok && call.display)?.display);
      setAsk('');
    }, error => setAgent({ text: error instanceof ApiError && (error.status === 404 || error.status === 501 || error.status === 503) ? 'Text chat is not connected yet. Pick parts from the list instead.' : message(error), candidates: [], tone: 'error' }));
    setAsking(false);
  };
  const submitAsk = (event: FormEvent) => { event.preventDefault(); void sendAsk(ask); };

  const pickStart = async (spaceId: string) => {
    if (!session || !model) return;
    setPicker(false);
    try {
      setSession(await api.updateSession(session.session_id, { position: { space_id: spaceId, floor_id: model.space.get(spaceId)?.floor_id, point: anchorOf(model, spaceId), source: 'desk', confidence: 'medium', heading_deg: null, marker_id: null } }));
      setTour(null);
    } catch (error) { setAgent({ text: `Could not change the start: ${message(error)}`, candidates: [], tone: 'error' }); }
  };

  const you = tour?.start ?? session?.position ?? null;
  const highlight = useMemo(() => (focusId && model?.asset.get(focusId) ? [model.asset.get(focusId)!.space_id] : frameSpaces), [focusId, model, frameSpaces]);
  const focus = focusId ? model?.asset.get(focusId) : null;
  const provisional = (tour as { _fixture?: { geometry?: string } } | null)?._fixture?.geometry === 'provisional';

  if (loadError) return <main className="desk desk-message"><div className="surface notice"><h1>The building did not load</h1><p>{loadError}</p><div className="row"><button className="primary-button" onClick={() => void loadBuilding()}>Try again</button><button className="secondary-button" onClick={() => navigate('/')}>Choose a building</button></div></div></main>;
  if (!model) return <main className="desk desk-message"><p className="loading"><LoaderCircle className="spin" size={20}/>Loading the building…</p></main>;

  return <main className="desk">
    <aside className="desk-panel surface" aria-label="Plan a collection tour">
      <header className="desk-brand">
        <button className="brand-mark" onClick={() => navigate('/')} aria-label="Choose another building"><Building2 size={18}/></button>
        <div><p className="product">Talk to Your Building</p><h1>{model.snapshot.building.building.name}</h1></div>
        {(mockMode || provisional) && <DemoBadge reason={mockMode ? 'Mock mode: bundled kit data, not the live API' : 'Provisional route geometry'}/>}
      </header>

      <form className="ask" onSubmit={submitAsk}>
        <label htmlFor="ask-input">What do you need?</label>
        <div className="ask-field">
          <input ref={askRef} id="ask-input" value={ask} onChange={event => setAsk(event.target.value)} placeholder="“Where is the 3D printer?”" autoComplete="off" maxLength={500}/>
          <div className="voice-slot" id="desk-voice-slot"/>
          <button className="icon-button dark" type="submit" disabled={!ask.trim() || asking || !session} aria-label="Ask">{asking ? <LoaderCircle className="spin" size={18}/> : <ArrowUp size={19}/>}</button>
        </div>
      </form>
      {agent && <div className={`agent-reply ${agent.tone}`} role="status" aria-live="polite">
        <p>{agent.text}</p>
        {agent.candidates.length > 0 && <div className="chips">{agent.candidates.map(candidate => <button key={candidate.id} onClick={() => { if (model.asset.has(candidate.id)) focusAsset(candidate.id); void sendAsk(candidate.name); }}>{candidate.name}{candidate.floor_id ? <span> · {floorName(model, candidate.floor_id)}</span> : null}</button>)}</div>}
      </div>}

      <button className="start-chip" onClick={() => setPicker(true)} disabled={!session}>
        <MapPin size={17} aria-hidden="true"/>
        <span>{you ? <>You are at <strong>{spaceName(model, you.space_id)}</strong> · {floorName(model, you.floor_id)}</> : 'Where are you now?'}</span>
        <span className="link">Change</span>
      </button>

      {tour
        ? <TourPanel model={model} tour={tour} plannedMs={plannedMs} onHandoff={() => setHandoff(true)} onEdit={() => setTour(null)} onFocusStop={(spaceId, floor) => { setFocusId(null); setFrameSpaces([spaceId]); setFloorId(floor); }}/>
        : <>
          <PartsList model={model} query={search} onQuery={setSearch} selected={selected} onToggle={toggle} focusId={focusId} onFocus={focusAsset}/>
          <footer className="plan-bar">
            {planError && <p className="plan-error" role="alert">{planError}</p>}
            <label className="toggle"><input type="checkbox" checked={keepOrder} onChange={event => setKeepOrder(event.target.checked)}/><span>Keep my order</span></label>
            <button className="primary-button" onClick={() => void plan()} disabled={!selected.size || planning || !session}>
              {planning ? <LoaderCircle className="spin" size={18}/> : <Route size={18}/>}
              {selected.size ? `Plan collection tour · ${selected.size} ${selected.size === 1 ? 'part' : 'parts'}` : 'Select parts to plan a tour'}
            </button>
          </footer>
        </>}
    </aside>

    <section className="desk-map" aria-label="Building map">
      <MapView model={model} floorId={floorId} onFloor={setFloorId} tour={tour} selected={selected} focusAssetId={focusId} highlightSpaceIds={highlight} you={you}
        onAsset={id => { toggle(id); focusAsset(id); }} onSpace={picker ? id => void pickStart(id) : undefined}
        frame={tour && !frameSpaces.length && !focusId ? 'route' : highlight.length ? 'space' : tour ? 'route' : 'all'} frameSpaceIds={highlight}
        frameKey={tour && !frameSpaces.length && !focusId ? `tour:${tour.tour_id}:${tour.revision}` : focusId ? `focus:${focusId}` : highlight.join(',') || 'all'}/>
      {focus && !tour && <div className="focus-card surface" role="status">
        <div><strong>{focus.name}</strong><span>{assetPlace(model, focus)}</span></div>
        <button className={selected.has(focus.id) ? 'secondary-button' : 'primary-button'} onClick={() => toggle(focus.id)}>{selected.has(focus.id) ? 'Remove' : 'Add to tour'}</button>
      </div>}
      {link === 'offline' && <p className="link-status surface" role="status">Reconnecting to live updates…</p>}
    </section>

    <StartPicker model={model} open={picker} current={you?.space_id ?? null} onPick={id => void pickStart(id)} onClose={() => setPicker(false)}/>
    <HandoffDialog tour={tour} open={handoff} opened={openedOnPhone} onClose={() => setHandoff(false)}/>
  </main>;
}

import { ArrowDownUp, ArrowLeft, ArrowUpRight, Box, Building2, Check, ChevronDown, Coffee, Copy, Expand, Layers3, LoaderCircle, LocateFixed, MapPin, Minus, MonitorSmartphone, Pause, Play, Plus, QrCode, Smartphone, Wifi, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ColabModel, ColabPosition, ColabState } from '../api/colab';
import { colabApi, epochMs, positionLabel } from '../api/colab';
import { useLatest } from '../api/latest';
import { buildModel } from '../map/model';
import { linkHandler } from '../router';
import { publicBase, qrPath } from '../desk/HandoffDialog';
import { ColabScene } from './ColabScene';
import { ColabWifiSetup } from './ColabWifiSetup';
import './colab.css';

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return reduced;
}

function useSceneTime(state: ColabState | null, reduced: boolean) {
  const [now, setNow] = useState(Date.now());
  const offset = useRef(0);
  useEffect(() => { if (state) { offset.current = epochMs(state.server_time) - Date.now(); setNow(epochMs(state.server_time)); } }, [state]);
  useEffect(() => {
    if (reduced || !state?.movements.some(move => epochMs(move.started_at) + move.duration_s * 1000 > Date.now() + offset.current)) return;
    let frame = 0;
    let previous = 0;
    const tick = (at: number) => {
      const time = Date.now() + offset.current;
      if (!document.hidden && at - previous > 33) { setNow(time); previous = at; }
      if (!document.hidden && state.movements.some(move => epochMs(move.started_at) + move.duration_s * 1000 > time)) frame = requestAnimationFrame(tick);
    };
    const visibility = () => { cancelAnimationFrame(frame); if (!document.hidden) frame = requestAnimationFrame(tick); };
    visibility();
    document.addEventListener('visibilitychange', visibility);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('visibilitychange', visibility); };
  }, [reduced, state]);
  return now;
}

function shortSource(position: ColabPosition) {
  return position.source === 'wifi_fingerprint' ? 'Wi-Fi estimate' : position.source === 'manual' ? 'Manual' : 'Simulated';
}

export function Colab() {
  const [payload, setPayload] = useState<ColabModel | null>(null);
  const [state, setState] = useState<ColabState | null>(null);
  const [floorId, setFloorId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [feedError, setFeedError] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [focused, setFocused] = useState(true);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [locationOpen, setLocationOpen] = useState(false);
  const [manualRoom, setManualRoom] = useState('');
  const [deviceName, setDeviceName] = useState('My device');
  const shareDialog = useRef<HTMLDialogElement>(null);
  const shareUrl = `${publicBase()}/colab`;
  const qr = useMemo(() => qrPath(shareUrl), [shareUrl]);
  const reduced = useReducedMotion();
  const now = useSceneTime(state, reduced);
  const load = useLatest();
  const loadState = useLatest();
  const acceptState = useCallback((value: ColabState) => {
    setState(previous => !previous || value.sequence > previous.sequence || (value.sequence === previous.sequence && value.server_time >= previous.server_time) ? value : previous);
    setFeedError(false);
  }, []);
  const reload = useCallback(() => {
    setError(null);
    void load(colabApi.model, value => {
      setPayload(value);
      setFloorId(value.building.floors.find(floor => floor.level === 3)?.id ?? value.building.floors.at(-1)?.id ?? '');
    }, reason => setError(reason instanceof Error ? reason.message : 'The building could not be loaded.'));
  }, [load]);
  useEffect(reload, [reload]);
  useEffect(() => {
    if (payload?.model_revision && state?.model_revision && payload.model_revision !== state.model_revision) reload();
  }, [payload?.model_revision, state?.model_revision, reload]);
  useEffect(() => {
    const refresh = () => { void loadState(colabApi.state, acceptState, () => setFeedError(true)); };
    refresh();
    const timer = window.setInterval(refresh, 2500);
    return () => clearInterval(timer);
  }, [loadState, acceptState]);

  const model = useMemo(() => payload ? buildModel({ building: payload.building, building_version: 0, content_hash: 'colab-schematic', closed: [], derived: { anchors: payload.anchors, areas_m2: {} } }) : null, [payload]);
  const activeFloor = model?.floor.get(floorId);
  const roomList = (model?.spacesOn.get(floorId) ?? []).filter(room => !/lift|stair/.test(room.room_type));
  const selected = selectedAsset ? model?.asset.get(selectedAsset) : null;
  const position = state?.positions.find(item => item.device_id === selectedPosition);
  const wifi = state?.positions.filter(item => item.source === 'wifi_fingerprint' && !item.stale) ?? [];
  const hasWalker = state?.walk_running ?? false;
  const floorAssets = model?.snapshot.building.assets.filter(asset => asset.floor_id === floorId) ?? [];
  const movements = state?.movements.filter(move => now >= epochMs(move.started_at) && now < epochMs(move.started_at) + move.duration_s * 1000) ?? [];

  const changeFloor = (id: string) => { setFloorId(id); setManualRoom(''); setSelectedAsset(null); setSelectedPosition(null); setZoom(1); };
  const act = async (operation: () => Promise<unknown>) => {
    setBusy(true); setActionError(null);
    try { await operation(); await loadState(colabApi.state, acceptState, () => setFeedError(true)); }
    catch (reason) { setActionError(reason instanceof Error ? reason.message : 'This action could not be completed.'); }
    finally { setBusy(false); }
  };
  const placeManually = () => {
    const room = model?.space.get(manualRoom || roomList[0]?.id || '');
    if (!room) return;
    const anchor = payload?.anchors[room.id];
    if (!anchor) { setActionError('This room has no verified interior point. Choose another room.'); return; }
    const [x, y] = anchor;
    const existingId = sessionStorage.getItem('colab-device-id') ?? undefined;
    void act(async () => {
      const result = await colabApi.position({ device_id: existingId, label: deviceName.trim() || 'My device', floor_id: floorId, x, y, source: 'manual' });
      sessionStorage.setItem('colab-device-id', result.device_id);
      setSelectedPosition(result.device_id); setSelectedAsset(null);
    });
  };
  const share = async () => {
    try { await navigator.clipboard.writeText(shareUrl); setCopied(true); window.setTimeout(() => setCopied(false), 2200); }
    catch { setActionError('Copy the /colab address from your browser to open this shared view on another device.'); }
  };

  return <main className="colab-page">
    <header className="colab-header">
      <a className="colab-wordmark" href="/" onClick={linkHandler('/')} aria-label="Back to building list"><span className="colab-brand-icon"><Building2 size={21}/></span><span>Talk to your building<span className="colab-wordmark-sub">MUNICH URBAN COLAB</span></span></a>
      <div className="colab-header-actions"><span className={`colab-feed-status${feedError ? ' disconnected' : ''}`}><span/>{feedError ? 'Reconnecting' : state ? 'Shared view' : 'Connecting'}</span><button className="colab-icon-button" onClick={() => shareDialog.current?.showModal()} aria-label="Open shared view on another device"><QrCode size={18}/></button><a className="colab-back" href="/" onClick={linkHandler('/')}><ArrowLeft size={15}/><span>All buildings</span></a></div>
    </header>

    <div className="colab-workspace">
      <aside className="colab-panel">
        <div className="colab-eyebrow"><span/> A BUILDING, UNDERSTOOD</div>
        <h1>A place for<br/>ideas to move.</h1>
        <p className="colab-intro">Explore the Colab, one floor at a time. Find the coffee, the meeting spaces, and each other.</p>

        <section className="colab-floor-card" aria-label="Selected floor">
          <div className="colab-floor-heading"><span className="colab-floor-number">{activeFloor?.level.toString().padStart(2, '0') ?? '—'}</span><div><span className="colab-overline">YOU ARE EXPLORING</span><h2>{activeFloor?.name ?? 'Loading building'}</h2></div><Layers3 size={22}/></div>
          <div className="colab-floor-stats"><span><Box size={14}/>{floorAssets.length} furnishings</span><span><ArrowDownUp size={14}/>Lift & stairs</span></div>
          <div className="colab-floor-provenance">{activeFloor && activeFloor.level >= 3 ? 'Schematic from the supplied floor signage' : 'Illustrative layout · not surveyed'}</div>
        </section>

        <section className="colab-places" aria-labelledby="colab-places-title">
          <div className="colab-section-heading"><h2 id="colab-places-title">Around this floor</h2><span>{floorAssets.length}</span></div>
          <div className="colab-place-list">
            {floorAssets.filter(asset => /coffee|meeting_table|kitchen_table|think_tank|mobile_display|tool_cart/.test(asset.type)).sort((a, b) => {
              const priority = (type: string) => /coffee/.test(type) ? 0 : /mobile_display|kitchen_table/.test(type) ? 1 : /tool_cart/.test(type) ? 2 : 3;
              return priority(a.type) - priority(b.type);
            }).slice(0, 5).map(asset => <button key={asset.id} className={`colab-place${selectedAsset === asset.id ? ' selected' : ''}`} onClick={() => { setSelectedAsset(asset.id); setSelectedPosition(null); }}><span className="colab-place-icon">{/coffee/.test(asset.type) ? <Coffee size={18}/> : <Box size={18}/>}</span><span><strong>{asset.name}</strong><small>{model?.space.get(asset.space_id)?.name}</small></span><ArrowUpRight size={15}/></button>)}
            {!!model && floorAssets.length === 0 && <p className="colab-muted-note">Select another floor to explore its spaces.</p>}
          </div>
        </section>

        <section className="colab-presence" aria-labelledby="colab-presence-title">
          <div className="colab-section-heading"><h2 id="colab-presence-title">People & devices</h2><button onClick={() => setLocationOpen(!locationOpen)} aria-expanded={locationOpen} aria-controls="colab-location-controls"><Plus size={16}/><span>Connect</span></button></div>
          {state?.positions.length ? <ul className="colab-device-list">{state.positions.map(item => <li key={item.device_id}><button className={item.device_id === selectedPosition ? 'selected' : ''} onClick={() => { changeFloor(item.floor_id); setSelectedPosition(item.device_id); }}><span className={`colab-device-dot ${item.source}${item.stale ? ' stale' : ''}`}/><span><strong>{item.label}</strong><small>{positionLabel(item)} · {model?.floor.get(item.floor_id)?.name}</small></span>{item.source === 'wifi_fingerprint' ? <Wifi size={16}/> : <MapPin size={16}/>}</button></li>)}</ul> : <div className="colab-empty-presence"><LocateFixed size={23}/><div><strong>No location fixes yet</strong><p>Connect a collector or place yourself on the map.</p></div></div>}
          <p className="colab-presence-note">{wifi.length ? `${wifi.length} Wi-Fi estimate${wifi.length === 1 ? '' : 's'} · indicative zones, not validated accuracy.` : 'No live Wi-Fi location is being inferred.'}</p>
        </section>

        {locationOpen && <section id="colab-location-controls" className="colab-location-controls">
          <div className="colab-section-heading"><h2>Connect your location</h2><button onClick={() => setLocationOpen(false)} aria-label="Close location controls"><X size={16}/></button></div>
          <details><summary><Wifi size={16}/>Wi-Fi collector<ChevronDown size={15}/></summary><p>Wi-Fi estimates need a paired native collector and calibrated fingerprints. A web browser cannot scan nearby access points. Open this shared view on your iPhone or laptop; an Android collector can send measurements.</p><p>Without calibration there is no Wi-Fi fix. Collector estimates stay visibly separate from manual and simulated positions.</p></details>
          {payload && <ColabWifiSetup model={payload} floorId={floorId}/>}
          <label>Device name<input value={deviceName} onChange={event => setDeviceName(event.target.value)} maxLength={50}/></label>
          <label>Confirm a room on {activeFloor?.name}<select value={manualRoom || roomList[0]?.id || ''} onChange={event => setManualRoom(event.target.value)}>{roomList.map(room => <option key={room.id} value={room.id}>{room.name}</option>)}</select></label>
          <button className="colab-primary" onClick={placeManually} disabled={busy || !roomList.length}><MapPin size={16}/>Place me here <span>Manual</span></button>
        </section>}

        <div className="colab-panel-bottom"><Building2 size={15}/><p>Spatial prototype. Room geometry and furnishings are illustrative, not a surveyed building model.</p></div>
      </aside>

      <section className="colab-stage" aria-label="Interactive building view">
        <div className="colab-stage-top"><div><span className="colab-overline">THE COLAB, IN PERSPECTIVE</span><span className="colab-stage-title">{focused ? 'A closer look at your floor' : 'Every level. One shared place.'}</span></div><span className="colab-schematic-pill">Schematic model</span></div>
        <div className="colab-map-area">
          {error ? <div className="colab-load-message" role="alert"><Building2 size={38}/><h2>The building is not available yet.</h2><p>{error}</p><button className="colab-primary" onClick={reload}>Try again</button></div> : !model ? <div className="colab-load-message"><LoaderCircle className="spin" size={28}/><p>Opening the Colab…</p></div> : <ColabScene model={model} state={state} floorId={floorId} selectedAsset={selectedAsset} selectedPosition={selectedPosition} now={now} reducedMotion={reduced} zoom={zoom} focused={focused} onFloor={changeFloor} onAsset={id => { setSelectedAsset(id); setSelectedPosition(null); }} onPosition={id => { setSelectedPosition(id); setSelectedAsset(null); }}/>}
        </div>
        {model && <nav className="colab-floor-selector" aria-label="Choose a floor"><span>LEVEL</span>{[...model.floors].reverse().map(floor => <button key={floor.id} className={floor.id === floorId ? 'active' : ''} aria-pressed={floor.id === floorId} aria-label={`Show ${floor.name}`} onClick={() => changeFloor(floor.id)}>{floor.level.toString().padStart(2, '0')}</button>)}</nav>}
        {(selected || position) && <div className="colab-selection-card" role="status"><span className="colab-selection-icon">{position ? <Smartphone size={23}/> : selected && /coffee/.test(selected.type) ? <Coffee size={23}/> : <Box size={23}/>}</span><div><span className="colab-overline">{position ? shortSource(position) : 'SCHEMATIC FURNISHING'}</span><strong>{position?.label ?? selected?.name}</strong><small>{position ? `${model?.floor.get(position.floor_id)?.name}${position.accuracy_m !== null ? ` · indicative radius ${position.accuracy_m.toFixed(1)} m (unvalidated)` : ''}${position.stale ? ' · last update is stale' : ''}` : selected ? model?.space.get(selected.space_id)?.name : ''}</small></div><button className="colab-icon-button" onClick={() => { setSelectedAsset(null); setSelectedPosition(null); }} aria-label="Close selected item"><X size={17}/></button></div>}
        <div className="colab-stage-bottom"><div className="colab-view-controls"><button className={focused ? 'active' : ''} onClick={() => { setFocused(!focused); setZoom(1); }}><Layers3 size={16}/>{focused ? 'Show all levels' : 'Focus floor'}</button><div/><button aria-label="Zoom out" onClick={() => setZoom(value => Math.max(.8, value - .15))} disabled={zoom <= .8}><Minus size={17}/></button><button aria-label="Zoom in" onClick={() => setZoom(value => Math.min(1.6, value + .15))} disabled={zoom >= 1.6}><Plus size={17}/></button><button aria-label="Reset building view" onClick={() => { setZoom(1); setFocused(true); }}><Expand size={17}/></button></div><span className="colab-view-hint">Select a floor or an object to explore</span></div>
      </section>
    </div>

    <footer className="colab-footer"><div className="colab-simulation-state"><span className={state?.demo_running ? 'on' : ''}/><div><strong>{movements.length ? `${movements.length} furnishing${movements.length === 1 ? '' : 's'} moving` : 'A little movement. The same on every screen.'}</strong><span>Simulated furniture · occasional shared events{reduced ? ' · reduced motion' : ''}</span></div></div><div className="colab-demo-controls"><button onClick={() => void act(() => colabApi.demo(!state?.demo_running))} disabled={busy || !state}>{state?.demo_running ? <Pause size={15}/> : <Play size={15}/>}<span>{state?.demo_running ? 'Pause movement' : 'Resume movement'}</span></button><button className={hasWalker ? 'active' : ''} onClick={() => void act(() => colabApi.walk(!hasWalker))} disabled={busy || !state}><MonitorSmartphone size={16}/>{hasWalker ? 'Stop demo walk' : 'Demo walk'}<span className="colab-demo-tag">Simulated</span></button></div></footer>
    {actionError && <div className="colab-toast" role="alert"><span>{actionError}</span><button aria-label="Dismiss error" onClick={() => setActionError(null)}><X size={16}/></button></div>}
    {copied && <div className="colab-toast" role="status"><Check size={17}/>Shared building link copied.</div>}
    <dialog className="colab-share-dialog" ref={shareDialog} aria-labelledby="colab-share-title"><div className="colab-section-heading"><h2 id="colab-share-title">One building. Every screen.</h2><button onClick={() => shareDialog.current?.close()} aria-label="Close sharing dialog"><X size={20}/></button></div><p>Scan to open this same shared view. Furniture events and explicitly labelled positions stay in sync.</p><svg className="colab-share-qr" viewBox={`-3 -3 ${qr.size + 6} ${qr.size + 6}`} role="img" aria-label="QR code for the shared Colab view" shapeRendering="crispEdges"><rect x={-3} y={-3} width={qr.size + 6} height={qr.size + 6} fill="#fff"/><path d={qr.d} fill="#24321b"/></svg><div className="colab-share-url"><code>{shareUrl.replace(/^https?:\/\//, '')}</code><button className="colab-icon-button" onClick={() => void share()} aria-label="Copy shared building link">{copied ? <Check size={18}/> : <Copy size={18}/>}</button></div>{/localhost|127\.0\.0\.1|\[::1\]/.test(shareUrl) && <p className="colab-share-note">This local address only works on this computer. Use the public deployment address to connect a phone.</p>}<p className="colab-share-note">Opening the view does not track this phone. Location sharing requires an explicit manual placement or a paired collector.</p></dialog>
  </main>;
}

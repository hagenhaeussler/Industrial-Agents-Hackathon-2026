import { ArrowUp, ArrowUpDown, Check, DoorClosed, Footprints, History, LoaderCircle, RotateCcw, ShieldCheck, TriangleAlert, Undo2, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, api, clearAdminSession, ensureSession, mockMode } from '../api/client';
import { readAdminCode, rememberAdminCode } from '../api/adminAccess';
import { useLatest } from '../api/latest';
import type { BuildingEventRecord, EditAction, EditPreview, ServerMessage, Session, ToolResponse } from '../api/types';
import { useBuildingSocket } from '../api/ws';
import { scenario } from '../demo/scenario';
import { MapView } from '../map/MapView';
import { buildModel, floorName } from '../map/model';
import type { Model } from '../map/model';
import { humanSummary } from '../phone/guidance';
import { navigate, useLocation } from '../router';
import { DemoBadge } from '../ui/DemoBadge';
import { TracePanel } from '../trace/TracePanel';
import { VoiceButton, VoiceRoot, useVoiceSession } from '../phone/voice';
import { Upload } from './Upload';
import { AdminAccess, adminAccessError } from './Access';

type Target = { id: string; name: string; kind: 'lift' | 'stairs' | 'door' | 'room'; closed: boolean; detail: string };
type Preview = EditPreview & { target: Target; opId: string };

const message = (error: unknown) => error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong.';
const uuid = () => (globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`);
const time = (iso: string) => { try { return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }); } catch { return ''; } };

function targetOf(model: Model, id: string): Target | null {
  const closed = model.closed.has(id);
  const connector = model.connector.get(id);
  if (connector) return { id, name: connector.name, kind: connector.kind === 'lift' ? 'lift' : 'stairs', closed, detail: connector.floor_ids.map(floor => floorName(model, floor)).join(' – ') };
  const opening = model.snapshot.building.openings.find(item => item.id === id);
  if (opening) return { id, name: `${opening.kind === 'entrance' ? 'Entrance' : 'Door'} ${opening.space_ids.map(space => model.space.get(space)?.ref || model.space.get(space)?.name).filter(Boolean).join(' / ')}`, kind: 'door', closed, detail: `${floorName(model, opening.floor_id)} · ${opening.width_m.toFixed(2)} m wide${opening.step_free ? '' : ', with a step'}` };
  const space = model.space.get(id);
  if (space) return { id, name: space.name, kind: 'room', closed, detail: floorName(model, space.floor_id) };
  return null;
}

/** `/admin`: facility changes with preview → confirm once → undo (UX J6, CONTRACTS §6). Desk users are not admins. */
export function Admin() {
  return <VoiceRoot agent="admin"><AdminScreen/></VoiceRoot>;
}

function AdminScreen() {
  const { query } = useLocation();
  const demo = query.get('demo') === 'hero';
  const buildingId = query.get('building') ?? scenario.building_id;
  const latest = useLatest();
  const [model, setModel] = useState<Model | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [accessError, setAccessError] = useState<string | null>(null);
  const [floorId, setFloorId] = useState('');
  const [events, setEvents] = useState<BuildingEventRecord[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState<'preview' | 'commit' | 'undo' | 'reset' | null>(null);
  const [notice, setNotice] = useState<{ text: string; tone: 'ok' | 'error' | 'conflict' } | null>(null);
  const [ask, setAsk] = useState('');
  const [resetAvailable, setResetAvailable] = useState(true);
  const [lastCalls, setLastCalls] = useState<ToolResponse[]>([]);
  const confirmRef = useRef<HTMLButtonElement>(null);

  const reload = useCallback(() => latest(() => Promise.all([api.building(buildingId), api.events(buildingId)]), ([snapshot, log]) => {
    const next = buildModel(snapshot);
    setModel(next);
    setFloorId(current => current && next.floor.has(current) ? current : (next.floors.find(floor => floor.level === 0) ?? next.floors[0])?.id ?? '');
    setEvents(log);
  }, error => setNotice({ text: `The building did not load: ${message(error)}`, tone: 'error' })), [buildingId, latest]);

  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => {
    let live = true;
    setSession(null); setAccessError(null);
    const code = readAdminCode();
    if (!code) { clearAdminSession(buildingId); setCheckingAccess(false); return; }
    setCheckingAccess(true);
    ensureSession(buildingId, 'desk', 'admin', code).then(next => { if (live) setSession(next); }, error => {
      if (live) { clearAdminSession(buildingId); setAccessError(adminAccessError(error)); }
    }).finally(() => { if (live) setCheckingAccess(false); });
    return () => { live = false; };
  }, [buildingId]);

  const unlock = async (code: string) => {
    const next = await ensureSession(buildingId, 'desk', 'admin', code);
    rememberAdminCode(code); setSession(next); setAccessError(null);
  };
  const lock = () => { clearAdminSession(buildingId); setSession(null); setPreview(null); setLastCalls([]); setAsk(''); setAccessError(null); };

  const onSocket = useCallback((event: ServerMessage) => {
    if (event.type === 'building_changed' || event.type === 'building_reset') void reload();
  }, [reload]);
  const link = useBuildingSocket(model ? buildingId : null, onSocket, () => void reload());

  const tool = async (name: string, args: Record<string, unknown>): Promise<ToolResponse> => {
    if (!session) throw new Error('No admin session yet.');
    let response: ToolResponse;
    try { response = await api.tool(name, session.session_id, args); }
    catch (error) { if (error instanceof ApiError && error.status === 403) { lock(); setAccessError('Admin access expired. Enter the current code to continue.'); } throw error; }
    setLastCalls(current => [response, ...current].slice(0, 3));
    if (!response.ok && response.error?.code === 'forbidden') { lock(); setAccessError('Admin access expired. Enter the current code to continue.'); }
    if (!response.ok) throw Object.assign(new ApiError(200, response.error?.code ?? 'internal', response.error?.message ?? response.speech ?? 'The change failed.'), { response });
    return response;
  };

  const propose = async (target: Target, action: EditAction = target.closed ? 'open' : 'close') => {
    setBusy('preview'); setNotice(null);
    try {
      const response = await tool('propose_edit', { action, target: target.id });
      setPreview({ ...(response.result as unknown as EditPreview), target, opId: uuid() });
      requestAnimationFrame(() => confirmRef.current?.focus());
    } catch (error) { setNotice({ text: message(error), tone: 'error' }); }
    setBusy(null);
  };

  const commit = async () => {
    if (!preview || busy) return;
    setBusy('commit');
    const started = performance.now();
    try {
      await tool('commit_edit', { proposal_id: preview.proposal_id, op_id: preview.opId });
      console.info(`[timing] admin commit acknowledged in ${Math.round(performance.now() - started)} ms`);
      setNotice({ text: `${humanSummary(preview.summary)}. Phones on an active tour replan now.`, tone: 'ok' });
      setPreview(null);
      void reload();
    } catch (error) {
      if (error instanceof ApiError && error.code === 'version_conflict') setNotice({ text: 'The building changed since this preview. Preview the change again before confirming.', tone: 'conflict' });
      else setNotice({ text: message(error), tone: 'error' });
    }
    setBusy(null);
  };

  const undo = async (event: BuildingEventRecord) => {
    setBusy('undo'); setNotice(null);
    try {
      await tool('undo', { event_id: event.event_id, op_id: uuid() });
      setNotice({ text: `${humanSummary(`Undo: ${event.summary}`)}. Phones replan now.`, tone: 'ok' });
      void reload();
    } catch (error) { setNotice({ text: message(error), tone: 'error' }); }
    setBusy(null);
  };

  const reset = async () => {
    if (!session) return;
    setBusy('reset');
    try {
      await api.demoReset(buildingId, session.session_id);
      setPreview(null); setNotice({ text: 'Demo reset: the building is back to its original state.', tone: 'ok' });
      void reload();
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) setResetAvailable(false);
      setNotice({ text: error instanceof ApiError && error.status === 404 ? 'Demo reset is switched off on this server.' : message(error), tone: 'error' });
    }
    setBusy(null);
  };

  const sendAsk = async (event: FormEvent) => {
    event.preventDefault();
    if (!session || !ask.trim()) return;
    try {
      const reply = await api.chat(session.session_id, ask.trim());
      setNotice({ text: reply.reply, tone: 'ok' });
      const proposal = reply.tool_calls.find(call => call.ok && call.tool === 'propose_edit')?.result as unknown as EditPreview | undefined;
      if (proposal && model) { const target = targetOf(model, proposal.edit.target); if (target) setPreview({ ...proposal, target, opId: uuid() }); }
      if (reply.tool_calls.some(call => call.ok && (call.tool === 'commit_edit' || call.tool === 'undo'))) { setPreview(null); void reload(); }
      setAsk('');
    } catch (error) {
      setNotice({ text: error instanceof ApiError && [404, 501, 503].includes(error.status) ? 'Text and voice commands are not connected yet. Use the controls below or click a lift, stair or door on the map.' : message(error), tone: 'error' });
    }
  };

  // voice admin: a spoken proposal shows the same preview card; a spoken commit or undo refreshes the log
  const voice = useVoiceSession(session?.session_id ?? null, display => {
    if (display.kind === 'edit_preview' && model) {
      const proposal = display as unknown as EditPreview;
      const target = targetOf(model, proposal.edit?.target ?? '');
      if (target) setPreview({ ...proposal, target, opId: uuid() });
    }
    if (display.kind === 'edit_committed') { setPreview(null); void reload(); }
  });

  const pick = (id: string) => { if (!model || busy) return; const space = model.space.get(id); const connector = [...model.connector.values()].find(item => item.space_ids.includes(id)); const target = targetOf(model, connector?.id ?? space?.id ?? id); if (target) void propose(target); };

  if (checkingAccess) return <main className="desk-message"><p className="loading"><LoaderCircle className="spin" size={20}/>Verifying admin access…</p></main>;
  if (!session) return <AdminAccess onUnlock={unlock} error={accessError}/>;
  if (!model) return <main className="desk-message">{notice ? <div className="surface notice"><h1>Admin view</h1><p>{notice.text}</p></div> : <p className="loading"><LoaderCircle className="spin" size={20}/>Loading the building…</p>}</main>;

  const connectors = [...model.connector.values()].map(item => targetOf(model, item.id)!).sort((a, b) => a.name.localeCompare(b.name));
  const closedOther = model.snapshot.closed.filter(id => !model.connector.has(id)).map(id => targetOf(model, id)).filter((item): item is Target => !!item);
  const undone = new Set(events.filter(item => item.undoes).map(item => item.undoes));
  const lastOwn = [...events].reverse().find(item => item.kind !== 'undo' && !undone.has(item.event_id));

  return <main className="desk admin">
    <aside className="desk-panel surface" aria-label="Change the building">
      <header className="desk-brand">
        <button className="brand-mark admin-mark" onClick={() => navigate('/')} aria-label="Choose another building"><ShieldCheck size={18}/></button>
        <div><p className="product">Admin · building changes</p><h1>{model.snapshot.building.building.name}</h1></div>
        <button className="icon-button" onClick={lock} aria-label="Lock admin view" title="Lock admin view"><ShieldCheck size={18}/></button>
        {mockMode && <DemoBadge reason="Mock mode"/>}
      </header>

      <form className="ask" onSubmit={event => void sendAsk(event)}>
        <label htmlFor="admin-ask">What changed?</label>
        <div className="ask-field">
          <input id="admin-ask" value={ask} onChange={event => setAsk(event.target.value)} placeholder={`“${scenario.admin.say || 'Close the east lift.'}”`} autoComplete="off" maxLength={500}/>
          <VoiceButton voice={voice} onUnavailable={text => setNotice({ text: `${text} Use the controls below.`, tone: 'error' })}/>
          <button className="icon-button dark" type="submit" disabled={!ask.trim() || !session} aria-label="Send"><ArrowUp size={19}/></button>
        </div>
      </form>

      {notice && <div className={`agent-reply ${notice.tone === 'ok' ? '' : 'error'}`} role="status" aria-live="polite">
        <p>{notice.text}</p>
        {notice.tone === 'conflict' && preview && <div className="chips"><button onClick={() => void propose(preview.target, preview.edit.action)}>Preview again</button></div>}
      </div>}

      <div className="admin-scroll">
        {preview && <section className="preview-card" aria-labelledby="preview-title">
          <p className="policy">Preview · nothing has changed yet</p>
          <h2 id="preview-title">{preview.summary}</h2>
          <p className="muted">{preview.target.detail}</p>
          <ul className="effects">
            <li><strong>{preview.effects.active_tours_affected}</strong> active {preview.effects.active_tours_affected === 1 ? 'tour' : 'tours'} affected</li>
            {preview.effects.tours.filter(item => item.after_m !== item.before_m).slice(0, 4).map(item => <li key={item.tour_id}>{item.reachable_after && item.after_m !== null ? <>Tour {item.tour_id.slice(0, 4)}: {Math.round(item.before_m)} m → <strong>{Math.round(item.after_m)} m</strong></> : <>Tour {item.tour_id.slice(0, 4)}: <strong>no route any more</strong></>}</li>)}
            <li><strong>{preview.effects.newly_unreachable_spaces}</strong> {preview.effects.newly_unreachable_spaces === 1 ? 'room becomes' : 'rooms become'} unreachable</li>
          </ul>
          <div className="tour-actions">
            <button className="secondary-button" onClick={() => setPreview(null)} disabled={busy === 'commit'}><X size={17}/>Cancel</button>
            <button ref={confirmRef} className="primary-button" onClick={() => void commit()} disabled={!!busy}>{busy === 'commit' ? <LoaderCircle className="spin" size={18}/> : <Check size={18}/>}Confirm: {preview.edit.action === 'close' ? 'close' : preview.edit.action === 'open' ? 'reopen' : 'apply'}</button>
          </div>
        </section>}

        <TracePanel model={model} responses={lastCalls}/>

        <section className="admin-section" aria-labelledby="vertical-title">
          <h2 id="vertical-title">Lifts and stairs</h2>
          <ul className="element-list">
            {connectors.map(item => <li key={item.id} className={item.closed ? 'closed' : ''}>
              <span className="element-icon" aria-hidden="true">{item.kind === 'lift' ? <ArrowUpDown size={18}/> : <Footprints size={18}/>}</span>
              <span className="stop-copy"><strong>{item.name}</strong><span>{item.closed ? 'Closed' : 'Open'} · {item.detail}</span></span>
              <button className={item.closed ? 'secondary-button' : 'primary-button'} disabled={!!busy || !session} onClick={() => void propose(item)}>{item.closed ? 'Reopen…' : 'Close…'}</button>
            </li>)}
          </ul>
          {closedOther.length > 0 && <>
            <h3 className="floor-heading">Other closures</h3>
            <ul className="element-list">{closedOther.map(item => <li key={item.id} className="closed">
              <span className="element-icon" aria-hidden="true"><DoorClosed size={18}/></span>
              <span className="stop-copy"><strong>{item.name}</strong><span>Closed · {item.detail}</span></span>
              <button className="secondary-button" disabled={!!busy || !session} onClick={() => void propose(item)}>Reopen…</button>
            </li>)}</ul>
          </>}
          <p className="fineprint">Click a lift, stair or door on the map to change it. Every change shows a preview first.</p>
        </section>

        <section className="admin-section" aria-labelledby="log-title">
          <h2 id="log-title"><History size={16} aria-hidden="true"/> Changes</h2>
          {!events.length && <p className="empty">No changes yet. The building is in its original state.</p>}
          <ol className="event-log">
            {[...events].reverse().slice(0, 12).map(item => <li key={item.event_id} className={undone.has(item.event_id) ? 'undone' : ''}>
              <span><strong>{item.kind === 'undo' ? humanSummary(item.summary) : item.summary}</strong><span>{time(item.created_at)} · version {item.building_version}{undone.has(item.event_id) ? ' · undone' : ''}</span></span>
              {item === lastOwn && <button className="secondary-button" disabled={!!busy} onClick={() => void undo(item)}><Undo2 size={16}/>Undo</button>}
            </li>)}
          </ol>
        </section>

        <Upload sessionId={session?.session_id ?? null}/>
      </div>

      {demo && resetAvailable && <footer className="plan-bar admin-foot">
        <button className="link-button" disabled={!!busy || !session} onClick={() => void reset()}><RotateCcw size={14}/> Reset demo</button>
      </footer>}
    </aside>

    <section className="desk-map" aria-label="Building map">
      <MapView model={model} floorId={floorId} onFloor={setFloorId} showParts={false} onSpace={pick} onOpening={pick}
        frame={preview ? 'space' : 'all'} frameSpaceIds={preview ? (model.connector.get(preview.target.id)?.space_ids ?? [preview.target.id]) : undefined}
        highlightSpaceIds={preview ? (model.connector.get(preview.target.id)?.space_ids ?? (model.space.has(preview.target.id) ? [preview.target.id] : [])) : []}
        frameKey={preview ? `preview:${preview.proposal_id}` : 'all'}/>
      {link === 'offline' && <p className="link-status surface" role="status"><TriangleAlert size={14}/> Reconnecting to live updates…</p>}
    </section>
  </main>;
}

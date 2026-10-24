import { Check, FileText, LoaderCircle, Upload, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { DragEvent, FormEvent } from 'react';
import { ApiError, api, mockMode } from '../api/client';
import { forgetAdminCode, readAdminCode, rememberAdminCode } from '../api/adminAccess';
import type { TeamBuildingResult, Validation } from '../api/types';
import { navigate } from '../router';

type Kind = 'equipment' | 'plan';
const limits = { equipment: 2_000_000, plan: 5_000_000 };

export function NewBuilding({ teamId, onBack, onCreated }: { teamId: string; onBack: () => void; onCreated: (id: string) => void }) {
  const [equipment, setEquipment] = useState<File | null>(null);
  const [plan, setPlan] = useState<File | null>(null);
  const [over, setOver] = useState<Kind | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [result, setResult] = useState<TeamBuildingResult | null>(null);
  const [access, setAccess] = useState(false);
  const [code, setCode] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const alive = useRef(true);
  const sending = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (access && dialog.current && !dialog.current.open) dialog.current.showModal();
    if (!access && dialog.current?.open) dialog.current.close();
  }, [access]);

  const choose = (kind: Kind, file?: File) => {
    if (!file || busy) return;
    setError(null); setValidation(null);
    if (!file.name.toLowerCase().endsWith(kind === 'plan' ? '.json' : '.csv')) { setError(kind === 'plan' ? 'Choose a structured JSON floor plan.' : 'Choose a CSV equipment list.'); return; }
    if (file.size > limits[kind]) { setError(`${kind === 'plan' ? 'Floor plans' : 'Equipment lists'} must be smaller than ${kind === 'plan' ? '5' : '2'} MB.`); return; }
    if (kind === 'equipment') setEquipment(file); else setPlan(file);
  };
  const drop = (kind: Kind, event: DragEvent) => { event.preventDefault(); setOver(null); choose(kind, event.dataTransfer.files[0]); };

  const upload = async (credential: string) => {
    if (!equipment || !plan || sending.current) return;
    if (mockMode) { setError('Building uploads need the live app. Open this page without mock mode.'); return; }
    sending.current = true; setBusy(true); setError(null); setValidation(null);
    try {
      let raw: unknown;
      try { raw = JSON.parse(await plan.text()); } catch { throw new Error('The floor plan is not valid JSON. Choose a structured building plan.'); }
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('The floor plan must contain a building, floors and rooms.');
      const inventory = await equipment.text();
      if (!alive.current) return;
      const created = await api.createTeamBuilding(teamId, raw as Record<string, unknown>, inventory, credential);
      if (!alive.current) return;
      rememberAdminCode(credential); setCode(''); setAccess(false); setResult(created); onCreated(created.building_id);
    } catch (reason) {
      if (!alive.current) return;
      if (reason instanceof ApiError && reason.status === 403) { forgetAdminCode(); setCode(''); setAccess(true); }
      const report = reason instanceof ApiError ? (reason.data as { validation?: Validation } | undefined)?.validation : undefined;
      setValidation(report ?? null);
      setError(reason instanceof Error ? reason.message : 'The upload did not finish. Check the team buildings before trying again.');
    } finally { sending.current = false; if (alive.current) setBusy(false); }
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy || !equipment || !plan) return;
    const credential = readAdminCode();
    if (credential) void upload(credential); else { setError(null); setAccess(true); }
  };

  if (result) return <div className="building-created" role="status">
    <Check size={26} aria-hidden="true"/><h3>Your building is ready</h3>
    <p>{result.validation.stats.floors} floors · {result.validation.stats.spaces} rooms and spaces · {result.validation.stats.assets} equipment items</p>
    {!!result.validation.warnings.length && <details><summary>Review {result.validation.warnings.length} validation notes</summary><ul>{result.validation.warnings.slice(0, 8).map((item, index) => <li key={index}>{item.message}</li>)}</ul></details>}
    <button className="primary-button" onClick={() => navigate(`/desk?building=${encodeURIComponent(result.building_id)}&team=${encodeURIComponent(teamId)}`)}>Open building</button>
    <button className="secondary-button" onClick={onBack}>Back to buildings</button>
  </div>;

  const box = (kind: Kind, title: string, file: File | null, hint: string) => <label className={`building-file-box${over === kind ? ' over' : ''}${file ? ' ready' : ''}`} htmlFor={`building-${kind}`}
    onDragOver={event => { event.preventDefault(); if (!busy) setOver(kind); }} onDragLeave={() => setOver(null)} onDrop={event => drop(kind, event)}>
    {file ? <Check size={24} aria-hidden="true"/> : kind === 'plan' ? <FileText size={25} aria-hidden="true"/> : <Upload size={25} aria-hidden="true"/>}
    <strong>{title}</strong>
    {file ? <span className="building-file-name">{file.name}</span> : <small>{hint}</small>}
    <input className="sr-only" id={`building-${kind}`} type="file" accept={kind === 'plan' ? '.json,application/json' : '.csv,text/csv'} disabled={busy}
      onChange={event => { choose(kind, event.target.files?.[0]); event.target.value = ''; }}/>
  </label>;

  return <>
    <form className="new-building-form" onSubmit={submit}>
      {box('equipment', 'Equipment list', equipment, 'Drop your CSV here, or choose a file · up to 2 MB')}
      {box('plan', 'Floor plan', plan, 'Drop your building JSON here, or choose a file · up to 5 MB')}
      {error && !access && <div className="workspace-error" role="alert"><p>{error}</p>{validation && <ul>{validation.errors.slice(0, 5).map((item, index) => <li key={index}>{item.message}</li>)}</ul>}</div>}
      <button className="primary-button" type="submit" disabled={busy || !equipment || !plan}>{busy ? <><LoaderCircle className="spin" size={17}/>Creating building…</> : <><Upload size={17}/>Upload and create building</>}</button>
      <button className="workspace-back-link" type="button" onClick={onBack} disabled={busy}>Back to buildings</button>
      <details className="upload-format-help"><summary>File formats</summary><p>The JSON plan contains measured floors, room outlines and doors. Equipment CSV columns: asset_id, name, type, space_id, x_m, y_m. Room IDs and coordinates must match the plan. Equipment in the CSV replaces any equipment already in the JSON.</p></details>
    </form>
    <dialog ref={dialog} className="team-access-dialog" aria-labelledby="team-access-title" onCancel={() => { if (!busy) setAccess(false); }} onClose={() => setAccess(false)}>
      <form onSubmit={event => { event.preventDefault(); if (code.trim() && !busy) void upload(code.trim()); }}>
        <div className="row" style={{ justifyContent: 'space-between' }}><h2 id="team-access-title">Building access</h2><button className="workspace-back" type="button" aria-label="Close access dialog" onClick={() => setAccess(false)} disabled={busy}><X size={18}/></button></div>
        <p>Enter the private access code to add this building to your team.</p>
        <label htmlFor="building-access-code">Access code</label><input id="building-access-code" type="password" autoComplete="off" value={code} onChange={event => setCode(event.target.value)} autoFocus disabled={busy}/>
        {error && <p role="alert" className="workspace-error">{error}</p>}
        <div className="row"><button className="secondary-button" type="button" disabled={busy} onClick={() => setAccess(false)}>Cancel</button><button className="primary-button" type="submit" disabled={!code.trim() || busy}>{busy ? 'Creating…' : 'Create building'}</button></div>
      </form>
    </dialog>
  </>;
}

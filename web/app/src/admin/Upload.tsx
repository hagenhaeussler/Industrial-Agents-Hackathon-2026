import { FileUp, LoaderCircle } from 'lucide-react';
import { useRef, useState } from 'react';
import type { DragEvent } from 'react';
import { ApiError, api } from '../api/client';
import type { Validation } from '../api/types';
import { navigate } from '../router';

type State = { kind: 'idle' } | { kind: 'busy'; name: string } | { kind: 'done'; id: string; validation: Validation } | { kind: 'failed'; text: string; validation?: Validation };

/** Upload a kit-format building.json (UX J8 stage 1). The file is data: shown as text only, validated by the server. */
export function Upload({ sessionId }: { sessionId: string | null }) {
  const input = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<State>({ kind: 'idle' });
  const [over, setOver] = useState(false);

  const send = async (file: File) => {
    if (!sessionId) return;
    setState({ kind: 'busy', name: file.name });
    let raw: unknown;
    try { raw = JSON.parse(await file.text()); } catch { setState({ kind: 'failed', text: `${file.name} is not valid JSON.` }); return; }
    try {
      const result = await api.uploadBuilding(raw, sessionId);
      setState({ kind: 'done', id: result.building_id, validation: result.validation });
    } catch (error) {
      const validation = error instanceof ApiError ? (error.data as { validation?: Validation } | undefined)?.validation : undefined;
      const text = error instanceof ApiError && error.status === 503 ? 'Uploading needs the building validator, which is not available on this server.' : error instanceof Error ? error.message : 'The upload failed.';
      setState({ kind: 'failed', text, validation });
    }
  };
  const drop = (event: DragEvent) => { event.preventDefault(); setOver(false); const file = event.dataTransfer.files[0]; if (file) void send(file); };

  const report = (validation: Validation) => <div className="validation">
    <p className="stats">{Object.entries(validation.stats).map(([key, value]) => <span key={key}><strong>{value}</strong> {key.replace(/_/g, ' ')}</span>)}</p>
    {validation.errors.length > 0 && <><h4>{validation.errors.length} {validation.errors.length === 1 ? 'error' : 'errors'} (must be fixed)</h4><ul>{validation.errors.slice(0, 6).map((item, index) => <li key={index}><code>{item.path}</code> {item.message}</li>)}</ul></>}
    {validation.warnings.length > 0 && <details><summary>{validation.warnings.length} {validation.warnings.length === 1 ? 'warning' : 'warnings'}</summary><ul>{validation.warnings.slice(0, 20).map((item, index) => <li key={index}><code>{item.path}</code> {item.message}</li>)}</ul></details>}
  </div>;

  return <section className="admin-section" aria-labelledby="upload-title">
    <h2 id="upload-title"><FileUp size={16} aria-hidden="true"/> Add a building</h2>
    <div className={`drop-zone ${over ? 'over' : ''}`} onDragOver={event => { event.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={drop}>
      <p>Drop a <code>building.json</code> here (kit format) or</p>
      <button className="secondary-button" disabled={!sessionId || state.kind === 'busy'} onClick={() => input.current?.click()}>{state.kind === 'busy' ? <><LoaderCircle className="spin" size={16}/>Checking {state.name}…</> : 'Choose a file'}</button>
      <input ref={input} type="file" accept=".json,application/json" hidden onChange={event => { const file = event.target.files?.[0]; if (file) void send(file); event.target.value = ''; }}/>
    </div>
    {state.kind === 'done' && <div className="upload-result ok" role="status">
      <p><strong>Building added.</strong> Every tool works on it now.</p>
      {report(state.validation)}
      <div className="row"><button className="primary-button" onClick={() => navigate(`/desk?building=${encodeURIComponent(state.id)}`)}>Open in desk</button><button className="secondary-button" onClick={() => navigate(`/admin?building=${encodeURIComponent(state.id)}`)}>Manage it</button></div>
    </div>}
    {state.kind === 'failed' && <div className="upload-result error" role="alert"><p><strong>Not added.</strong> {state.text}</p>{state.validation && report(state.validation)}</div>}
  </section>;
}

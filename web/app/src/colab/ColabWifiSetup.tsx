import { Check, Copy, LoaderCircle, Radio, RefreshCw, ShieldCheck, Wifi } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import type { components } from '../api/schema.gen';
import type { ColabModel } from '../api/colab';
import { useLatest } from '../api/latest';
import './colab-wifi.css';

type Status = components['schemas']['WifiStatus'];
type Pairing = components['schemas']['PairedCollector'];

async function wifiRequest<T>(path: string, code?: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/colab/${path}`, {
    method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
    headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(code ? { 'X-Admin-Token': code } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new Error(typeof error?.detail === 'string' ? error.detail : 'The Wi-Fi setup request failed.');
  }
  return response.json() as Promise<T>;
}

/** Native measurements are admitted here; this component never scans browser radios. */
export function ColabWifiSetup({ model, floorId }: { model: ColabModel; floorId: string }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [adminCode, setAdminCode] = useState('');
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [deviceId, setDeviceId] = useState('');
  const [roomId, setRoomId] = useState('');
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const latestStatus = useLatest();
  const rooms = model.building.spaces.filter(room => room.floor_id === floorId && !['lift', 'stair'].includes(room.type));

  const refresh = useCallback(() => latestStatus(() => wifiRequest<Status>('wifi/status'), setStatus), [latestStatus]);
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 5000); return () => clearInterval(timer); }, [refresh]);
  useEffect(() => { setRoomId(''); setX(''); setY(''); }, [floorId]);

  const chooseRoom = (id: string) => {
    setRoomId(id);
    const point = model.anchors[id];
    setX(point ? point[0].toFixed(2) : '');
    setY(point ? point[1].toFixed(2) : '');
  };
  const act = async (operation: () => Promise<void>) => {
    setBusy(true); setError(''); setMessage('');
    try { await operation(); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Wi-Fi setup failed.'); }
    finally { setBusy(false); }
  };
  const pair = () => void act(async () => {
    const result = await wifiRequest<Pairing>('pair', adminCode, { label: 'Survey Android' });
    setPairing(result); setDeviceId(result.device_id);
    setMessage('Collector paired. Keep its token private and use its matching device ID.');
  });
  const capture = () => void act(async () => {
    const result = await wifiRequest<Status>('wifi/capture', adminCode, {
      device_id: deviceId, floor_id: floorId, x: Number(x), y: Number(y),
      label: model.building.spaces.find(room => room.id === roomId)?.name ?? 'Survey point',
    });
    setMessage(`Saved survey point ${result.calibration_points}. Collect distinct points on both floors, then validate at unseen spots.`);
  });
  const copyToken = async () => {
    if (!pairing) return;
    try { await navigator.clipboard.writeText(pairing.token); setCopied(true); window.setTimeout(() => setCopied(false), 2000); }
    catch { setError('Clipboard access was denied. Select the token text to copy it.'); }
  };

  return <details className="colab-wifi-setup">
    <summary><ShieldCheck size={16}/>Set up real Wi-Fi readings<span>{status?.calibration_points ?? 0} points</span></summary>
    <div className="colab-wifi-content">
      <p>Use an Android native collector. Router coordinates are unnecessary. The iPhone and desktop can view its shared position; they do not inherit independent Wi-Fi scanning.</p>
      <p><a href="/api/colab/collector.py" download>Download Python collector</a> · <a href="/api/colab/guide.md" download>Setup instructions</a></p>
      <div className="colab-wifi-status"><Wifi size={15}/><span>{status?.ready ? 'Survey available · accuracy not validated' : 'Survey needed · no automatic Wi-Fi fix'}</span><button className="colab-icon-button" onClick={() => void refresh()} aria-label="Refresh collector status"><RefreshCw size={14}/></button></div>
      <label>Admin code<input type="password" autoComplete="off" value={adminCode} onChange={event => setAdminCode(event.target.value)} placeholder="Required to pair and calibrate"/></label>
      <button className="colab-primary" disabled={busy || !adminCode} onClick={pair}>{busy ? <LoaderCircle size={15} className="spin"/> : <Radio size={15}/>}Pair Android collector</button>
      {pairing && <div className="colab-pairing-result">
        <strong>Collector device ID</strong><code>{pairing.device_id}</code>
        <strong>Private receive token · expires in 12 hours</strong><code className="colab-private-token">{pairing.token}</code>
        <button onClick={() => void copyToken()}>{copied ? <Check size={14}/> : <Copy size={14}/>}Copy collector token</button>
        <p>Use this as <code>COLAB_TRACKING_TOKEN</code>, with <code>--device-id {pairing.device_id}</code>. Download the collector and follow its Android setup instructions in the project.</p>
        <p>Upload endpoint: <code>{location.origin}/api/colab/wifi/scans</code>. The admin code is never sent by the collector.</p>
      </div>}
      <label>Active collector<select value={deviceId} onChange={event => setDeviceId(event.target.value)}><option value="">Choose a paired device</option>{pairing && !status?.devices.some(device => device.device_id === pairing.device_id) && <option value={pairing.device_id}>{pairing.device_id} · waiting for readings</option>}{status?.devices.map(device => <option key={device.device_id} value={device.device_id}>{device.label} · {device.readings_count} radio readings</option>)}</select></label>
      <p>Stand at a known point in a room on the selected floor. Pick the room, then adjust its schematic metre coordinates if needed. A fresh scan with at least three radios must arrive before capture.</p>
      <label>Survey room<select value={roomId} onChange={event => chooseRoom(event.target.value)}><option value="">Choose where you are standing</option>{rooms.map(room => <option key={room.id} value={room.id}>{room.name}</option>)}</select></label>
      <div className="colab-survey-coordinates"><label>X · model metres<input type="number" step="0.1" value={x} onChange={event => setX(event.target.value)}/></label><label>Y · model metres<input type="number" step="0.1" value={y} onChange={event => setY(event.target.value)}/></label></div>
      <button className="colab-primary" disabled={busy || !adminCode || !deviceId || !roomId || x === '' || y === '' || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y))} onClick={capture}>Save latest scan at this point</button>
      <p className="colab-wifi-caveat">Mobile data can send updates, but cellular service alone does not give this indoor map a room or floor. Wi-Fi scan throttling can cause gaps; old scans never become new fixes.</p>
      {message && <p className="colab-wifi-success" role="status">{message}</p>}
      {error && <p className="colab-wifi-error" role="alert">{error}</p>}
    </div>
  </details>;
}

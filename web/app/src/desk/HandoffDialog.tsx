import { Check, Copy, X } from 'lucide-react';
import QRCode from 'qrcode';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Tour } from '../api/types';

/** The phone link: `PUBLIC_BASE_URL/go/<tour_id>` and nothing else (CONTRACTS §10). */
export const publicBase = () => (import.meta.env.VITE_PUBLIC_BASE_URL as string | undefined)?.replace(/\/$/, '') || location.origin;
export const tourUrl = (tourId: string) => `${publicBase()}/go/${tourId}`;

/** QR modules as one SVG path (no HTML injection). */
export function qrPath(text: string): { size: number; d: string } {
  const { modules } = QRCode.create(text, { errorCorrectionLevel: 'M' });
  let d = '';
  for (let y = 0; y < modules.size; y++) for (let x = 0; x < modules.size; x++) if (modules.get(y, x)) d += `M${x} ${y}h1v1h-1z`;
  return { size: modules.size, d };
}

type Props = { tour: Tour | null; open: boolean; opened: boolean; onClose: () => void };

export function HandoffDialog({ tour, open, opened, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [copied, setCopied] = useState(false);
  const url = tour ? tourUrl(tour.tour_id) : '';
  const local = /localhost|127\.0\.0\.1|\[::1\]/.test(url);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const qr = useMemo(() => (url ? qrPath(url) : null), [url]);

  const copy = async () => {
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 1600); } catch { /* clipboard blocked: the URL is visible */ }
  };

  return <dialog ref={ref} className="sheet handoff-sheet" aria-labelledby="handoff-title" onClose={onClose} onCancel={onClose}>
    <header className="sheet-header">
      <div><h2 id="handoff-title">Scan with your phone</h2><p>The tour opens on the phone with the same stops and order.</p></div>
      <button className="icon-button" onClick={onClose} aria-label="Close"><X size={22}/></button>
    </header>
    {qr && <svg className="qr" viewBox={`-2 -2 ${qr.size + 4} ${qr.size + 4}`} role="img" aria-label={`QR code for ${url}`} shapeRendering="crispEdges"><rect x={-2} y={-2} width={qr.size + 4} height={qr.size + 4} fill="#fff"/><path d={qr.d} fill="#191c16"/></svg>}
    <div className="handoff-url"><code>{url.replace(/^https?:\/\//, '')}</code><button className="icon-button" onClick={() => void copy()} aria-label="Copy link">{copied ? <Check size={18}/> : <Copy size={18}/>}</button></div>
    {local && <p className="fineprint warn">This address only works on this computer. Open the app through its public or LAN address so a phone can reach it.</p>}
    <p className={`handoff-status ${opened ? 'done' : ''}`} role="status" aria-live="polite">{opened ? <><Check size={18}/>Opened on phone</> : <><span className="pulse" aria-hidden="true"/>Waiting for the phone…</>}</p>
  </dialog>;
}

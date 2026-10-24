import jsQR from 'jsqr';
import { X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useCamera } from '../camera/useCamera';

/**
 * Marker IDs from a decoded QR text. Only `/m/<marker_id>` links count; the text is data, never followed
 * as a link. Frames stay in this canvas and are never stored or uploaded.
 */
export function markerIdFrom(text: string): string | null {
  const match = /(?:^|\/)m\/(mk_[a-z0-9]{4,32})(?:[/?#]|$)/i.exec(text.trim());
  return match?.[1] ?? null;
}

export function Scanner({ open, onMarker, onClose }: { open: boolean; onMarker: (markerId: string) => void; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const camera = useCamera();
  const cameraRef = useRef(camera);
  cameraRef.current = camera;
  const [hint, setHint] = useState('Point the camera at the position code on the door.');

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog || !open) return;
    if (!dialog.open) dialog.showModal();
    setHint('Point the camera at the position code on the door.');
    void cameraRef.current.start();
    return () => { cameraRef.current.stop(); if (dialog.open) dialog.close(); };
  }, [open]);

  useEffect(() => {
    if (camera.state.kind !== 'live') return;
    let done = false;
    const timer = setInterval(() => {
      const video = cameraRef.current.videoRef.current;
      if (done || !video || video.readyState < 2 || !video.videoWidth) return;
      const scale = Math.min(1, 640 / video.videoWidth);
      const width = Math.round(video.videoWidth * scale), height = Math.round(video.videoHeight * scale);
      canvas.current ??= document.createElement('canvas');
      canvas.current.width = width; canvas.current.height = height;
      const context = canvas.current.getContext('2d', { willReadFrequently: true });
      if (!context) return;
      context.drawImage(video, 0, 0, width, height);
      const code = jsQR(context.getImageData(0, 0, width, height).data, width, height, { inversionAttempts: 'dontInvert' });
      if (!code?.data) return;
      const id = markerIdFrom(code.data);
      if (id) { done = true; cameraRef.current.stop(); onMarker(id); }
      else setHint('That code is not a position code. Look for the code printed on the door sign.');
    }, 180);
    return () => { done = true; clearInterval(timer); };
  }, [camera.state.kind, onMarker]);

  const close = () => { camera.stop(); onClose(); };

  return <dialog ref={ref} className="sheet scanner-sheet" aria-labelledby="scan-title" onClose={close} onCancel={close}>
    <header className="sheet-header">
      <div><h2 id="scan-title">Scan a position code</h2><p>{hint}</p></div>
      <button className="icon-button" onClick={close} aria-label="Close scanner"><X size={22}/></button>
    </header>
    <div className="scanner-view">
      <video ref={camera.videoRef} autoPlay playsInline muted aria-label="Camera view for scanning"/>
      <span className="scanner-frame" aria-hidden="true"/>
    </div>
    {camera.state.kind === 'error' && <p className="plan-error" role="alert">{camera.state.message} You can choose your room instead.</p>}
    {camera.state.kind === 'requesting' && <p className="fineprint">Waiting for camera permission…</p>}
  </dialog>;
}

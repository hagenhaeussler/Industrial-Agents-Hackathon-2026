import { ArrowUp, Flag, Map as MapIcon, ScanQrCode } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { Point, ReachableRoute } from '../api/types';
import { useCamera } from '../camera/useCamera';
import { startAr } from '../camera/ar/ArSession';
import type { ArHandle } from '../camera/ar/ArSession';
import { getXr } from '../camera/ar/deviceGate';
import { arrowState } from './cameraArrow';
import type { Anchor } from './cameraArrow';

/** Latest device alpha in degrees, or null without a motion sensor (relative, not a compass). */
export function useDeviceAlpha(enabled: boolean): number | null {
  const [alpha, setAlpha] = useState<number | null>(null);
  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;
    let frame = 0;
    const onOrientation = (event: DeviceOrientationEvent) => {
      if (event.alpha === null) return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setAlpha(event.alpha));
    };
    window.addEventListener('deviceorientation', onOrientation);
    return () => { window.removeEventListener('deviceorientation', onOrientation); cancelAnimationFrame(frame); };
  }, [enabled]);
  return alpha;
}

type Props = {
  leg: ReachableRoute | null;
  step: number;
  position: Point | null;
  floorId: string;
  anchor: Anchor | null;
  motion: boolean;
  onAlpha: (alpha: number | null) => void;
  onScan: () => void;
  onExit: (message?: string) => void;
  minimap: ReactNode;
};

/** The camera guidance view: live camera, a direction-only arrow, the minimap. Frames never leave the video element. */
export function CameraGuide({ leg, step, position, floorId, anchor, motion, onAlpha, onScan, onExit, minimap }: Props) {
  const camera = useCamera();
  const cameraRef = useRef(camera);
  cameraRef.current = camera;
  const alpha = useDeviceAlpha(motion);
  const viewRef = useRef<HTMLDivElement>(null);
  const arCanvasRef = useRef<HTMLDivElement>(null);
  const arRef = useRef<ArHandle | null>(null);
  const arAttempt = useRef<AbortController | null>(null);
  const exitRef = useRef(onExit);
  exitRef.current = onExit;
  const [supportsAr, setSupportsAr] = useState(false);
  const [standing, setStanding] = useState(false);
  const [arState, setArState] = useState<'off' | 'starting' | 'live'>('off');
  const [arError, setArError] = useState<string | null>(null);
  useEffect(() => { onAlpha(alpha); }, [alpha, onAlpha]);
  useEffect(() => {
    void cameraRef.current.start();
    return () => cameraRef.current.stop();
  }, []);
  useEffect(() => {
    let live = true;
    void getXr()?.isSessionSupported('immersive-ar').then(ok => { if (live) setSupportsAr(ok); }, () => undefined);
    return () => { live = false; };
  }, []);
  useEffect(() => {
    const pause = () => { if (document.hidden) exitRef.current('Camera guidance paused while the app was in the background.'); };
    const leave = () => exitRef.current();
    document.addEventListener('visibilitychange', pause);
    window.addEventListener('pagehide', leave);
    return () => { document.removeEventListener('visibilitychange', pause); window.removeEventListener('pagehide', leave); };
  }, []);
  useEffect(() => {
    setStanding(false);
    if (arAttempt.current) exitRef.current('The route changed. Scan a position code before starting AR again.');
    return () => { arAttempt.current?.abort(); void arRef.current?.stopAr(); arRef.current = null; };
  }, [leg, anchor]);

  const beginAr = () => {
    if (!leg || !anchor || !standing || !supportsAr || !viewRef.current || !arCanvasRef.current || arState !== 'off') return;
    const attempt = new AbortController();
    arAttempt.current = attempt;
    setArState('starting'); setArError(null);
    // Call directly from this click. startAr requests the XR session before loading Three.js.
    void startAr({ route: leg, marker: { ...anchor, building_id: leg.building_id }, container: arCanvasRef.current, overlay: viewRef.current,
      stopCamera: () => cameraRef.current.stop(), signal: attempt.signal,
      onLost: text => { if (!attempt.signal.aborted) onExit(text); },
    }).then(handle => { if (attempt.signal.aborted) void handle.stopAr(); else { arRef.current = handle; setArState('live'); } }, () => {
      if (attempt.signal.aborted) return;
      setArState('off'); setStanding(false);
      setArError('AR could not start. The map and direction-only camera view still work.');
      void cameraRef.current.start();
    });
  };
  const endAr = () => {
    arAttempt.current?.abort(); void arRef.current?.stopAr(); arRef.current = null;
    onExit();
  };

  const state = arrowState(leg, step, position, floorId, anchor, motion ? alpha : null);
  const failed = camera.state.kind === 'error' ? camera.state.message : null;

  const arAvailable = supportsAr && !!leg && leg.geometry !== 'provisional' && !!anchor && anchor.floor_id === floorId;

  return <div className="camera-guide" ref={viewRef}>
    <video ref={camera.videoRef} className={camera.state.kind === 'live' ? 'live' : ''} autoPlay playsInline muted aria-label="Live camera view of your surroundings"/>
    <div ref={arCanvasRef} className="ar-canvas"/>
    <div className="camera-guide-minimap surface" aria-hidden="true">{minimap}</div>
    {arState !== 'off'
      ? <div className="camera-ar-controls surface" role="status"><p>{arState === 'live' ? 'Experimental AR · current-floor walking line' : 'Waiting for AR permission…'}</p><button className="secondary-button" onClick={endAr}>Back to map</button></div>
      : failed
      ? <div className="camera-card surface" role="alert"><p>{failed} The map still guides you.</p><button className="primary-button" onClick={() => onExit(failed)}><MapIcon size={18}/>Back to the map</button></div>
      : state.kind === 'arrow'
        ? <div className="camera-arrow" role="img" aria-label={`Direction arrow, ${Math.round(state.bearing)} degrees`}>
          <span className="arrow-disc" style={{ transform: `rotate(${state.bearing}deg)` }}><ArrowUp size={72} strokeWidth={2.6}/></span>
          <span className="direction-label surface">Direction only{state.relative ? ' · facing the code direction' : ''}</span>
        </div>
        : state.kind === 'scan'
          ? <div className="camera-card surface" role="status">
            <p>{state.reason === 'other_floor' ? 'New floor: scan the next position code to point the arrow.' : 'Scan a position code on a door sign to point the arrow.'}</p>
            <button className="primary-button" onClick={onScan}><ScanQrCode size={18}/>Scan the next position code</button>
          </div>
          : state.kind === 'arrived'
            ? <div className="camera-arrow" role="status"><span className="arrow-disc arrived"><Flag size={56} strokeWidth={2.6}/></span><span className="direction-label surface">You are here</span></div>
            : null}
    {camera.state.kind === 'requesting' && <p className="direction-label surface camera-waiting" role="status">Waiting for camera permission…</p>}
    {arAvailable && arState === 'off' && !failed && <div className="camera-ar-controls surface">
      <label><input type="checkbox" checked={standing} onChange={event => setStanding(event.target.checked)}/>I am standing at the scanned code, facing its indicated direction.</label>
      <button className="secondary-button" disabled={!standing} onClick={beginAr}>Try experimental AR</button>
      <p className="fineprint">Marker calibration is manual. Accuracy needs checking on this device.</p>
    </div>}
    {arError && <p className="camera-ar-error surface" role="alert">{arError}</p>}
  </div>;
}

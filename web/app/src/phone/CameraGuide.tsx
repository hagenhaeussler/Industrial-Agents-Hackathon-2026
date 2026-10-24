import { ArrowUp, Flag, Map as MapIcon, ScanQrCode } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { Point, ReachableRoute } from '../api/types';
import { useCamera } from '../camera/useCamera';
import { arrowState } from './cameraArrow';
import type { Anchor } from './cameraArrow';

type Orientation = { requestPermission?: () => Promise<'granted' | 'denied'> };

/** iOS asks for motion access from a tap; elsewhere it is simply available (or absent). */
export async function requestMotion(): Promise<boolean> {
  const event = (globalThis as { DeviceOrientationEvent?: Orientation }).DeviceOrientationEvent;
  if (!event) return false;
  if (typeof event.requestPermission !== 'function') return true;
  try { return (await event.requestPermission()) === 'granted'; } catch { return false; }
}

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
  useEffect(() => { onAlpha(alpha); }, [alpha, onAlpha]);
  useEffect(() => {
    void cameraRef.current.start();
    return () => cameraRef.current.stop();
  }, []);

  const state = arrowState(leg, step, position, floorId, anchor, motion ? alpha : null);
  const failed = camera.state.kind === 'error' ? camera.state.message : null;

  return <div className="camera-guide">
    <video ref={camera.videoRef} className={camera.state.kind === 'live' ? 'live' : ''} autoPlay playsInline muted aria-label="Live camera view of your surroundings"/>
    <div className="camera-guide-minimap surface" aria-hidden="true">{minimap}</div>
    {failed
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
  </div>;
}

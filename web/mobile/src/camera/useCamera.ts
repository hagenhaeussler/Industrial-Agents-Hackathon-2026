import { useEffect, useRef, useState } from 'react';

type CameraState =
  | { kind: 'off' }
  | { kind: 'requesting' }
  | { kind: 'live' }
  | { kind: 'error'; message: string };

function cameraError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError') return 'Kamerazugriff wurde nicht erlaubt. Erlaube ihn in den Website-Einstellungen deines Browsers.';
    if (error.name === 'NotFoundError') return 'Keine Kamera gefunden. Du kannst die Demo trotzdem ausprobieren.';
    if (error.name === 'NotReadableError') return 'Die Kamera ist gerade belegt. Schließe andere Kamera-Apps und versuche es erneut.';
  }
  return 'Die Kamera konnte nicht starten. Bitte versuche es erneut.';
}

/** Owns the stream, including requests that resolve after stop or unmount. */
export function useCamera() {
  const [state, setState] = useState<CameraState>({ kind: 'off' });
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const requestRef = useRef(0);

  const stop = () => {
    requestRef.current += 1;
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setState({ kind: 'off' });
  };

  const start = async () => {
    stop();
    const request = requestRef.current;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setState({ kind: 'error', message: 'Die Kamera braucht HTTPS oder localhost. Öffne die sichere App-Adresse.' });
      return;
    }
    setState({ kind: 'requesting' });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      if (request !== requestRef.current) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      streamRef.current = stream;
      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        await video.play();
      }
      if (request !== requestRef.current) return;
      stream.getVideoTracks().forEach(track => track.addEventListener('ended', () => {
        if (streamRef.current !== stream) return;
        stream.getTracks().forEach(item => item.stop());
        streamRef.current = null;
        setState({ kind: 'error', message: 'Die Kamera wurde unterbrochen. Du kannst sie erneut starten.' });
      }, { once: true }));
      setState({ kind: 'live' });
    } catch (error) {
      if (request !== requestRef.current) return;
      streamRef.current?.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      setState({ kind: 'error', message: cameraError(error) });
    }
  };

  useEffect(() => () => {
    requestRef.current += 1;
    streamRef.current?.getTracks().forEach(track => track.stop());
  }, []);

  return { state, videoRef, start, stop };
}

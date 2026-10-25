import { useEffect, useRef, useState } from "react";

type CameraState = { kind: "off" } | { kind: "requesting" } | { kind: "live" } | { kind: "error"; message: string };

function cameraError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError") return "Camera access is blocked. Allow it in your browser's site settings.";
    if (error.name === "NotFoundError") return "No camera found. The map and directions still work.";
    if (error.name === "NotReadableError") return "Another app is using the camera. Close it and try again.";
  }
  return "The camera could not start. Please try again.";
}

/**
 * The device camera, rear-facing if possible. Owns the stream, including requests that resolve after stop or
 * unmount. Nothing is recorded here; `useLocalization` sends single frames to find the position.
 */
export function useCamera() {
  const [state, setState] = useState<CameraState>({ kind: "off" });
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const requestRef = useRef(0);

  const release = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const stop = () => {
    requestRef.current += 1;
    release();
    setState({ kind: "off" });
  };

  const start = async () => {
    stop();
    const request = requestRef.current;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setState({ kind: "error", message: "The camera needs HTTPS or localhost." });
      return;
    }
    setState({ kind: "requesting" });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      if (request !== requestRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      if (request !== requestRef.current) return;
      stream.getVideoTracks().forEach((track) =>
        track.addEventListener(
          "ended",
          () => {
            if (streamRef.current !== stream) return;
            release();
            setState({ kind: "error", message: "The camera stopped. You can start it again." });
          },
          { once: true },
        ),
      );
      setState({ kind: "live" });
    } catch (error) {
      if (request !== requestRef.current) return;
      release();
      setState({ kind: "error", message: cameraError(error) });
    }
  };

  useEffect(
    () => () => {
      requestRef.current += 1;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  return { state, videoRef, start, stop };
}

import { useEffect, useRef, useState, type RefObject } from "react";
import { captureFrame, postFrame, toFix, type Fix } from "./localize";

const INTERVAL_MS = 1000;

export type LocalizationStatus = "searching" | "located" | "unavailable";

/**
 * While `active`, send one camera frame about every second to the localization service, never more than one at
 * a time, and report reliable positions. Frames are not stored here or by the service. Stops for good when the
 * building has no map or the service is not available.
 */
export function useLocalization(
  buildingId: string,
  video: RefObject<HTMLVideoElement | null>,
  active: boolean,
  onFix: (fix: Fix) => void,
): LocalizationStatus {
  const [status, setStatus] = useState<LocalizationStatus>("searching");
  const onFixRef = useRef(onFix);
  onFixRef.current = onFix;
  const unavailable = status === "unavailable";

  useEffect(() => {
    if (!active || unavailable) return;
    const canvas = document.createElement("canvas");
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      const started = performance.now();
      try {
        const frame = !document.hidden && video.current ? await captureFrame(video.current, canvas) : null;
        if (frame) {
          const outcome = await postFrame(buildingId, frame, abort.signal);
          if (outcome.kind === "unavailable") return setStatus("unavailable");
          const fix = outcome.kind === "result" ? toFix(outcome.result) : undefined;
          if (fix) onFixRef.current(fix);
          setStatus(fix ? "located" : "searching");
        }
      } catch {
        if (abort.signal.aborted) return;
      }
      timer = setTimeout(() => void tick(), Math.max(0, INTERVAL_MS - (performance.now() - started)));
    };
    void tick();
    return () => {
      abort.abort();
      clearTimeout(timer);
    };
  }, [buildingId, active, unavailable]);

  return status;
}

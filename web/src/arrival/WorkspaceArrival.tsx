import { useEffect, useRef, useState } from "react";
import { arrivalBuildings } from "./catalogue";
import "./arrival.css";

const MAX_DURATION_MS = 3000;
const FADE_MS = 200;
let renderer: Promise<typeof import("./map")> | undefined;
function loadRenderer() {
  // Share an in-flight chunk across StrictMode effect replays and subsequent entrances.
  return renderer ??= import("./map").catch((error) => { renderer = undefined; throw error; });
}

/** A one-time Home → Workspace entrance. The normal workspace mounts underneath immediately. */
export function WorkspaceArrival({ buildingId }: { buildingId: string }) {
  const building = arrivalBuildings.find((candidate) => candidate.id === buildingId);
  const [visible, setVisible] = useState(() => !!building && history.state?.workspaceArrival === buildingId
    && !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [leaving, setLeaving] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Consume the entrance marker so reloads and Back/Forward open the usual workspace directly.
    if (history.state?.workspaceArrival === buildingId) {
      const { workspaceArrival: _, ...state } = history.state;
      history.replaceState(state, "");
    }
    if (!visible || !building || !container.current) return;
    const request = new AbortController();
    let fadeTimer: number | undefined;
    let finishing = false;
    const finish = () => {
      if (request.signal.aborted || finishing) return;
      finishing = true;
      setLeaving(true);
      fadeTimer = window.setTimeout(() => setVisible(false), FADE_MS);
    };
    // Includes chunk loading and map requests: a slow/unavailable map never holds up the workspace.
    const deadline = window.setTimeout(finish, MAX_DURATION_MS - FADE_MS);
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const motionChanged = () => { if (motion.matches) finish(); };
    motion.addEventListener("change", motionChanged);
    void loadRenderer().then(({ startArrival }) => {
      if (!request.signal.aborted && !finishing) startArrival(container.current!, building, finish, request.signal);
    }).catch(finish);
    return () => {
      request.abort();
      window.clearTimeout(deadline);
      window.clearTimeout(fadeTimer);
      motion.removeEventListener("change", motionChanged);
    };
  }, [building, buildingId, visible]);

  if (!visible) return null;
  return <div className="workspace-arrival" data-leaving={leaving} aria-label={`Arriving at ${building!.label}`}>
    <div ref={container} className="workspace-arrival-map" aria-hidden="true" />
    <div className="workspace-arrival-caption" role="status"><span>LOCORA</span><strong>{building!.label}</strong></div>
    <button className="workspace-arrival-skip" type="button" onClick={() => setVisible(false)}>Skip animation</button>
  </div>;
}

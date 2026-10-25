import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight, LoaderCircle } from "lucide-react";
import type { CampusBuilding } from "./geography";
import type { BuildingScene } from "@building/view";
import type { RoomPick } from "./map";
import { GoogleIndoorLayer } from "./GoogleIndoorLayer";
import { indoorCamera } from "./indoor-camera";
import { currentGoogle3d, exteriorCamera, isBuildingClick, loadGoogle3d, type ExteriorPose, type GoogleMapElement } from "./google3d";

export function GoogleExterior({ building, inside, scene, gap, floor, room, onRoom, onEnter, onCancel, replay, topDown }: {
  building: CampusBuilding; inside: boolean; scene?: BuildingScene; gap: number; floor: string|null; room?:RoomPick;
  onRoom: (room:RoomPick|undefined)=>void; onEnter: (pose: ExteriorPose) => void; onCancel: () => void;
  replay: number; topDown: number;
}) {
  const [sdk, setSdk] = useState(currentGoogle3d);
  const [status, setStatus] = useState<"key" | "loading" | "ready" | "error">(sdk ? "loading" : "key");
  const [message, setMessage] = useState("");
  const host = useRef<HTMLDivElement>(null);
  const keyInput = useRef<HTMLInputElement>(null);
  const mapRef = useRef<GoogleMapElement | null>(null);
  const [googleMap,setGoogleMap]=useState<GoogleMapElement|null>(null);
  const layerRef=useRef<GoogleIndoorLayer|null>(null);
  const [layer,setLayer]=useState<GoogleIndoorLayer|null>(null);
  const [layerError,setLayerError]=useState("");
  const latest = useRef({ building, onEnter, inside, gap, floor, room, onRoom });
  useEffect(() => { latest.current = { building, onEnter, inside, gap, floor, room, onRoom }; }, [building, onEnter, inside, gap, floor, room, onRoom]);
  // Recover the already-loaded public SDK after a development hot reload. No key is read or retained.
  useEffect(()=>{const available=currentGoogle3d();if(available && !sdk) setSdk(available);},[sdk]);

  useEffect(()=>{
    if (!sdk || !googleMap || !scene || !building.googleIndoorModel) return;
    const request=new AbortController();setLayerError("");
    void GoogleIndoorLayer.prepare(googleMap,sdk,building,scene,room=>latest.current.onRoom(room),request.signal).then(created=>{
      if (request.signal.aborted) {created.destroy();return;}
      layerRef.current=created;setLayer(created);
      if (latest.current.inside) created.show(latest.current.gap,latest.current.floor,latest.current.room?.id);
    }).catch(()=>{if (!request.signal.aborted) setLayerError("The floor model could not load. Google's building is still visible. Return to the exterior or use Campus.");});
    return ()=>{request.abort();layerRef.current?.destroy();layerRef.current=null;setLayer(null);};
  },[sdk,googleMap,building,scene]);

  useEffect(()=>{
    if (inside) layer?.show(gap,floor,room?.id); else layer?.hide();
  },[inside,layer,gap,floor,room?.id]);

  useEffect(() => {
    if (!sdk || !host.current) return;
    let map: GoogleMapElement;
    let alive = true;
    const failed = () => {
      if (!alive) return;
      setStatus("error"); setMessage("Google 3D is unavailable. Check the key, its quota and allowed websites, or use Campus.");
    };
    const timer = window.setTimeout(failed, 45000);
    try {
      const b = latest.current.building;
      map = new sdk.Map3DElement({ center: { lat: b.center[1], lng: b.center[0] }, range: exteriorCamera(b).range,
        tilt: 56, heading: 336, fov:35, mode: "HYBRID", description: `Photorealistic exterior of ${b.label}` });
      mapRef.current = map;
      setGoogleMap(map);
      const steady = (event: Event) => {
        if (alive && (event as Event & { isSteady?: boolean }).isSteady) {
          window.clearTimeout(timer); setStatus("ready"); setMessage("");

        }
      };
      const clicked = (event: Event) => {
        const position = (event as Event & { position?: { lat: number; lng: number } }).position;
        if (!latest.current.inside && isBuildingClick(latest.current.building, position)) {
          latest.current.onEnter({ heading: map.heading, tilt: map.tilt });
        }
      };
      map.addEventListener("gmp-steadychange", steady);
      map.addEventListener("gmp-error", failed);
      map.addEventListener("gmp-click", clicked);
      host.current.append(map);
      return () => {
        alive = false; window.clearTimeout(timer);
        map.removeEventListener("gmp-steadychange", steady); map.removeEventListener("gmp-error", failed);
        map.removeEventListener("gmp-click", clicked); map.remove(); mapRef.current = null;
      };
    } catch { failed(); window.clearTimeout(timer); }
    return () => { alive = false; window.clearTimeout(timer); };
  }, [sdk]);

  useEffect(() => {
    if (!googleMap || !host.current) return;
    // SATELLITE keeps the photographic 3D mesh while removing Google's road and POI labels.
    googleMap.mode=inside ? "SATELLITE" : "HYBRID";
    if (inside && (!scene || !layer)) return;
    const aspect=host.current.clientWidth/Math.max(1,host.current.clientHeight);
    const camera=inside && scene ? indoorCamera(building,scene,gap,floor,aspect,room?.id) : exteriorCamera(building,aspect);
    if (!camera) return;
    googleMap.stopCameraAnimation?.();
    googleMap.flyCameraTo({endCamera:camera,
      durationMillis:window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : room ? 750 : 1100});
  }, [googleMap,building,inside,scene,layer,gap,floor,room?.id,replay]);

  useEffect(() => { if (mapRef.current && topDown > 0) mapRef.current.tilt = mapRef.current.tilt > 20 ? 0 : 56; }, [topDown]);

  const connect = async (event: FormEvent) => {
    event.preventDefault();
    const key = keyInput.current?.value.trim() ?? "";
    if (!/^AIza[\w-]{30,60}$/.test(key)) { setMessage("Enter a valid Google Maps browser key or Demo Key."); return; }
    keyInput.current!.value = "";
    setStatus("loading"); setMessage("");
    try { setSdk(await loadGoogle3d(key)); }
    catch { setStatus("key"); setMessage("Google could not load. Check your connection and key, then try again."); }
  };

  return <div className="explore-google" aria-label="Photorealistic campus and floor model">
    <div className="explore-google-map" ref={host} />
    {status === "key" && <div className="explore-google-setup"><form onSubmit={(event) => void connect(event)} autoComplete="off">
      <span className="explore-eyebrow">GOOGLE 3D · THIS TAB ONLY</span>
      <h2>A real-world view of your building.</h2>
      <p>Connect your Google Maps Demo Key to explore the photographic exterior. Click your building to open its floors.</p>
      <label htmlFor="google-map-key">Google Maps key<input ref={keyInput} id="google-map-key" type="password" autoComplete="off" spellCheck={false} required placeholder="Paste your Demo Key" /></label>
      {message && <p role="alert">{message}</p>}
      <button className="explore-primary" type="submit">Open Google 3D<ArrowRight size={16} /></button>
      <small>Used only in this tab and sent to Google. Never saved to files or browser storage.</small>
      <button className="explore-google-cancel" type="button" onClick={onCancel}>Back to Campus</button>
    </form></div>}
    {status === "loading" && <div className="explore-google-status" role="status"><LoaderCircle className="explore-spin" size={17} />Loading photographic 3D…</div>}
    {status === "ready" && !inside && <div className="explore-google-hint">Click {building.label} to open {building.localFrame ? "its floors" : "the workspace"}</div>}
    {inside && scene && !layer && !layerError && <div className="explore-google-status" role="status"><LoaderCircle className="explore-spin" size={17}/>Loading your floors into Google 3D…</div>}
    {inside && layerError && <div className="explore-google-status" role="alert">{layerError}</div>}
    {status === "error" && <div className="explore-google-status" role="alert">{message}<button onClick={onCancel}>Use Campus</button></div>}
  </div>;
}

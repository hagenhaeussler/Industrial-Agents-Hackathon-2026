import { ArrowLeft, ArrowRight, ArrowUpRight, Box, Building2, ChevronDown, Globe2, Layers3, LoaderCircle,
  Map as MapIcon, Navigation, RotateCcw, Search, Satellite, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBuilding } from "../api/buildings";
import { navigate } from "../router";
import { aerialPreview, levelName, type CampusBuilding, type CampusCatalog } from "./geography";
import { CampusMap, type JourneyStage, type RoomPick } from "./map";
import type { ExteriorPose } from "./google3d";
import "maplibre-gl/dist/maplibre-gl.css";
import "./explore.css";

const GoogleExterior = lazy(() => import("./GoogleExterior").then((module) => ({ default: module.GoogleExterior })));

export function CampusExplorer() {
  const catalog = useQuery({ queryKey: ["campus-catalog"], staleTime: Infinity, queryFn: async ({ signal }) => {
    const response = await fetch("/maps/buildings.json", { signal });
    if (!response.ok) throw new Error("The building catalogue could not be loaded.");
    return response.json() as Promise<CampusCatalog>;
  } });
  if (catalog.isPending) return <main className="explorer-loading"><Box size={30} /><p>Opening your world…</p></main>;
  if (catalog.isError) return <main className="explorer-loading"><p>{catalog.error.message}</p>
    <button className="explore-primary" onClick={() => void catalog.refetch()}>Try again</button>
    <a href="/buildings">Open building list</a></main>;
  return <Explorer catalog={catalog.data} />;
}

function Explorer({ catalog }: { catalog: CampusCatalog }) {
  const initial = catalog.buildings.find((b) => b.id === new URLSearchParams(location.search).get("building"))
    ?? catalog.buildings.find((b) => b.id === catalog.featuredBuildingId) ?? catalog.buildings[0]!;
  const [selected, setSelected] = useState(initial);
  const [search, setSearch] = useState("");
  const [roomSearch,setRoomSearch]=useState("");
  const [stage, setStage] = useState<JourneyStage>("globe");
  const [ready, setReady] = useState(false);
  const [retry, setRetry] = useState(0);
  const [aerial, setAerial] = useState(false);
  const [photographic, setPhotographic] = useState(()=>new URLSearchParams(location.search).get("map")==="photo");
  const [photoReplay, setPhotoReplay] = useState(0);
  const [photoTopDown, setPhotoTopDown] = useState(0);
  const [notice, setNotice] = useState("");
  const [inside, setInside] = useState(false);
  const [floor, setFloor] = useState<string | null>(null);
  const [gap, setGap] = useState(8);
  const [room, setRoom] = useState<RoomPick>();
  const [pickerOpen, setPickerOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const controller = useRef<CampusMap | null>(null);
  const document = useBuilding(selected.id, inside && !!selected.localFrame);
  const flying = stage === "flying" || stage === "arriving";

  const choose = useCallback((building: CampusBuilding) => {
    setSelected(building); setInside(false); setFloor(null); setRoom(undefined); setPickerOpen(false); setNotice("");
    const url = new URL(location.href); url.searchParams.set("building", building.id);
    history.replaceState(null, "", url.pathname + url.search);
    void controller.current?.flyTo(building);
  }, []);

  useEffect(() => {
    setReady(false); setNotice("");
    try {
      const created = new CampusMap(container.current!, catalog, {
        onStage: setStage,
        onSelect: (id) => { const building = catalog.buildings.find((b) => b.id === id); if (building) choose(building); },
        onRoom: setRoom,
        onError: (message) => { setNotice(message); setAerial(false); },
        onReady: () => {
          setReady(true);
          created.setSelected(initial);
          if (new URLSearchParams(location.search).has("building")) void created.flyTo(initial);
        },
      });
      controller.current = created;
      return () => { controller.current = null; created.destroy(); };
    } catch {
      setNotice("This device could not start the 3D map. You can still open the workspace or the building list.");
    }
  }, [catalog, choose, retry]);

  useEffect(() => {
    if (inside && !photographic && document.data && selected.localFrame && ready) {
      controller.current?.showIndoor(document.data.scene, selected, gap, floor);
    }
  }, [inside, photographic, document.data, selected, gap, floor, ready]);

  const shown = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    return [...catalog.buildings]
      .sort((a, b) => Number(b.id === catalog.featuredBuildingId) - Number(a.id === catalog.featuredBuildingId) || a.label.localeCompare(b.label))
      .filter((b) => `${b.label} ${b.name} ${b.address ?? ""} ${b.city ?? ""}`.toLocaleLowerCase().includes(term));
  }, [catalog, search]);

  const shownRooms=useMemo(()=>{
    const term=roomSearch.trim().toLocaleLowerCase();
    return document.data?.scene.floors.filter(f=>!floor || f.id===floor).flatMap(f=>f.spaces
      .filter(s=>s.type==="room" && `${s.name} ${s.ref}`.toLocaleLowerCase().includes(term))
      .map(s=>({id:s.id,name:s.name,ref:s.ref,floorId:f.id,level:f.level}))) ?? [];
  },[document.data,floor,roomSearch]);

  const goInside = (pose?: ExteriorPose) => {
    if (inside) return;
    if (!selected.localFrame) return navigate(`/admin/${encodeURIComponent(selected.id)}`);
    if (!photographic) controller.current?.focusForIndoor(pose);
    if (photographic && !selected.googleIndoorModel) {
      setPhotographic(false);controller.current?.focusForIndoor(pose);
      setNotice("This building has no Google floor model yet. Opening its campus floor model.");
    }
    setInside(true); setRoom(undefined);setRoomSearch("");
  };
  const exterior = () => { setInside(false); setRoom(undefined); controller.current?.showExterior(); };
  const mode = (next: boolean) => { setPhotographic(false); setAerial(next); controller.current?.setAerial(next); };
  const photoMode = () => {
    setPhotographic(true); exterior();
    if (stage === "globe") choose(selected);
  };
  const photoVisible = photographic && !flying && stage !== "globe";
  const roomMode=inside && photographic;
  const pickGoogleRoom=useCallback((picked:RoomPick|undefined)=>{
    setRoom(picked);
    if (picked) setFloor(picked.floorId);
  },[]);
  const primaryLabel = flying ? "On our way…" : stage === "globe" ? "Explore building" : inside ? "Open workspace" : selected.localFrame ? "Go inside" : "Open workspace";

  return <main className="campus-explorer">
    <header className="explore-header">
      <a className="explore-brand" href="/" aria-label="Talk to your building home"><Box size={31} strokeWidth={1.5} /><span>Talk to your building</span></a>
      <nav aria-label="Main navigation"><a className="active" href="/" aria-current="page">Explore</a>
        <a href={`/admin/${encodeURIComponent(selected.id)}`}>Workspace <ArrowUpRight size={13} /></a></nav>
      <a className="explore-library" href="/buildings"><Building2 size={16} /><span>All buildings</span></a>
    </header>
    <div className="explore-body">
      <aside className={`explore-rail ${roomMode ? "is-inside" : ""} ${pickerOpen ? "picker-open" : ""}`} aria-label={roomMode ? "Room explorer" : "Building explorer"}>
        <div className="explore-search-block">
          <button className="mobile-picker-toggle" onClick={() => setPickerOpen((open) => !open)} aria-expanded={pickerOpen}>
            <span>{selected.label}</span><ChevronDown size={18} /></button>
          <div className="explore-rail-title"><h1>{roomMode ? "Explore your rooms" : "Explore your buildings"}</h1><span>{roomMode ? shownRooms.length : catalog.buildings.length}</span></div>
          <label className="explore-search"><Search size={18} /><input placeholder={roomMode ? "Find a room by name or number" : "Search buildings or places"} aria-label={roomMode ? "Search rooms" : "Search buildings or places"}
            value={roomMode ? roomSearch : search} onChange={(event) => roomMode ? setRoomSearch(event.target.value) : setSearch(event.target.value)} />
            {(roomMode ? roomSearch : search) && <button aria-label="Clear search" onClick={() => roomMode ? setRoomSearch("") : setSearch("")}><X size={15} /></button>}</label>
        </div>
        {roomMode ? <div className="explore-list" aria-label="Rooms">
          <p className="explore-room-instruction">{floor ? "Choose a room to take a closer look." : "Choose a level, or find a room to fly inside."}</p>
          {shownRooms.slice(0,100).map(picked=><button key={picked.id} className={`explore-building-row explore-room-row ${room?.id===picked.id ? "selected" : ""}`}
            aria-pressed={room?.id===picked.id} onClick={()=>pickGoogleRoom(picked)}>
            <span className="explore-room-glyph"><Box size={19}/></span><span><strong>{picked.name || picked.ref || "Room"}</strong><small>{levelName(picked.level)} · {picked.ref}</small></span><ArrowRight size={16}/>
          </button>)}
          {shownRooms.length>100 && <p className="explore-no-results">Showing 100 of {shownRooms.length} rooms. Choose a level or search by number.</p>}
          {!shownRooms.length && !document.isPending && <p className="explore-no-results">No rooms match this selection.</p>}
        </div> : <div className="explore-list" aria-label="Mapped buildings">
          {shown.map((building) => <button key={building.id} className={`explore-building-row ${selected.id === building.id ? "selected" : ""}`}
            aria-pressed={selected.id === building.id} onClick={() => choose(building)} disabled={!ready}>
            <AerialImage building={building} className="explore-thumbnail" />
            <span><strong>{building.label}</strong><small>{building.city ?? "Bavaria"} · {building.floors} levels</small></span>
            <ArrowRight size={16} /></button>)}
          {shown.length === 0 && <p className="explore-no-results">No buildings match “{search}”. Try a name, street or city.</p>}
        </div>}
        <section className="explore-building-detail" aria-label="Selected building">
          <div className="explore-cover"><AerialImage building={selected} className="explore-cover-image" />
            <span><Navigation size={13} /> Real location</span></div>
          <h2>{selected.label}</h2>
          <p className="explore-address">{selected.address ?? selected.city ?? "Location from OpenStreetMap"}{selected.address && selected.city ? `, ${selected.city}` : ""}</p>
          <p className="explore-counts"><Layers3 size={14} /> {selected.floors} levels <span>·</span> {selected.rooms.toLocaleString("en")} rooms</p>
          <button className="explore-primary" disabled={!ready || flying || (inside && document.isPending)}
            onClick={() => stage === "globe" ? choose(selected) : inside ? navigate(`/admin/${encodeURIComponent(selected.id)}`) : goInside()}>
            {flying || (inside && document.isPending) ? <LoaderCircle className="explore-spin" size={17} /> : null}
            {inside && document.isPending ? "Loading indoor plan…" : primaryLabel}<ArrowRight size={17} /></button>
          <a className="explore-workspace-link" href={`/admin/${encodeURIComponent(selected.id)}`}><ArrowUpRight size={16} /> Open workspace</a>
        </section>
        <footer className="explore-rail-footer"><a href="https://www.geodaten.bayern.de/" target="_blank" rel="noreferrer">Aerial imagery © Bayerische Vermessungsverwaltung</a>
          <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a></footer>
      </aside>
      <section className="explore-canvas" aria-label="Interactive campus map">
        <div className="explore-map" ref={container} />
        {photographic && !flying && stage !== "globe" && <Suspense fallback={<div className="explore-map-loading">Opening Google 3D…</div>}>
          <GoogleExterior building={selected} inside={inside} scene={document.data?.scene} gap={gap} floor={floor} room={room}
            onRoom={pickGoogleRoom} onEnter={goInside} onCancel={() => mode(false)}
            replay={photoReplay} topDown={photoTopDown} />
        </Suspense>}
        <div className="explore-map-top">
          <div className="explore-location"><span className="explore-dot" />{stage === "globe" ? "Your buildings, on Earth" : flying ? stage === "arriving" ? "Arriving at your building" : "Flying to your building" : selected.city ?? "Campus view"}</div>
          <div className="explore-mode" role="group" aria-label="Map appearance"><button aria-pressed={!aerial && !photographic} onClick={() => mode(false)}><MapIcon size={15} />Campus</button>
            <button aria-pressed={aerial && !photographic} onClick={() => mode(true)}><Satellite size={15} />Aerial</button>
            <button aria-pressed={photographic} onClick={photoMode}><Box size={15} />3D Photo</button></div>
        </div>
        {!ready && !notice && <div className="explore-map-loading"><LoaderCircle size={22} className="explore-spin" /><span>Loading the map…</span></div>}
        {stage === "globe" && ready && <div className="explore-globe-prompt"><Globe2 size={22} /><div><strong>A world of buildings.</strong><span>Choose a place. We’ll take you there.</span></div>
          <button onClick={() => choose(selected)} aria-label={`Fly to ${selected.label}`}><ArrowRight size={20} /></button></div>}
        {flying && <div className="explore-journey" role="status"><span className="explore-journey-track"><i /></span><strong>{selected.label}</strong><span>{selected.address ?? "Following the map to your building"}</span></div>}
        {notice && <div className="explore-notice" role="alert"><span>{notice}</span>{!ready && <button onClick={() => setRetry((value) => value + 1)}>Retry</button>}
          <button onClick={() => setNotice("")} aria-label="Dismiss notice"><X size={16} /></button></div>}
        {inside && document.isError && <div className="explore-notice" role="alert"><span>The indoor plan could not load. {document.error.message}</span>
          <button onClick={() => void document.refetch()}>Retry</button><button onClick={exterior}>Back to campus</button></div>}
        {inside && document.data && <>
          <div className="explore-floor-panel" aria-label="Floor selection"><span>LEVELS</span>
            <button aria-pressed={floor === null} onClick={() => { setFloor(null); setRoom(undefined);setRoomSearch(""); }}>All</button>
            {[...document.data.scene.floors].reverse().map((f) => <button key={f.id} aria-pressed={floor === f.id}
              onClick={() => { setFloor(f.id); setRoom(undefined);setRoomSearch(""); }} aria-label={`Show ${levelName(f.level)}`}>{f.level === 0 ? "G" : f.level < 0 ? `B${-f.level}` : f.level}</button>)}</div>
          <div className="explore-indoor-toolbar"><button onClick={exterior}><ArrowLeft size={15} />{photographic ? "Back to 3D" : "Campus"}</button><span className="explore-toolbar-divider" />
            <label>Separate floors <input type="range" min="0" max="12" step="1" value={gap} onChange={(event) => setGap(Number(event.target.value))} /><output>{gap} m</output></label></div>
        </>}
        {room && <div className="explore-room-card"><button className="explore-room-close" aria-label="Close room details" onClick={() => setRoom(undefined)}><X size={16} /></button>
          <span>{levelName(room.level)}</span><strong>{room.name}</strong><small>Room {room.ref}</small>
          <a href={`/admin/${encodeURIComponent(selected.id)}`}>Explore in workspace <ArrowUpRight size={14} /></a></div>}
        <div className="explore-view-tools"><button onClick={() => { setInside(false); controller.current?.globe(); }} disabled={!ready} title="Globe overview" aria-label="Globe overview"><Globe2 size={19} /></button>
          <button onClick={() => photoVisible ? setPhotoReplay((value) => value + 1) : choose(selected)} disabled={!ready} title={inside && photoVisible ? "Refocus floors" : "Replay arrival"} aria-label={inside && photoVisible ? "Refocus floors" : "Replay arrival"}><RotateCcw size={18} /></button>
          <button onClick={() => photoVisible ? setPhotoTopDown((value) => value + 1) : controller.current?.topDown()} disabled={!ready} title="Toggle top-down view" aria-label="Toggle top-down view"><Layers3 size={19} /></button></div>
        {stage !== "globe" && !flying && <div className="explore-map-caption"><Navigation size={14} /><span>{inside ? "Inside your building" : selected.label}</span>
          <a href={selected.osmUrl} target="_blank" rel="noreferrer" aria-label="View building in OpenStreetMap"><ArrowUpRight size={14} /></a></div>}
      </section>
    </div>
  </main>;
}

function AerialImage({ building, className }: { building: CampusBuilding; className: string }) {
  const [failedUrl, setFailedUrl] = useState("");
  const url = aerialPreview(building);
  return failedUrl === url ? <span className={`${className} explore-image-fallback`}><Building2 size={24} /></span>
    : <img className={className} src={url} alt={`Aerial view of ${building.label}`} loading="lazy" onError={() => setFailedUrl(url)} />;
}

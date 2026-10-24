import { ArrowRight, Camera, CameraOff, Check, ChevronRight, MapPin, RotateCcw, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { Agent } from '../agent/Agent';
import { DemoScene } from '../camera/DemoScene';
import { useCamera } from '../camera/useCamera';
import { FloorMap, RouteBanner, RouteOverlay, TurnIcon } from '../navigation/Navigation';
import { advanceStep, destinations, getStep, initialDestination } from '../navigation/routes';
import type { Destination } from '../navigation/routes';

/** The prototype phone guide on demo routes; replaced by the live tour journey in C02. */
export function Guide() {
  const camera = useCamera();
  const [destination, setDestination] = useState(initialDestination);
  const [stepIndex, setStepIndex] = useState(0);
  const routeDialog = useRef<HTMLDialogElement>(null);
  const step = getStep(destination, stepIndex);
  const live = camera.state.kind === 'live';
  const requesting = camera.state.kind === 'requesting';

  const selectDestination = (next: Destination) => { setDestination(next); setStepIndex(0); };
  const nextStep = () => { setStepIndex(current => advanceStep(destination, current)); routeDialog.current?.close(); };

  return <main className={`app ${live ? 'camera-live' : 'camera-demo'}`}>
    <div className="camera-layer"><DemoScene/><video ref={camera.videoRef} className={live ? 'camera-video visible' : 'camera-video'} autoPlay playsInline muted aria-hidden={!live} aria-label="Live camera view of your surroundings"/></div>
    <div className="camera-shade" aria-hidden="true"/>
    <RouteOverlay step={step}/>

    <div className="top-ui"><RouteBanner destination={destination} step={step} onOpen={() => routeDialog.current?.showModal()}/>
      <div className="under-route"><button className={`camera-toggle surface ${live ? 'is-live' : 'is-off'}`} onClick={() => live || requesting ? camera.stop() : void camera.start()} aria-label={requesting ? 'Cancel camera request' : live ? 'Turn camera off' : 'Turn camera on'} title={requesting ? 'Cancel camera request' : live ? 'Turn camera off' : 'Turn camera on'} aria-pressed={live}>{live ? <Camera size={20}/> : <CameraOff size={20}/>}</button>
        <FloorMap step={step} destination={destination} onOpen={() => routeDialog.current?.showModal()}/>
      </div>
    </div>

    {camera.state.kind === 'error' && <div className="camera-error surface" role="alert"><p>{camera.state.message}</p><button onClick={camera.stop}>Close</button></div>}

    <Agent arrived={step.turn === 'arrived'} onDestination={selectDestination}/>

    <dialog ref={routeDialog} className="sheet route-sheet" aria-labelledby="route-title"><div className="sheet-handle"/><header className="sheet-header"><div><h2 id="route-title">Where to?</h2><p>Ground floor</p></div><button className="icon-button" onClick={() => routeDialog.current?.close()} aria-label="Close route"><X size={22}/></button></header>
      <div className="destination-list">{destinations.map(item => <button key={item.id} className={`destination-option ${destination.id === item.id ? 'selected' : ''}`} onClick={() => selectDestination(item)}><span className="destination-icon"><MapPin size={21}/></span><span><strong>{item.name}</strong><span>{item.room} · Ground floor</span></span>{destination.id === item.id ? <Check size={20}/> : <ChevronRight size={20}/>}</button>)}</div>
      <div className="route-steps"><h3>Your route</h3><ol>{destination.steps.map((item, index) => <li className={index === stepIndex ? 'current' : ''} key={item.instruction}><span className="step-symbol">{index < stepIndex ? <Check size={18}/> : <TurnIcon turn={item.turn} size={18}/>}</span><span><strong>{item.instruction}</strong><span>{item.detail}</span></span><span className="step-meters">{item.meters} m</span></li>)}</ol></div>
      <p className="demo-explanation">Example data. Location detection is not connected yet.</p><footer className="route-actions"><button className="icon-button" onClick={() => setStepIndex(0)} aria-label="Restart route"><RotateCcw size={20}/></button><button className="primary-button" onClick={nextStep} disabled={step.turn === 'arrived'}>{step.turn === 'arrived' ? 'Arrived' : 'Next step'}<ArrowRight size={18}/></button></footer>
    </dialog>
  </main>;
}

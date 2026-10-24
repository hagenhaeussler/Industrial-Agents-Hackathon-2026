import { ArrowLeft, Route } from 'lucide-react';
import type { ReachableRoute } from '../api/types';
import { floorName, spaceName } from './model';
import type { Model } from './model';

/** A separately requested route can be inspected without changing collection progress or position. */
export function RoutePreview({ route, model, onClose, collection = false }: { route: ReachableRoute; model: Model; onClose: () => void; collection?: boolean }) {
  return <section className="route-preview surface" aria-label="Requested route">
    <p className="policy"><Route size={16} aria-hidden="true"/>Requested route · {Math.round(route.length_m)} m{route.constraints.step_free ? ' · step-free' : ''}</p>
    <h2>{spaceName(model, route.from_space_id)} → {spaceName(model, route.to_space_id)}</h2>
    {route.geometry === 'provisional' && <p className="fineprint">Provisional route: straight segments are shown until computed walk geometry is available.</p>}
    <details><summary>Directions</summary><ol>{route.maneuvers.map((maneuver, index) => <li key={`${maneuver.i}:${index}`}>{maneuver.text}<span className="muted"> · {floorName(model, maneuver.floor_id)}</span></li>)}</ol></details>
    <p className="fineprint">This preview does not change your position{collection ? ' or collection progress' : ''}.</p>
    <button className="secondary-button" onClick={onClose}><ArrowLeft size={16}/>{collection ? 'Back to collection tour' : 'Back to building'}</button>
  </section>;
}

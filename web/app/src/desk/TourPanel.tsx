import { ArrowLeft, Smartphone, TriangleAlert, X } from 'lucide-react';
import type { Tour, UnreachableReason } from '../api/types';
import { displayOrder, isProvisional, spaceName } from '../map/model';
import type { Model } from '../map/model';
import { TracePanel } from '../trace/TracePanel';

export const policyLabel = (tour: Tour) => tour.order_policy === 'optimized_exact' ? 'Optimal order' : tour.order_policy === 'optimized_heuristic' ? 'Good order · heuristic' : 'Your order';

export const reasonText: Record<UnreachableReason, string> = {
  no_step_free_path: 'no step-free way there',
  blocked_by_closure: 'blocked by a closure',
  too_narrow: 'the doors are too narrow',
  disconnected: 'not connected to the rest of the building',
};

const metres = (m: number) => `${Math.round(m)} m`;

type Props = { model: Model; tour: Tour; plannedMs: number | null; onHandoff: () => void; onEdit: () => void; onFocusStop: (spaceId: string, floorId: string) => void; onRemoveStop?: (assetIds: string[]) => void; busy?: boolean };

export function TourPanel({ model, tour, plannedMs, onHandoff, onEdit, onFocusStop, onRemoveStop, busy }: Props) {
  const stops = new Map(tour.stops.map(stop => [stop.stop_id, stop]));
  const legTo = new Map(tour.legs.map(leg => [leg.to_space_id, leg]));
  const provisional = isProvisional(tour);
  return <section className="tour-panel" aria-labelledby="tour-title">
    <div className="tour-head">
      <div>
        <p className="policy">{policyLabel(tour)}</p>
        <h2 id="tour-title" tabIndex={-1}>{tour.stops.length} {tour.stops.length === 1 ? 'stop' : 'stops'} · {metres(tour.length_m)}</h2>
        <p className="muted">From {spaceName(model, tour.start.space_id)}{tour.end ? (tour.end.space_id === tour.start.space_id ? ' and back' : ` to ${spaceName(model, tour.end.space_id)}`) : ''}{tour.constraints.step_free ? ' · step-free' : ''}{plannedMs !== null ? ` · planned in ${plannedMs < 1000 ? `${Math.max(1, Math.round(plannedMs))} ms` : `${(plannedMs / 1000).toFixed(1)} s`}` : ''}</p>
      </div>
    </div>
    <ol className="stop-list">
      {displayOrder(tour).map((stopId, index) => {
        const stop = stops.get(stopId);
        if (!stop) return null;
        const leg = legTo.get(stop.space_id);
        const floorId = model.space.get(stop.space_id)?.floor_id ?? '';
        return <li key={stopId} className={`${stop.status} ${onRemoveStop ? 'removable' : ''}`}>
          <button onClick={() => onFocusStop(stop.space_id, floorId)} aria-label={`Stop ${index + 1}: ${stop.label}`}>
            <span className="stop-n" aria-hidden="true">{stop.status === 'collected' ? '✓' : index + 1}</span>
            <span className="stop-copy"><strong>{stop.label.split(' · ')[0]}</strong><span>{stop.label.split(' · ').slice(1).join(' · ') || spaceName(model, stop.space_id)} · {model.floor.get(floorId)?.name}</span></span>
            {leg?.reachable && <span className="stop-m">{metres(leg.length_m)}</span>}
          </button>
          {onRemoveStop && tour.stops.length > 1 && <button className="stop-remove" disabled={busy} onClick={() => onRemoveStop(stop.asset_ids)} aria-label={`Remove ${stop.label.split(' · ')[0]} and plan again`}><X size={16}/></button>}
        </li>;
      })}
    </ol>
    {tour.end && (() => {
      const last = tour.legs.find(leg => leg.to_space_id === tour.end!.space_id);
      return <p className="finish-line"><span className="stop-n finish" aria-hidden="true">⚑</span><span className="stop-copy"><strong>Finish: {spaceName(model, tour.end.space_id)}</strong><span>{model.floor.get(tour.end.floor_id)?.name}</span></span>{last?.reachable && <span className="stop-m">{metres(last.length_m)}</span>}</p>;
    })()}
    {tour.unreachable_stops.length > 0 && <div className="unreachable" role="status">
      <TriangleAlert size={18} aria-hidden="true"/>
      <div><strong>Not included</strong>{tour.unreachable_stops.map(item => <p key={item.stop_id}>{item.stop_id === 'end' ? 'Finish point' : stops.get(item.stop_id)?.label ?? item.stop_id}: {reasonText[item.reason as UnreachableReason] ?? item.reason}</p>)}</div>
    </div>}
    {provisional && <p className="fineprint">Route lines are provisional straight segments until the core publishes walk polylines.</p>}
    <TracePanel model={model} tour={tour}/>
    <div className="tour-actions">
      <button className="secondary-button" onClick={onEdit}><ArrowLeft size={17}/>Change parts</button>
      <button className="primary-button" onClick={onHandoff}><Smartphone size={18}/>Send to phone</button>
    </div>
  </section>;
}

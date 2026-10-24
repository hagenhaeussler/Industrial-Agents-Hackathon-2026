import { Calculator } from 'lucide-react';
import type { ToolResponse, Tour } from '../api/types';
import { spaceName } from '../map/model';
import type { Model } from '../map/model';

const PROFILE: Record<string, string> = {
  kit_1_1_0: 'Kit route model 1.1.0: door-to-door walks inside each room, stairs count 2 m per metre of height, a lift ride counts 15 m plus 1 m per metre. The same rules score the benchmark.',
};
const POLICY: Record<string, string> = {
  optimized_exact: 'Order: the shortest total over every possible order of the pending stops (exact, up to 12 stops).',
  optimized_heuristic: 'Order: good, not proven optimal (nearest neighbour plus 2-opt; used above 12 stops).',
  fixed: 'Order: kept exactly as you chose it.',
};

/** "How I calculated this": the language layer interprets, the rules decide. Everything here comes from the server's result. */
export function TracePanel({ model, tour, responses = [] }: { model: Model; tour?: Tour | null; responses?: ToolResponse[] }) {
  const traced = responses.filter(response => response.trace?.length);
  if (!tour && !traced.length) return null;
  const constraints = tour?.constraints;
  return <details className="trace-panel">
    <summary><Calculator size={16} aria-hidden="true"/>How I calculated this</summary>
    <div className="trace-body">
      {tour && <>
        <p>{PROFILE[tour.profile] ?? `Route model: ${tour.profile}.`}</p>
        <p>{POLICY[tour.order_policy] ?? `Order: ${tour.order_policy}.`}</p>
        {constraints && <p>Constraints: {constraints.step_free ? 'step-free only' : 'stairs allowed'}{constraints.min_door_width_m ? `, doors at least ${constraints.min_door_width_m} m wide` : ''}{constraints.closed.length ? `, ${constraints.closed.length} closed ${constraints.closed.length === 1 ? 'element' : 'elements'} avoided` : ''}.</p>}
        <ol className="trace-legs">
          {tour.legs.map((leg, index) => <li key={index}>
            <strong>{spaceName(model, leg.from_space_id)} → {spaceName(model, leg.to_space_id)}</strong>
            {leg.reachable
              ? <span>{leg.length_m.toFixed(1)} m · {leg.space_path.length} rooms · {leg.element_path.length} doors, stairs or lifts</span>
              : <span>No route: {leg.reason.replace(/_/g, ' ')}</span>}
          </li>)}
        </ol>
        <p className="fineprint">Building version {tour.building_version} · tour revision {tour.revision}{tour.changed_because ? ` · replanned after “${tour.changed_because.summary}”` : ''}</p>
      </>}
      {traced.map(response => <div key={response.request_id} className="trace-calls">
        <p><strong>{response.tool}</strong> · request {response.request_id}</p>
        <ol>{response.trace!.map((step, index) => <li key={index}><code>{step.fn}</code> {Object.entries(step.args).filter(([key]) => !key.startsWith('_')).slice(0, 3).map(([key, value]) => `${key}=${typeof value === 'string' ? value : JSON.stringify(value)}`).join(', ')} <span>{step.ms} ms</span></li>)}</ol>
      </div>)}
    </div>
  </details>;
}

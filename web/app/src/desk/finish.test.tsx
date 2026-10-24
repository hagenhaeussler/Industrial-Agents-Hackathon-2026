import { describe, expect, test } from 'bun:test';
import { renderToStaticMarkup } from 'react-dom/server';
import type { Snapshot, Tour } from '../api/types';
import { buildModel } from '../map/model';
import snapshot from '../mocks/data/building_proc-factory-dev-003.json';
import payloads from '../phone/fixtures/final-destination-c7.json';
import { TourPanel } from './TourPanel';

const model = buildModel(snapshot as unknown as Snapshot);
const render = (tour: Tour) => renderToStaticMarkup(<TourPanel model={model} tour={tour} plannedMs={null} onHandoff={() => undefined} onEdit={() => undefined} onFocusStop={() => undefined}/>);
const finish = (html: string) => /<p class="finish-line">(.*?)<\/p>/.exec(html)?.[1] ?? '';

describe('desk final destination summary', () => {
  test('uses the final edge when a part and the finish share a room', () => {
    const tour = structuredClone(payloads.before) as unknown as Tour;
    const first = tour.legs[0]!;
    if (!first.reachable) throw new Error('Fixture needs a reachable first leg');
    first.to_space_id = tour.end!.space_id; first.length_m = 91;
    const last = tour.legs[tour.legs.length - 1]!;
    if (!last.reachable) throw new Error('Fixture needs a reachable final leg');
    last.length_m = 17;
    const line = finish(render(tour));
    expect(line).toContain('Finish:');
    expect(line).toContain('17 m');
    expect(line).not.toContain('91 m');
  });
  test('does not show a distance for an unreachable finish', () => {
    const tour = payloads.blockedEnd as unknown as Tour;
    const html = render(tour);
    expect(finish(html)).toContain('Finish:');
    expect(finish(html)).not.toContain('stop-m');
    expect(html).toContain('Finish point');
    expect(html).toContain('blocked by a closure');
  });
});

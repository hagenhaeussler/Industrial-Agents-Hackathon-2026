import { describe, expect, test } from 'bun:test';
import { renderToStaticMarkup } from 'react-dom/server';
import type { Snapshot, Tour } from '../api/types';
import { buildModel } from '../map/model';
import snapshot from '../mocks/data/building_proc-factory-dev-003.json';
import blockedEndJson from '../mocks/data/tour_c7_blocked_end.json';
import tourJson from '../mocks/data/tour_proc-factory-dev-003.json';
import { TourPanel } from './TourPanel';

// adapted from Hagen's codex's test (e384c73) to the real fixtures on this branch
const model = buildModel(snapshot as unknown as Snapshot);
const render = (tour: Tour) => renderToStaticMarkup(<TourPanel model={model} tour={tour} plannedMs={null} onHandoff={() => undefined} onEdit={() => undefined} onFocusStop={() => undefined}/>);
const finishLine = (html: string) => /<p class="finish-line">(.*?)<\/p>/.exec(html)?.[1] ?? '';
const stopList = (html: string) => /<ol class="stop-list">(.*?)<\/ol>/.exec(html)?.[1] ?? '';

describe('desk final destination summary', () => {
  test('a part in the finish room keeps its own leg; the finish shows the final leg', () => {
    const tour = structuredClone(tourJson) as unknown as Tour;
    const first = tour.legs[0]!, finalLeg = structuredClone(tour.legs[0]!);
    if (!first.reachable || !finalLeg.reachable) throw new Error('fixture needs reachable legs');
    tour.end = { ...tour.start, space_id: first.to_space_id };
    first.length_m = 91;
    finalLeg.from_space_id = tour.legs[tour.legs.length - 1]!.to_space_id; finalLeg.to_space_id = first.to_space_id; finalLeg.length_m = 17;
    tour.legs.push(finalLeg);
    const html = render(tour);
    expect(stopList(html)).toContain('91 m');
    expect(stopList(html)).not.toContain('17 m');
    expect(finishLine(html)).toContain('Finish:');
    expect(finishLine(html)).toContain('17 m');
    expect(finishLine(html)).not.toContain('91 m');
  });
  test('an unreachable finish shows no distance and says why', () => {
    const html = render(blockedEndJson as unknown as Tour);
    expect(finishLine(html)).toContain('Finish:');
    expect(finishLine(html)).not.toContain('stop-m');
    expect(html).toContain('Finish point');
    expect(html).toContain('blocked by a closure');
  });
});

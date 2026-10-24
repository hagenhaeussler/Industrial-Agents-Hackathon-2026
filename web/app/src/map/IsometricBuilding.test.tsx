import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { act, cleanup, fireEvent, render } from '@testing-library/react';
import { Window } from 'happy-dom';
import { renderToStaticMarkup } from 'react-dom/server';
import buildingJson from '../../../../data/dev/proc-campus-dev-013/building.json';
import type { Building, ReachableRoute, Snapshot } from '../api/types';
import { createIsometricLayout, isometricMatrix } from '../geo/isometric';
import { FloorMap } from './FloorMap';
import { IsometricBuilding } from './IsometricBuilding';
import { buildModel } from './model';

// Real three-floor kit building; room anchors use the renderer's existing centroid fallback.
const building = buildingJson as unknown as Building;
const snapshot: Snapshot = { building, building_version: 0, content_hash: 'sha256:e867a1668c8b8745', closed: [building.spaces[0]!.id], derived: { anchors: {}, areas_m2: {} } };
const model = buildModel(snapshot);
const floor0 = model.floors[0]!.id, floor1 = model.floors[1]!.id, floor2 = model.floors[2]!.id;

// Public drawing fields from core.routing.route(load_building('data/dev/proc-campus-dev-013'),
// 'proc-campus-dev-013-F0-S001', 'proc-campus-dev-013-F2-S001'), generated without questions/gold data.
const route: ReachableRoute = {
  from_space_id: 'proc-campus-dev-013-F0-S001', to_space_id: 'proc-campus-dev-013-F2-S001',
  constraints: { step_free: false, min_door_width_m: 0, closed: [], no_transit_room_types: [] },
  profile: 'kit_1_1_0', building_id: building.building.id, building_version: 0, content_hash: snapshot.content_hash,
  reachable: true, length_m: 43.81,
  space_path: ['proc-campus-dev-013-F0-S001', 'proc-campus-dev-013-F0-S010', 'proc-campus-dev-013-F1-S010', 'proc-campus-dev-013-F2-S010', 'proc-campus-dev-013-F2-S001'],
  node_path: ['proc-campus-dev-013-F0-S001', 'door:proc-campus-dev-013-F0-O0009', 'proc-campus-dev-013-F0-S010', 'proc-campus-dev-013-F1-S010', 'proc-campus-dev-013-F2-S010', 'door:proc-campus-dev-013-F2-O0050', 'proc-campus-dev-013-F2-S001'],
  element_path: ['proc-campus-dev-013-F0-O0009', 'proc-campus-dev-013-V03', 'proc-campus-dev-013-V03', 'proc-campus-dev-013-F2-O0050'],
  segments: [
    { floor_id: floor0, kind: 'walk', space_id: 'proc-campus-dev-013-F0-S001', points: [[-7.2, 24.45], [-6.3, 35.42], [-6, 35.42]], length_m: 11.307 },
    { floor_id: floor0, kind: 'walk', space_id: 'proc-campus-dev-013-F0-S010', points: [[-6, 35.42], [-5.7, 35.42], [-3, 35.42]], length_m: 3 },
    { floor_id: floor0, kind: 'stairs', element_id: 'proc-campus-dev-013-V03', points: [[-3, 35.42]], to_floor_id: floor1, length_m: 7.6 },
    { floor_id: floor1, kind: 'stairs', element_id: 'proc-campus-dev-013-V03', points: [[-3, 35.42]], to_floor_id: floor2, length_m: 7.6 },
    { floor_id: floor2, kind: 'walk', space_id: 'proc-campus-dev-013-F2-S010', points: [[-3, 35.42], [-5.7, 35.42], [-6, 35.42]], length_m: 3 },
    { floor_id: floor2, kind: 'walk', space_id: 'proc-campus-dev-013-F2-S001', points: [[-6, 35.42], [-6.3, 35.42], [-7.2, 24.45]], length_m: 11.307 },
  ],
  maneuvers: [
    { i: 0, kind: 'depart', floor_id: floor0, at: [-7.2, 24.45], distance_m: 0, text: 'Start in Corridor 0.01.', landmark: null, element_id: null },
    { i: 1, kind: 'turn_right', floor_id: floor0, at: [-6, 35.42], distance_m: 11.31, text: 'Turn right into Staircase 2.', landmark: 'Staircase 2', element_id: 'proc-campus-dev-013-F0-O0009' },
    { i: 2, kind: 'take_stairs', floor_id: floor0, at: [-3, 35.42], distance_m: 3, text: 'Take the Staircase 2 to Floor 2.', landmark: 'Staircase 2', element_id: 'proc-campus-dev-013-V03' },
    { i: 3, kind: 'turn_left', floor_id: floor2, at: [-6, 35.42], distance_m: 18.2, text: 'After the Fire extinguisher 2.10, turn left.', landmark: 'Fire extinguisher 2.10', element_id: 'proc-campus-dev-013-F2-O0050' },
    { i: 4, kind: 'arrive', floor_id: floor2, at: [-7.2, 24.45], distance_m: 11.31, text: 'You have arrived at Corridor 2.01.', landmark: null, element_id: null },
  ],
};

let dom: Window;
beforeEach(() => {
  dom = new Window({ url: 'http://localhost/desk?building=proc-campus-dev-013' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
});
afterEach(() => { cleanup(); dom.happyDOM.abort(); });

const parse = (html: string) => { const container = document.createElement('div'); container.innerHTML = html; return container; };

describe('exploded isometric building', () => {
  test('renders every actual kit floor once with independent hatch IDs and no flat Ghost copies', () => {
    const content = parse(renderToStaticMarkup(<IsometricBuilding model={model} floorId={floor1}/>));
    expect(model.floors.length).toBe(3);
    expect(content.querySelectorAll('.isometric-floor').length).toBe(3);
    expect(content.querySelectorAll('.map-rooms polygon').length).toBe(building.spaces.length);
    expect(content.querySelector('path[stroke-dasharray="3 3"]')).toBeNull();
    const patterns = [...content.querySelectorAll('pattern')].map(pattern => pattern.id);
    expect(patterns.length).toBe(3); expect(new Set(patterns).size).toBe(3);
    for (const element of content.querySelectorAll('[fill^="url(#"]')) {
      const id = element.getAttribute('fill')!.slice(5, -1);
      expect(patterns).toContain(id);
    }
    for (const floor of model.floors) {
      const button = content.querySelector(`[role="button"][aria-label="Focus ${floor.name}"]`)!;
      expect(button).not.toBeNull();
      expect(button.getAttribute('tabindex')).toBe('0');
      expect(button.getAttribute('aria-pressed')).toBe(String(floor.id === floor1));
    }
  });

  test('preserves raw core route paths inside each floor projection without changing route data', () => {
    const before = JSON.stringify(route);
    const content = parse(renderToStaticMarkup(<IsometricBuilding model={model} floorId={floor0} route={route}/>));
    const layout = createIsometricLayout(model.box, model.floors.length);
    for (const [rank, floor] of model.floors.entries()) {
      const stacked = content.querySelector(`[data-floor-id="${floor.id}"]`)!;
      const flat = parse(renderToStaticMarkup(<FloorMap model={model} floorId={floor.id} route={route}/>));
      const actual = stacked.querySelector('.map-route path[stroke="#dcff58"]')?.getAttribute('d') ?? null;
      expect(actual).toBe(flat.querySelector('.map-route path[stroke="#dcff58"]')?.getAttribute('d') ?? null);
      expect(stacked.querySelector('.floor-drawing')!.parentElement!.getAttribute('transform')).toBe(isometricMatrix(layout, rank));
    }
    expect(content.querySelectorAll('.map-route path[stroke="#dcff58"]').length).toBe(2);
    expect(JSON.stringify(route)).toBe(before);
  });

  test('selected assets on inactive floors stay visible at their unmodified building coordinates', () => {
    const assets = model.floors.map(floor => building.assets.find(asset => asset.floor_id === floor.id)!);
    const content = parse(renderToStaticMarkup(<IsometricBuilding model={model} floorId={floor1} selected={new Set(assets.map(asset => asset.id))}/>));
    expect(content.querySelectorAll('.map-chosen').length).toBe(3);
    for (const asset of assets) {
      const dot = content.querySelector(`[data-floor-id="${asset.floor_id}"] .map-chosen circle`)!;
      expect(Number(dot.getAttribute('cx'))).toBe(Math.round(asset.position[0] * 100) / 100);
      expect(Number(dot.getAttribute('cy'))).toBe(Math.round(-asset.position[1] * 100) / 100);
    }
  });

  test('floor labels support keyboard selection and refocus without resizing the scene', async () => {
    const calls: string[] = [];
    const screen = render(<IsometricBuilding model={model} floorId={floor0} onFloor={id => calls.push(id)}/>);
    const viewBox = screen.getByRole('group', { name: 'Exploded 3D building: 3 floors' }).getAttribute('viewBox');
    const camera = screen.container.querySelector('.isometric-camera')!.getAttribute('style');
    await act(async () => { fireEvent.keyDown(screen.getByRole('button', { name: 'Focus Floor 2' }), { key: 'Enter' }); });
    expect(calls).toEqual([floor2]);
    await act(async () => { screen.rerender(<IsometricBuilding model={model} floorId={floor2} onFloor={id => calls.push(id)}/>); });
    expect(screen.getByRole('button', { name: 'Focus Floor 2' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: 'Focus Ground floor' }).getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByRole('group', { name: 'Exploded 3D building: 3 floors' }).getAttribute('viewBox')).toBe(viewBox);
    expect(screen.container.querySelector('.isometric-camera')!.getAttribute('style')).not.toBe(camera);
  });

  test('a connector pill selects its target floor once instead of bubbling back to the source floor', async () => {
    const calls: string[] = [];
    const screen = render(<IsometricBuilding model={model} floorId={floor0} route={route} onFloor={id => calls.push(id)}/>);
    const ground = screen.container.querySelector(`[data-floor-id="${floor0}"]`)!;
    const pill = [...ground.querySelectorAll('.map-pill.clickable')].find(item => item.textContent?.includes('Stairs to Floor 1'));
    expect(pill).toBeDefined();
    await act(async () => { fireEvent.click(pill!); });
    expect(calls).toEqual([floor1]);
  });
});

import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { act, cleanup, fireEvent, render } from '@testing-library/react';
import { Window } from 'happy-dom';
import buildingJson from '../../../../demo/colab/building.json';
import type { Building } from '../api/types';
import type { ColabMovement, ColabPosition, ColabState } from '../api/colab';
import { movementPoint, positionLabel } from '../api/colab';
import { buildModel } from '../map/model';
import { match } from '../router';
import { ColabScene } from './ColabScene';

const building = buildingJson as unknown as Building;
const model = buildModel({ building, building_version: 0, content_hash: 'test-schematic', closed: [], derived: { anchors: {}, areas_m2: {} } });
const floor = model.floors.find(item => item.level === 3)!;
const movement: ColabMovement = { asset_id: 'test', floor_id: floor.id, from: [2, 4], to: [12, 8], started_at: 1_800_000_000, duration_s: 10 };

let dom: Window;
beforeEach(() => {
  dom = new Window({ url: 'http://localhost/colab' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
});
afterEach(() => { cleanup(); dom.happyDOM.abort(); });

describe('shared Colab scene', () => {
  test('interpolates a server event by its timestamp, clamps endpoints and never randomizes positions', () => {
    expect(movementPoint(movement, 1_800_000_000_000 - 500)).toEqual([2, 4]);
    expect(movementPoint(movement, 1_800_000_005_000)).toEqual([7, 6]);
    expect(movementPoint(movement, 1_800_000_020_000)).toEqual([12, 8]);
    expect(movementPoint({ ...movement, started_at: 1_800_000_000_000 }, 1_800_000_005_000)).toEqual([7, 6]);
    expect(movementPoint(movement, 1_800_000_005_000)).toEqual(movementPoint(movement, 1_800_000_005_000));
  });

  test('reduced motion shows discrete confirmed event positions without an animated intermediate location', () => {
    expect(movementPoint(movement, 1_799_999_999_000, true)).toEqual([2, 4]);
    expect(movementPoint(movement, 1_800_000_005_000, true)).toEqual([12, 8]);
  });

  test('draws supplied floors, furnishings and shared positions without inventing people', async () => {
    const changes: string[] = [];
    const base = { model, state: null, floorId: floor.id, selectedAsset: null, selectedPosition: null, now: 1_800_000_005_000, reducedMotion: true, zoom: 1, focused: false, onFloor: (id: string) => changes.push(id), onAsset: () => {}, onPosition: () => {} };
    const screen = render(<ColabScene {...base}/>);
    expect(screen.container.querySelectorAll('.colab-scene-floor').length).toBe(building.floors.length);
    expect(screen.container.querySelectorAll('.map-rooms polygon').length).toBe(building.spaces.length);
    expect(screen.container.querySelectorAll('.colab-furniture').length).toBe(building.assets.length);
    expect(screen.container.querySelectorAll('.colab-position').length).toBe(0);
    const fourth = model.floors.find(item => item.level === 4)!;
    await act(async () => fireEvent.keyDown(screen.getByRole('button', { name: `Focus ${fourth.name}` }), { key: 'Enter' }));
    expect(changes).toEqual([fourth.id]);
  });

  test('Wi-Fi, manual and simulated sources remain distinct, including stale status and unvalidated radius', () => {
    const point = building.assets.find(asset => asset.floor_id === floor.id)!;
    const positions: ColabPosition[] = [
      { device_id: 'wifi', label: 'Android collector', floor_id: floor.id, space_id: point.space_id, x: point.position[0], y: point.position[1], source: 'wifi_fingerprint', confidence: 'low', accuracy_m: 5, updated_at: 1_800_000_000, stale: false },
      { device_id: 'manual', label: 'My phone', floor_id: floor.id, space_id: point.space_id, x: point.position[0] + 1, y: point.position[1], source: 'manual', confidence: 'confirmed', accuracy_m: null, updated_at: 1_800_000_000, stale: true },
      { device_id: 'simulated', label: 'Demo visitor', floor_id: floor.id, space_id: point.space_id, x: point.position[0] + 2, y: point.position[1], source: 'simulated', confidence: 'simulated', accuracy_m: null, updated_at: 1_800_000_000, stale: false },
    ];
    const state: ColabState = { model_revision: 'test-model', sequence: 1, server_time: 1_800_000_000, assets: [], movements: [], positions, demo_running: true, walk_running: true };
    const screen = render(<ColabScene model={model} state={state} floorId={floor.id} selectedAsset={null} selectedPosition={null} now={1_800_000_000_000} reducedMotion zoom={1} focused onFloor={() => {}} onAsset={() => {}} onPosition={() => {}}/>);
    expect(screen.getByRole('button', { name: 'Android collector: Wi-Fi estimate' })).not.toBeNull();
    expect(screen.getByRole('button', { name: 'My phone: Manually placed · stale' })).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Demo visitor: Simulated walk' })).not.toBeNull();
    expect(screen.container.textContent).toContain('indicative radius 5.0 m, unvalidated');
    expect(positionLabel(positions[2])).not.toContain('Wi-Fi');
  });

  test('adds a dedicated route without changing desk and phone routing', () => {
    expect(match('/colab')).toEqual({ name: 'colab' });
    expect(match('/desk')).toEqual({ name: 'desk' });
    expect(match('/go/existing-tour')).toEqual({ name: 'go', tourId: 'existing-tour' });
  });
});

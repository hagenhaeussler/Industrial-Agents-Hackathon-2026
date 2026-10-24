import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { Window } from 'happy-dom';
import { ApiError, api } from '../api/client';
import type { TeamBuildingResult } from '../api/types';
import { Home } from './Home';
import { NewBuilding } from './NewBuilding';

let dom: Window;
const original = { ...api };
const teams = [{ id: 'production', name: 'Production & Assembly', building_count: 1 }, { id: 'engineering', name: 'Research & Engineering', building_count: 1 }];
const building = { id: 'fixture-building', name: 'Workshop North', source: 'upload', split: 'dev', floors: 3, has_stairs: true, has_lift: true };
const result: TeamBuildingResult = { building_id: 'created-building', team_id: 'production', validation: { ok: true, errors: [], warnings: [], stats: { floors: 3, spaces: 8, assets: 2 } } };
function inputText(input: HTMLElement, value: string) {
  Object.assign(input, { attachEvent: () => undefined, detachEvent: () => undefined });
  fireEvent.focusIn(input); fireEvent.change(input, { target: { value } }); fireEvent.keyUp(input, { key: 'a' });
}
function files(view: ReturnType<typeof render>, plan = '{"building":{"name":"Workshop"}}') {
  fireEvent.change(view.getByLabelText(/Equipment list/), { target: { files: [new File(['asset_id,name,type,space_id,x_m,y_m\na1,Printer,printer,r1,1,2'], 'equipment.csv')] } });
  fireEvent.change(view.getByLabelText(/Floor plan/), { target: { files: [new File([plan], 'floor-plan.json')] } });
}
beforeEach(() => {
  dom = new Window({ url: 'https://localhost/' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true }, navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    location: { value: dom.location, configurable: true }, history: { value: dom.history, configurable: true },
    localStorage: { value: dom.localStorage, configurable: true }, sessionStorage: { value: dom.sessionStorage, configurable: true }, IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
  api.teams = async () => structuredClone(teams);
  api.teamBuildings = async () => [structuredClone(building)];
  api.createTeamBuilding = async () => structuredClone(result);
});
afterEach(() => { cleanup(); Object.assign(api, original); dom.happyDOM.abort(); });

describe('minimal team entry', () => {
  test('landing contains only the product name and one orb, without loading a catalog or microphone', () => {
    let requests = 0;
    api.teams = async () => { requests++; return teams; };
    const view = render(<Home/>);
    expect(view.getByRole('heading', { name: 'Talk to Your Building' })).toBeTruthy();
    expect(view.getAllByRole('button')).toHaveLength(1);
    expect(view.getByRole('button', { name: 'Choose your team' })).toBeTruthy();
    expect(view.queryByText('Choose a building')).toBeNull();
    expect(requests).toBe(0);
  });
  test('orb leads to team choice, selected team opens its buildings, and a building opens the desk with team context', async () => {
    const view = render(<Home/>);
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Choose your team' })); });
    await waitFor(() => expect(view.queryByRole('button', { name: /Production & Assembly/ })).not.toBeNull());
    expect(view.queryByRole('region', { name: 'Team buildings' })).toBeNull();
    await act(async () => { fireEvent.click(view.getByRole('button', { name: /Production & Assembly/ })); });
    await waitFor(() => expect(view.queryByRole('link', { name: /Workshop North/ })).not.toBeNull());
    expect(view.getByRole('button', { name: /Production & Assembly/ }).getAttribute('aria-pressed')).toBe('true');
    await act(async () => { fireEvent.click(view.getByRole('link', { name: /Workshop North/ })); });
    expect(location.pathname).toBe('/desk');
    expect(new URLSearchParams(location.search).get('team')).toBe('production');
    expect(new URLSearchParams(location.search).get('building')).toBe(building.id);
  });
  test('late buildings from a previous team cannot replace the newly selected team', async () => {
    let release!: (value: typeof building[]) => void;
    api.teamBuildings = async team => team === 'production' ? new Promise(resolve => { release = resolve; }) : [{ ...building, name: 'Engineering Lab' }];
    history.replaceState(null, '', '/?view=teams');
    const view = render(<Home/>);
    await waitFor(() => expect(view.queryByRole('button', { name: /Production & Assembly/ })).not.toBeNull());
    await act(async () => { fireEvent.click(view.getByRole('button', { name: /Production & Assembly/ })); });
    await act(async () => { fireEvent.click(view.getByRole('button', { name: /Research & Engineering/ })); });
    await waitFor(() => expect(view.queryByText('Engineering Lab')).not.toBeNull());
    await act(async () => { release([building]); });
    expect(view.queryByText('Workshop North')).toBeNull();
    expect(view.queryByText('Engineering Lab')).not.toBeNull();
  });
  test('create building shows two upload boxes inside the selected team panel', async () => {
    history.replaceState(null, '', '/?team=production');
    const view = render(<Home/>);
    await waitFor(() => expect(view.getByRole('button', { name: 'Create a new building' }).hasAttribute('disabled')).toBe(false));
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Create a new building' })); });
    expect(view.getByLabelText(/Equipment list/)).toBeTruthy(); expect(view.getByLabelText(/Floor plan/)).toBeTruthy();
    expect(view.getByRole('button', { name: 'Upload and create building' }).hasAttribute('disabled')).toBe(true);
  });
});

describe('two-file building upload', () => {
  test('requires both files and saves their actual contents to the selected team with existing tab access', async () => {
    sessionStorage.setItem('tyb.admin.access-code', 'test-private-code');
    const sent: unknown[][] = [], created: string[] = [];
    api.createTeamBuilding = async (...args) => { sent.push(args); return structuredClone(result); };
    const view = render(<NewBuilding teamId="production" onBack={() => undefined} onCreated={id => created.push(id)}/>);
    files(view);
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Upload and create building' })); });
    await waitFor(() => expect(view.queryByText('Your building is ready')).not.toBeNull());
    expect(sent).toHaveLength(1); expect(sent[0]![0]).toBe('production'); expect(sent[0]![1]).toEqual({ building: { name: 'Workshop' } });
    expect(String(sent[0]![2])).toContain('a1,Printer,printer,r1,1,2'); expect(sent[0]![3]).toBe('test-private-code');
    expect(created).toEqual(['created-building']);
    expect(view.queryByText('test-private-code')).toBeNull();
  });
  test('missing authority opens the existing access gate and never sends an anonymous upload', async () => {
    let calls = 0; api.createTeamBuilding = async () => { calls++; return result; };
    const view = render(<NewBuilding teamId="production" onBack={() => undefined} onCreated={() => undefined}/>);
    files(view);
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Upload and create building' })); });
    expect(view.getByRole('dialog', { name: 'Building access' }).hasAttribute('open')).toBe(true);
    expect(calls).toBe(0);
    inputText(view.getByLabelText('Access code'), 'test-private-code');
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Create building' })); });
    await waitFor(() => expect(calls).toBe(1));
  });
  test('malformed plans retain both chosen files and show an error without creating a building', async () => {
    sessionStorage.setItem('tyb.admin.access-code', 'test-private-code');
    let calls = 0; api.createTeamBuilding = async () => { calls++; return result; };
    const view = render(<NewBuilding teamId="production" onBack={() => undefined} onCreated={() => undefined}/>);
    files(view, 'not JSON');
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Upload and create building' })); });
    await waitFor(() => expect(view.queryByRole('alert')).not.toBeNull());
    expect(view.getByRole('alert').textContent).toContain('not valid JSON'); expect(calls).toBe(0);
    expect(view.getByText('equipment.csv')).toBeTruthy(); expect(view.getByText('floor-plan.json')).toBeTruthy();
  });
  test('server validation failure never shows a created building', async () => {
    sessionStorage.setItem('tyb.admin.access-code', 'test-private-code');
    api.createTeamBuilding = async () => { throw new ApiError(422, 'invalid_args', 'Equipment row 2: room missing'); };
    const view = render(<NewBuilding teamId="production" onBack={() => undefined} onCreated={() => { throw new Error('Must not create'); }}/>);
    files(view);
    await act(async () => { fireEvent.click(view.getByRole('button', { name: 'Upload and create building' })); });
    await waitFor(() => expect(view.queryByRole('alert')).not.toBeNull());
    expect(view.getByRole('alert').textContent).toContain('room missing'); expect(view.queryByText('Your building is ready')).toBeNull();
  });
});

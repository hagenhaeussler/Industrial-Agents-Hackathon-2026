/**
 * `?mock=1` only. Serves real kit data as fixtures (CONTRACTS §15) so screens can be built before the
 * live API lands. The tour comes from the kit route model with provisional straight segments; mock
 * planning only covers that one tour and says so. Every screen shows the "demo data" badge meanwhile.
 */
import { ApiError } from '../api/client';
import type { Transport } from '../api/client';
import type { Asset, BuildingSummary, ChatReply, Session, Snapshot, Tour } from '../api/types';
import { centroid } from '../geo/transform';
import snapshotJson from './data/building_proc-factory-dev-003.json';
import tourJson from './data/tour_proc-factory-dev-003.json';

const snapshot = snapshotJson as unknown as Snapshot;
const fixtureTour = tourJson as unknown as Tour;
const sessions = new Map<string, Session>();
const tours = new Map<string, Tour>([[fixtureTour.tour_id, structuredClone(fixtureTour)]]);
const constraints = { step_free: false, min_door_width_m: 0, closed: [], no_transit_room_types: [] };
let requests = 0;

const repoRoot = (import.meta.env.TYB_REPO_ROOT as string | undefined) ?? '';
const kitSnapshots = new Map<string, Promise<Snapshot>>();

/** Dev server only: any kit building straight from data/, anchors from polygon centroids (approximate). */
async function kitManifest(): Promise<(BuildingSummary & { path: string })[]> {
  if (!repoRoot) return [];
  const text = await (await fetch(`/@fs${repoRoot}data/manifest.csv`)).text();
  const [head, ...rows] = text.trim().split('\n');
  const keys = (head ?? '').split(',');
  return rows.map(row => {
    const cells = row.match(/("([^"]|"")*"|[^,]*)(,|$)/g)?.map(cell => cell.replace(/,$/, '').replace(/^"|"$/g, '').replace(/""/g, '"')) ?? [];
    const get = (key: string) => cells[keys.indexOf(key)] ?? '';
    return { id: get('building_id'), name: get('name'), source: get('source'), split: get('split'), floors: Number(get('floors')), has_lift: get('has_lift') === 'True', has_stairs: get('has_stairs') === 'True', path: get('path') };
  });
}

async function kitSnapshot(id: string): Promise<Snapshot> {
  const entry = (await kitManifest()).find(item => item.id === id);
  if (!entry) throw new ApiError(404, 'not_found', `Mock mode does not know ${id}.`);
  const building = await (await fetch(`/@fs${repoRoot}data/${entry.path}/building.json`)).json() as Snapshot['building'];
  const anchors = Object.fromEntries(building.spaces.map(space => [space.id, centroid(space.polygon)]));
  return { building, building_version: 0, content_hash: `mock:${id}`, closed: [], derived: { anchors, areas_m2: {} } };
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const hex = () => Math.random().toString(16).slice(2, 14).padEnd(12, '0');

function search(query: string): Asset[] {
  const words = query.toLowerCase().replace(/[^a-z0-9 .-]/g, ' ').split(/\s+/).filter(word => word.length > 2 && !['the', 'where', 'need', 'find', 'and', 'is', 'are'].includes(word));
  if (!words.length) return [];
  return snapshot.building.assets.filter(asset => words.every(word => `${asset.name} ${asset.type.replace(/_/g, ' ')}`.toLowerCase().includes(word)));
}

function chat(message: string): ChatReply {
  const request_id = `req_mock${String(++requests).padStart(8, '0')}`;
  const base = { tool: 'find', request_id, building_id: snapshot.building.building.id, building_version: 0 };
  const hits = search(message);
  const space = (asset: Asset) => snapshot.building.spaces.find(item => item.id === asset.space_id)?.name ?? asset.space_id;
  if (!hits.length) return { reply: `Demo data: I found nothing matching “${message}” in this building.`, tool_calls: [{ ...base, ok: false, error: { code: 'not_found', message: 'nothing matches' } }], display: null };
  if (hits.length > 1 && hits.length <= 4) {
    const candidates = hits.map(asset => ({ id: asset.id, name: asset.name, floor_id: asset.floor_id }));
    return { reply: `Demo data: there are ${hits.length} matches. Which one?`, tool_calls: [{ ...base, ok: false, error: { code: 'ambiguous', message: 'several matches', candidates } }], display: null };
  }
  const hit = hits[0]!;
  const display = { kind: 'highlight', asset_ids: hits.slice(0, 12).map(asset => asset.id), space_id: hit.space_id, floor_id: hit.floor_id };
  return { reply: hits.length > 4 ? `Demo data: ${hits.length} matches; showing them on the map.` : `Demo data: ${hit.name} is in ${space(hit)}.`, tool_calls: [{ ...base, ok: true, result: { asset_ids: display.asset_ids }, display }], display };
}

export const mockTransport: Transport = async (method, path, body) => {
  await delay(120);
  const input = (body ?? {}) as Record<string, unknown>;
  const [route] = path.split('?');
  const parts = (route ?? '').split('/').filter(Boolean).map(decodeURIComponent); // ['api', ...]
  const id = snapshot.building.building.id;
  if (method === 'GET' && parts[1] === 'teams') {
    const catalog = await mockTransport('GET', '/api/buildings') as BuildingSummary[];
    const names: Record<string, string> = { production: 'Production & Assembly', engineering: 'Research & Engineering', facilities: 'Facilities & Maintenance', property: 'Property Operations', projects: 'New Projects' };
    const group = (item: BuildingSummary) => item.source === 'procedural' ? item.id.includes('campus') ? 'engineering' : 'production' : item.source === 'osm_indoor' ? 'facilities' : ['resplan', 'swiss_dwellings'].includes(item.source) ? 'property' : 'projects';
    if (parts.length === 2) return Object.entries(names).map(([id, name]) => ({ id, name, building_count: catalog.filter(item => group(item) === id).length }));
    if (parts[3] === 'buildings' && names[parts[2]!]) return catalog.filter(item => group(item) === parts[2]);
  }
  if (method === 'GET' && route === '/api/buildings') {
    const summary: BuildingSummary = { id, name: snapshot.building.building.name, source: 'procedural', split: 'dev', floors: snapshot.building.floors.length, has_lift: true, has_stairs: true };
    return [summary, ...(await kitManifest()).filter(item => item.id !== id)];
  }
  if (method === 'GET' && parts[1] === 'buildings' && parts.length === 3) {
    if (parts[2] === id) return snapshot;
    const key = parts[2] ?? '';
    if (!kitSnapshots.has(key)) kitSnapshots.set(key, kitSnapshot(key));
    return await kitSnapshots.get(key)!;
  }
  if (parts[1] === 'sessions') {
    if (method === 'POST') {
      const session: Session = { session_id: hex() + hex(), building_id: String(input.building_id), device: input.device as Session['device'], role: input.role as Session['role'], profile: 'walk', constraints, position: null, active_tour_id: null };
      sessions.set(session.session_id, session);
      return session;
    }
    const session = sessions.get(parts[2] ?? '');
    if (!session) throw new ApiError(404, 'not_found', 'unknown session');
    if (method === 'PATCH') Object.assign(session, input);
    return session;
  }
  if (parts[1] === 'tours') {
    if (method === 'POST' && parts.length === 2) {
      const want = new Set((input.items as string[] | undefined) ?? []);
      const have = new Set(fixtureTour.stops.flatMap(stop => stop.asset_ids));
      if (want.size !== have.size || [...want].some(item => !have.has(item))) throw new ApiError(501, 'not_available', 'Mock mode can only plan the demo tour (3D printer, tool cabinet, UPS unit). Live planning needs the server.');
      const tour = { ...structuredClone(fixtureTour), tour_id: hex().slice(0, 10) };
      tours.set(tour.tour_id, tour);
      return tour;
    }
    const tour = tours.get(parts[2] ?? '');
    if (!tour) throw new ApiError(404, 'not_found', 'unknown tour');
    if (method === 'POST' && parts[3] === 'progress') {
      const stop = tour.stops.find(item => item.stop_id === input.stop_id);
      if (stop) stop.status = input.status as Tour['stops'][number]['status'];
      tour.revision += 1;
    }
    return structuredClone(tour);
  }
  if (method === 'POST' && route === '/api/chat') return chat(String(input.message ?? ''));
  throw new ApiError(501, 'not_available', `Mock mode does not serve ${method} ${route}.`);
};

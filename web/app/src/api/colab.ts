import type { Building, Point } from './types';
import type { components } from './schema.gen';

/** The Colab showcase is a separate, explicitly schematic model and shared demo feed. */
export type ColabModel = Omit<components['schemas']['ColabModel'], 'building'> & { building: Building };
export type ColabPosition = components['schemas']['ColabPosition'];
export type ColabMovement = components['schemas']['ColabMovement'];
export type ColabState = components['schemas']['ColabState'];
export type ColabWifiStatus = components['schemas']['WifiStatus'];
export type ColabPair = components['schemas']['PairedCollector'];

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/colab/${path}`, body === undefined ? { cache: 'no-store' } : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new Error(typeof payload?.detail === 'string' ? payload.detail : `The building service returned ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

export const colabApi = {
  model: () => request<ColabModel>('model'),
  state: () => request<ColabState>('state'),
  demo: (running: boolean) => request<ColabState>('demo', { running }),
  walk: (running: boolean) => request<ColabState>('demo/walk', { running }),
  position: (position: { device_id?: string; label: string; floor_id: string; x: number; y: number; source: 'manual' | 'simulated' }) => request<ColabPosition>('positions', position),
};

export const epochMs = (value: number): number => value < 1e12 ? value * 1000 : value;

/** Shared server timestamps ensure two screens animate the same event rather than inventing motion. */
export function movementPoint(movement: ColabMovement, nowMs: number, reducedMotion = false): Point {
  const duration = Math.max(1, movement.duration_s * 1000);
  const elapsed = nowMs - epochMs(movement.started_at);
  const t = Math.max(0, Math.min(1, elapsed / duration));
  const eased = reducedMotion ? (elapsed < 0 ? 0 : 1) : t * t * (3 - 2 * t);
  return [movement.from[0] + (movement.to[0] - movement.from[0]) * eased, movement.from[1] + (movement.to[1] - movement.from[1]) * eased];
}

export function positionLabel(position: ColabPosition): string {
  const source = position.source === 'wifi_fingerprint' ? 'Wi-Fi estimate' : position.source === 'manual' ? 'Manually placed' : 'Simulated walk';
  return `${source}${position.stale ? ' · stale' : ''}`;
}

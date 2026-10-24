/**
 * Compile-time guard: the precise contract types in `types.ts` must stay assignable to the server's
 * OpenAPI types (`schema.gen.ts`, regenerated with `bun run gen:api`). A server change that breaks
 * one of these fails `tsc -b`.
 */
import type { components } from './schema.gen';
import type { BuildingSummary, Position, Session, Snapshot, ToolResponse, Tour, TourStop } from './types';

type S = components['schemas'];
type Assignable<A, B> = [A] extends [B] ? true : false;
const ok = <T extends true>(): T | undefined => undefined;

export const schemaChecks = [
  ok<Assignable<BuildingSummary, S['BuildingSummary']>>(),
  ok<Assignable<Position, S['Position']>>(),
  ok<Assignable<Omit<Session, 'constraints'>, Omit<S['Session'], 'constraints' | 'updated_at'>>>(),
  ok<Assignable<Snapshot['derived'], S['DerivedGeometry']>>(),
  ok<Assignable<TourStop, S['TourStop']>>(),
  ok<Assignable<Pick<Tour, 'tour_id' | 'revision' | 'order' | 'length_m' | 'stops'>, Pick<S['TourResult'], 'tour_id' | 'revision' | 'order' | 'length_m' | 'stops'>>>(),
  ok<Assignable<Pick<ToolResponse, 'ok' | 'tool' | 'request_id'>, Pick<S['ToolResponse'], 'ok' | 'tool' | 'request_id'>>>(),
];

/**
 * The demo scenario from `demo/scenario.json` (repository root, owner Manuel's Claude).
 * Loaded through a glob so a build that only sees `web/` (Docker web stage) still succeeds;
 * it then falls back to the kit factory without preselected parts.
 */
export type Scenario = {
  building_id: string;
  fallback_building_id: string;
  persona: string;
  start: { space_id: string; label: string };
  say: string;
  items: string[];
  admin: { say: string; target: string; element_id: string };
};

const files = import.meta.glob<Scenario>('../../../../demo/scenario.json', { eager: true, import: 'default' });
const loaded = Object.values(files)[0];
if (!loaded) console.warn('demo/scenario.json is not part of this build; the demo opens the kit factory without preselected parts.');

export const scenario: Scenario = loaded ?? {
  building_id: 'proc-factory-dev-003', fallback_building_id: 'proc-factory-dev-003', persona: 'Manfred',
  start: { space_id: '', label: '' }, say: '', items: [], admin: { say: '', target: '', element_id: '' },
};

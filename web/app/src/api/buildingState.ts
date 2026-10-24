/** Numeric versions can be reused after demo reset; opaque state IDs identify the edit history. */
export type BuildingState = { building_version: number; building_state_id?: string | null };

export function sameBuildingState(current: BuildingState, candidate: BuildingState): boolean {
  if (current.building_version !== candidate.building_version) return false;
  // A legacy stored tour without an ID must refresh once against a live C9 snapshot.
  if (current.building_state_id || candidate.building_state_id) return !!current.building_state_id && current.building_state_id === candidate.building_state_id;
  return true; // Explicit old fixtures/servers have only a numeric version.
}

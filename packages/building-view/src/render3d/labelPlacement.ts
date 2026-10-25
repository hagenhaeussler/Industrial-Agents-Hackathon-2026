// Screen-space label placement for the 3D view. Labels are tried in priority order; a label that would
// overlap one already placed is hidden. Equal input gives equal output.

export interface LabelCandidate {
  key: string;
  /** Centre on screen, in CSS pixels. */
  x: number;
  y: number;
  width: number;
  height: number;
  /** Higher goes first. Ties go to the smaller key. */
  priority: number;
}

const CELL_PX = 64;

/** The keys of the labels that fit inside the viewport without overlapping. */
export function placeLabels(candidates: readonly LabelCandidate[], viewport: { width: number; height: number }): Set<string> {
  const order = [...candidates].sort((a, b) => b.priority - a.priority || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
  const grid = new Map<string, LabelCandidate[]>();
  const shown = new Set<string>();

  for (const label of order) {
    const left = label.x - label.width / 2;
    const top = label.y - label.height / 2;
    if (left < 0 || top < 0 || left + label.width > viewport.width || top + label.height > viewport.height) continue;
    const cells = cellKeys(left, top, label.width, label.height);
    const overlaps = cells.some((cell) => (grid.get(cell) ?? []).some((other) => intersects(label, other)));
    if (overlaps) continue;
    shown.add(label.key);
    for (const cell of cells) grid.set(cell, [...(grid.get(cell) ?? []), label]);
  }
  return shown;
}

function cellKeys(left: number, top: number, width: number, height: number): string[] {
  const keys: string[] = [];
  for (let cx = Math.floor(left / CELL_PX); cx <= Math.floor((left + width) / CELL_PX); cx++) {
    for (let cy = Math.floor(top / CELL_PX); cy <= Math.floor((top + height) / CELL_PX); cy++) keys.push(`${cx},${cy}`);
  }
  return keys;
}

function intersects(a: LabelCandidate, b: LabelCandidate): boolean {
  return Math.abs(a.x - b.x) * 2 < a.width + b.width && Math.abs(a.y - b.y) * 2 < a.height + b.height;
}

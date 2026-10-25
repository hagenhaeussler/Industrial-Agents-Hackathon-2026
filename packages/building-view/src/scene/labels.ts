// Which text a space label shows. Shared by the 2D and 3D views, so both label the same rooms.

/** The plan's text for a space and its font size in metres, or null if no readable label fits. */
export function fitLabel(name: string, ref: string, radius: number): { text: string; size: number } | null {
  const MIN_SIZE = 0.2;
  const MAX_SIZE = 0.9;
  for (const text of [name, ref]) {
    if (!text) continue;
    // A label must fit inside the largest circle in the room: roughly 0.55 em per character.
    const size = Math.min(MAX_SIZE, (1.7 * radius) / (text.length * 0.55), radius * 0.8);
    if (size >= MIN_SIZE) return { text, size: Math.round(size * 100) / 100 };
  }
  return null;
}

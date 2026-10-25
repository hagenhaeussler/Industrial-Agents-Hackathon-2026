/** One line of the conversation. Streamed updates replace the entry with the same key. */
export type TranscriptEntry =
  | { key: string; kind: "message"; role: "user" | "agent"; text: string }
  | { key: string; kind: "tool"; name: string; state: "loading" | "awaiting_approval" | "success" | "failure" };

/** Expressive voices add audio tags such as "[happy]" to steer speech. They are not part of the displayed text. */
export function withoutAudioTags(text: string): string {
  return text.replace(/\[[a-z][a-z '-]+\]\s*/gi, "").trim();
}

export function upsert(entries: TranscriptEntry[], entry: TranscriptEntry): TranscriptEntry[] {
  const index = entries.findIndex((existing) => existing.key === entry.key);
  if (index === -1) return [...entries, entry];
  return entries.map((existing, i) => (i === index ? entry : existing));
}

const TOOL_LABELS: Record<string, string> = {
  building_overview: "Read the building overview",
  find_spaces: "Searched rooms",
  find_assets: "Searched equipment",
  route: "Planned a route",
  reachable_spaces: "Checked reachable rooms",
};

/** A short, human label for a tool call in the transcript. */
export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? "Checked the building data";
}

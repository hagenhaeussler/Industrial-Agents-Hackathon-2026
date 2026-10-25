/** Transcript entries for the demo. Streamed updates replace the entry with the same key. */
export type TranscriptEntry =
  | { key: string; kind: "message"; role: "user" | "agent"; text: string }
  | { key: string; kind: "tool"; name: string; state: string; parameters: Record<string, unknown> };

/** Expressive voices add audio tags such as "[happy]" to steer speech. They are not part of the displayed text. */
export function withoutAudioTags(text: string): string {
  return text.replace(/\[[a-z][a-z '-]+\]\s*/gi, "").trim();
}

export function upsert(entries: TranscriptEntry[], entry: TranscriptEntry): TranscriptEntry[] {
  const index = entries.findIndex((existing) => existing.key === entry.key);
  if (index === -1) return [...entries, entry];
  return entries.map((existing, i) => (i === index ? entry : existing));
}

import type { Asset } from '../api/types';
import { floorName, spaceName } from '../map/model';
import type { Model } from '../map/model';

/**
 * Fallback for the desk ask box while text chat is not connected: a plain search of the parts list,
 * one phrase per item ("the 3D printer, the tool cabinet and the UPS unit"). No language model; the
 * reply says that it searched the list.
 */
const FILLER = /\b(i need|i'm looking for|im looking for|i am looking for|looking for|where is|where's|wheres|where are|find|show me|get me|please|bring me|can you|could you|i want|we need|also)\b/g;
const STOP = new Set(['the', 'a', 'an', 'some', 'my', 'our', 'me', 'to', 'of', 'in', 'on', 'is', 'are', 'it', 'and', 'upstairs', 'downstairs']);

export function phrases(text: string): string[] {
  return text.toLowerCase().replace(/[?!]/g, ' ').replace(FILLER, ' ')
    .split(/,|;|\band\b|&|\bplus\b|\+/).map(part => part.trim()).filter(Boolean);
}

const tokens = (phrase: string) => phrase.split(/\s+/).map(word => word.replace(/^[^a-z0-9]+|[^a-z0-9.\-]+$/g, '').replace(/\.+$/, '')).filter(word => word && !STOP.has(word));
const singular = (word: string) => (word.length > 3 && word.endsWith('s') && !word.endsWith('ss') ? word.slice(0, -1) : word);

export type PhraseMatch = { phrase: string; matches: Asset[] };

export function matchParts(model: Model, text: string): PhraseMatch[] {
  return phrases(text).map(phrase => {
    const words = tokens(phrase);
    if (!words.length) return { phrase, matches: [] };
    const hay = (asset: Asset) => `${asset.name} ${asset.type.replace(/_/g, ' ')} ${spaceName(model, asset.space_id)}`.toLowerCase();
    let matches = model.snapshot.building.assets.filter(asset => words.every(word => hay(asset).includes(word) || hay(asset).includes(singular(word))));
    const exact = matches.filter(asset => asset.name.toLowerCase() === words.join(' '));
    if (exact.length) matches = exact;
    return { phrase: words.join(' '), matches };
  }).filter(item => item.phrase);
}

export type Fallback = { reply: string; select: string[]; focus: string | null; candidates: { id: string; name: string; floor_id: string }[] };

export function fallbackReply(model: Model, text: string): Fallback {
  const results = matchParts(model, text);
  const unique = results.filter(item => item.matches.length === 1).map(item => item.matches[0]!);
  const ambiguous = results.filter(item => item.matches.length > 1);
  const missing = results.filter(item => !item.matches.length);
  const parts: string[] = ['Text chat is not connected yet, so I searched the parts list.'];
  if (unique.length === 1 && results.length === 1) parts.push(`${unique[0]!.name} is in ${spaceName(model, unique[0]!.space_id)} · ${floorName(model, unique[0]!.floor_id)}.`);
  else if (unique.length) parts.push(`Selected ${unique.map(asset => asset.name).join(', ')}.`);
  const first = ambiguous[0];
  if (first) parts.push(`There are ${first.matches.length} matches for “${first.phrase}”. Which one?`);
  if (missing.length) parts.push(`Nothing in this building matches ${missing.map(item => `“${item.phrase}”`).join(', ')}.`);
  if (!results.length) parts.push('Name a part, for example “the 3D printer”.');
  return {
    reply: parts.join(' '),
    select: results.length > 1 ? unique.map(asset => asset.id) : [],
    focus: unique[0]?.id ?? null,
    candidates: (first?.matches ?? []).slice(0, 4).map(asset => ({ id: asset.id, name: asset.name, floor_id: asset.floor_id })),
  };
}

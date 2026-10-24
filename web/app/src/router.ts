import { useSyncExternalStore } from 'react';
import type { MouseEvent } from 'react';

/** A tiny history router for the five SPA routes (CONTRACTS §7). Query flags like `?mock=1` survive navigation. */
const listeners = new Set<() => void>();
const notify = () => listeners.forEach(listener => listener());
if (typeof window !== 'undefined') window.addEventListener('popstate', notify);

const subscribe = (listener: () => void) => { listeners.add(listener); return () => listeners.delete(listener); };
const snapshot = () => location.pathname + location.search;

export function useLocation() {
  const href = useSyncExternalStore(subscribe, snapshot, () => '/');
  const url = new URL(href, 'http://local');
  return { path: url.pathname, query: url.searchParams };
}

const STICKY = ['mock'];
export function withSticky(to: string): string {
  const url = new URL(to, location.origin);
  const current = new URLSearchParams(location.search);
  for (const key of STICKY) if (current.has(key) && !url.searchParams.has(key)) url.searchParams.set(key, current.get(key)!);
  return url.pathname + url.search;
}

export function navigate(to: string, replace = false) {
  const target = withSticky(to);
  if (replace) history.replaceState(null, '', target); else history.pushState(null, '', target);
  notify();
}

export function linkHandler(to: string) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  };
}

export type Route =
  | { name: 'home' }
  | { name: 'desk' }
  | { name: 'admin' }
  | { name: 'go'; tourId: string }
  | { name: 'marker'; markerId: string }
  | { name: 'missing' };

export function match(path: string): Route {
  const clean = path.replace(/\/+$/, '') || '/';
  if (clean === '/') return { name: 'home' };
  if (clean === '/desk') return { name: 'desk' };
  if (clean === '/admin') return { name: 'admin' };
  const go = /^\/go\/([^/]+)$/.exec(clean);
  if (go?.[1]) return { name: 'go', tourId: decodeURIComponent(go[1]) };
  const marker = /^\/m\/([^/]+)$/.exec(clean);
  if (marker?.[1]) return { name: 'marker', markerId: decodeURIComponent(marker[1]) };
  return { name: 'missing' };
}

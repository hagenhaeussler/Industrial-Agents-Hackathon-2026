import { useSyncExternalStore } from "react";

/** The app's pages. A building ID comes from the URL, never from code. */
export type Page =
  | { name: "home" }
  | { name: "guide"; buildingId: string }
  | { name: "admin"; buildingId: string }
  | { name: "missing" };

export function parsePage(pathname: string): Page {
  const [first, second, ...rest] = pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (first === undefined) return { name: "home" };
  if (second !== undefined && rest.length === 0) {
    if (first === "b") return { name: "guide", buildingId: second };
    if (first === "admin") return { name: "admin", buildingId: second };
  }
  return { name: "missing" };
}

const listeners = new Set<() => void>();
const notify = () => listeners.forEach((listener) => listener());
window.addEventListener("popstate", notify);

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The current path and query. Re-renders on navigation. */
export function useLocation() {
  const href = useSyncExternalStore(subscribe, () => location.pathname + location.search);
  const url = new URL(href, location.origin);
  return { page: parsePage(url.pathname), query: url.searchParams };
}

export function navigate(to: string, replace = false, state: unknown = null) {
  if (replace) history.replaceState(state, "", to);
  else history.pushState(state, "", to);
  notify();
}

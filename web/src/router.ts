import { useSyncExternalStore } from "react";

/** The app's pages. A building ID comes from the URL, never from code. */
export type Page =
  | { name: "home" }
  | { name: "library" }
  | { name: "explore" }
  | { name: "guide"; buildingId: string }
  | { name: "admin"; buildingId: string }
  | { name: "missing" };

export function parsePage(pathname: string): Page {
  const [first, second, ...rest] = pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (first === undefined) return { name: "home" };
  if (first === "buildings" && second === undefined) return { name: "library" };
  if (first === "explore" && second === undefined) return { name: "explore" };
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

export function navigate(to: string, replace = false) {
  if (replace) history.replaceState(null, "", to);
  else history.pushState(null, "", to);
  notify();
}

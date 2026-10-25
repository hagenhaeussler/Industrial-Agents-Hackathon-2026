import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type LoaderWindow = Window & { __tybMapsLoaded?: () => void; google?: unknown };
beforeEach(() => {
  const append = document.head.append.bind(document.head);
  vi.spyOn(document.head, "append").mockImplementation((...nodes) => {
    // Keep real DOM lifecycle/events while preventing any provider execution or network call.
    for (const node of nodes) if (node instanceof HTMLScriptElement) node.type = "application/json";
    append(...nodes);
  });
});
afterEach(() => {
  document.head.querySelectorAll('script[src*="maps.googleapis.com"]').forEach((script) => script.remove());
  delete (window as LoaderWindow).google;
  delete (window as LoaderWindow).__tybMapsLoaded;
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("Google SDK session loader", () => {
  it("deduplicates SDK loading and reuses the library without persisting the key", async () => {
    const {loadGoogle3d,currentGoogle3d} = await import("./google3d");
    const sdk = {Map3DElement:HTMLElement};
    const importLibrary = vi.fn().mockResolvedValue(sdk);
    (window as LoaderWindow).google = {maps:{importLibrary}};
    const beforeLocal = localStorage.length, beforeSession = sessionStorage.length;
    const first = loadGoogle3d("test-only-placeholder"), second = loadGoogle3d("test-only-placeholder");
    expect(first).toBe(second);
    expect(document.head.querySelectorAll('script[src*="maps.googleapis.com"]').length).toBe(1);
    (window as LoaderWindow).__tybMapsLoaded!();
    expect(await first).toBe(sdk);
    expect(currentGoogle3d()).toBe(sdk);
    expect(await loadGoogle3d("unused-placeholder")).toBe(sdk);
    expect(importLibrary).toHaveBeenCalledTimes(1);
    expect(localStorage.length).toBe(beforeLocal);
    expect(sessionStorage.length).toBe(beforeSession);
  });
  it("removes a failed script and permits a fresh attempt without exposing its URL in the error", async () => {
    const {loadGoogle3d} = await import("./google3d");
    const first = loadGoogle3d("private-test-placeholder");
    const assertion = expect(first).rejects.toThrow("Google 3D could not load. Check your key and allowed websites.");
    document.head.querySelector('script[src*="maps.googleapis.com"]')!.dispatchEvent(new Event("error"));
    await assertion;
    expect(document.head.querySelector('script[src*="maps.googleapis.com"]')).toBeNull();
    const next = loadGoogle3d("next-test-placeholder");
    expect(next).not.toBe(first);
    const nextAssertion = expect(next).rejects.toThrow("Google 3D could not load");
    document.head.querySelector('script[src*="maps.googleapis.com"]')!.dispatchEvent(new Event("error"));
    await nextAssertion;
  });
});

import { useCallback, useEffect, useRef } from 'react';

/**
 * Runs requests for one view slot so that only the newest one may apply its result:
 * a late response to an older request is dropped instead of overwriting newer state.
 */
export function createLatest() {
  let current = 0;
  return {
    async run<T>(request: () => Promise<T>, apply: (value: T) => void, fail?: (error: unknown) => void): Promise<void> {
      const ticket = ++current;
      try {
        const value = await request();
        if (ticket === current) apply(value);
      } catch (error) {
        if (ticket === current) fail?.(error);
      }
    },
    cancel() { current += 1; },
    isLatest: (ticket: number) => ticket === current,
  };
}

export function useLatest() {
  const latest = useRef(createLatest());
  useEffect(() => () => latest.current.cancel(), []);
  return useCallback(<T,>(request: () => Promise<T>, apply: (value: T) => void, fail?: (error: unknown) => void) => latest.current.run(request, apply, fail), []);
}

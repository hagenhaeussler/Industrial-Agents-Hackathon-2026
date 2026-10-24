import { afterEach, describe, expect, test } from 'bun:test';
import { requestMotion } from './cameraMotion';

const original = Object.getOwnPropertyDescriptor(globalThis, 'DeviceOrientationEvent');
afterEach(() => { if (original) Object.defineProperty(globalThis, 'DeviceOrientationEvent', original); else Reflect.deleteProperty(globalThis, 'DeviceOrientationEvent'); });
const orientation = (value: unknown) => Object.defineProperty(globalThis, 'DeviceOrientationEvent', { value, configurable: true });

describe('motion permission gesture', () => {
  test('requests iOS permission synchronously before a lazy camera module is loaded', async () => {
    let called = false;
    orientation({ requestPermission: () => { called = true; return Promise.resolve('granted'); } });
    const pending = requestMotion();
    expect(called).toBe(true);
    expect(await pending).toBe(true);
  });
  test('missing, denied and rejected motion permission keep direction-only fallback available', async () => {
    orientation(undefined); expect(await requestMotion()).toBe(false);
    orientation({ requestPermission: async () => 'denied' }); expect(await requestMotion()).toBe(false);
    orientation({ requestPermission: async () => { throw new Error('denied'); } }); expect(await requestMotion()).toBe(false);
    orientation({}); expect(await requestMotion()).toBe(true);
  });
});

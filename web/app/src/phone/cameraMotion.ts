type Orientation = { requestPermission?: () => Promise<'granted' | 'denied'> };

/** Called directly by the Camera button: iOS requires the permission request in the user gesture. */
export async function requestMotion(): Promise<boolean> {
  const event = (globalThis as { DeviceOrientationEvent?: Orientation }).DeviceOrientationEvent;
  if (!event) return false;
  if (typeof event.requestPermission !== 'function') return true;
  try { return (await event.requestPermission()) === 'granted'; } catch { return false; }
}

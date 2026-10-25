import { Navigation2 } from "lucide-react";
import { useEffect, useState } from "react";

type OrientationEvent = DeviceOrientationEvent & { webkitCompassHeading?: number };
type PermissionRequest = { requestPermission?: () => Promise<"granted" | "denied"> };

/**
 * A small compass button. It shows the device heading after the user taps it (iOS asks for permission).
 * Building plans carry no north direction, so it does not turn the map.
 */
export function Compass() {
  const [heading, setHeading] = useState<number>();
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    const update = (event: OrientationEvent) => {
      const value = event.webkitCompassHeading ?? (event.absolute && event.alpha !== null ? 360 - event.alpha : undefined);
      if (value !== undefined) setHeading(Math.round(value));
    };
    const name = "ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation";
    window.addEventListener(name, update as EventListener);
    return () => window.removeEventListener(name, update as EventListener);
  }, [enabled]);

  if (typeof DeviceOrientationEvent === "undefined") return null;

  async function enable() {
    const request = (DeviceOrientationEvent as unknown as PermissionRequest).requestPermission;
    if (request && (await request()) !== "granted") return;
    setEnabled(true);
  }

  return (
    <button
      type="button"
      onClick={() => void enable()}
      aria-label={heading === undefined ? "Show compass" : `Heading ${heading} degrees`}
      className="float grid size-11 place-items-center rounded-[13px]"
    >
      <Navigation2
        size={20}
        className={heading === undefined ? "text-muted" : "fill-danger text-danger"}
        style={{ transform: `rotate(${-(heading ?? 0)}deg)` }}
      />
      {heading !== undefined && <span className="sr-only">{heading}°</span>}
    </button>
  );
}

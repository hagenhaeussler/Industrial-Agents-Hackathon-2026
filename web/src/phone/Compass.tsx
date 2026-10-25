import { Navigation2 } from "lucide-react";
import { useEffect, useState } from "react";

type OrientationEvent = DeviceOrientationEvent & { webkitCompassHeading?: number };
type PermissionRequest = typeof DeviceOrientationEvent & { requestPermission?: () => Promise<"granted" | "denied"> };

async function requestCompassPermission() {
  if (typeof DeviceOrientationEvent === "undefined") return;
  const orientation: PermissionRequest = DeviceOrientationEvent;
  try {
    await orientation.requestPermission?.();
  } catch {
    // A browser can require another user gesture. The compass button allows a retry.
  }
}

/**
 * Listen from page load. Browsers that require permission use the first page interaction.
 * Building plans carry no north direction, so it does not turn the map.
 */
export function Compass() {
  const [heading, setHeading] = useState<number>();

  useEffect(() => {
    if (typeof DeviceOrientationEvent === "undefined") return;
    const update = (event: OrientationEvent) => {
      const value = event.webkitCompassHeading ?? (event.absolute && event.alpha !== null ? 360 - event.alpha : undefined);
      if (value !== undefined) setHeading(Math.round(value));
    };
    const eventName = "ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation";
    window.addEventListener(eventName, update);
    const orientation: PermissionRequest = DeviceOrientationEvent;
    const requestPermission = () => void requestCompassPermission();
    if (orientation.requestPermission) {
      document.addEventListener("click", requestPermission, { once: true });
    }
    return () => {
      window.removeEventListener(eventName, update);
      document.removeEventListener("click", requestPermission);
    };
  }, []);

  if (typeof DeviceOrientationEvent === "undefined") return null;

  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        void requestCompassPermission();
      }}
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

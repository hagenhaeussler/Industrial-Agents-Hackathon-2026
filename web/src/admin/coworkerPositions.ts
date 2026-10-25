import { useEffect, useMemo, useReducer } from "react";
import type { Coworker } from "../api/coworkers";

/** Keeps floor transitions discrete and only interpolates points on the same floor. */
export function coworkerPosition(member: Coworker, serverNow: number) {
  const points = member.journey?.points;
  if (!points?.length) return member.position;
  const first = points[0]!;
  if (serverNow <= first.at) return first;
  for (let index = 1; index < points.length; index++) {
    const next = points[index]!;
    if (serverNow >= next.at) continue;
    const previous = points[index - 1]!;
    if (previous.floorId !== next.floorId) return previous;
    const duration = next.at - previous.at;
    const fraction = duration > 0 ? Math.max(0, Math.min(1, (serverNow - previous.at) / duration)) : 1;
    return { floorId: previous.floorId, x: previous.x + (next.x - previous.x) * fraction, y: previous.y + (next.y - previous.y) * fraction };
  }
  return points.at(-1)!;
}

/** Slides markers along their timed path. Stops the frame clock when hidden or at rest. */
export function useCoworkerMarkers(members: Coworker[], show: boolean, offset: number) {
  const [tick, redraw] = useReducer((value: number) => value + 1, 0);
  useEffect(() => {
    if (!show || !members.some((member) => member.journey)) return;
    let frame: number | undefined;
    const animate = () => {
      redraw();
      const now = Date.now() + offset;
      if (members.some((member) => (member.journey?.points.at(-1)?.at ?? 0) > now)) {
        frame = window.requestAnimationFrame(animate);
      }
    };
    const updateClock = () => {
      if (frame !== undefined) window.cancelAnimationFrame(frame);
      if (document.visibilityState !== "hidden") animate();
    };
    updateClock();
    document.addEventListener("visibilitychange", updateClock);
    return () => {
      if (frame !== undefined) window.cancelAnimationFrame(frame);
      document.removeEventListener("visibilitychange", updateClock);
    };
  }, [members, show, offset]);
  return useMemo(() => show ? members.map((member) => ({
    ...coworkerPosition(member, Date.now() + offset), id: member.id, name: member.name, color: member.color,
  })) : [], [members, show, offset, tick]);
}

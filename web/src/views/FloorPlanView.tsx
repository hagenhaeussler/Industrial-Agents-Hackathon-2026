import { FloorPlan, type BuildingScene, type FloorPlanOptions, type Overlay, type PickResult } from "@building/view";
import { useEffect, useRef, useState } from "react";

/** React wrapper for the 2D floor plan. The plan only draws; picks go back to the caller. */
export function FloorPlanView({
  scene,
  floorId,
  overlay,
  onPick,
  options,
  focus,
  className = "",
}: {
  scene: BuildingScene;
  floorId: string;
  overlay: Overlay;
  onPick?: (pick: PickResult | null) => void;
  options?: Partial<FloorPlanOptions>;
  /** A point to centre the view on, with a width in metres. */
  focus?: { x: number; y: number; width: number };
  className?: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [plan, setPlan] = useState<FloorPlan>();

  useEffect(() => {
    const view = new FloorPlan(container.current!, options);
    setPlan(view);
    return () => view.destroy();
  }, []);

  useEffect(() => {
    plan?.show(scene, floorId);
  }, [plan, scene, floorId]);
  useEffect(() => {
    plan?.setOverlay(overlay);
  }, [plan, overlay]);
  useEffect(() => (plan && onPick ? plan.onPick(onPick) : undefined), [plan, onPick]);
  useEffect(() => {
    if (!plan || !focus) return;
    const current = plan.getView();
    const height = (focus.width * current.height) / current.width;
    plan.setView({ x: focus.x - focus.width / 2, y: focus.y - height / 2, width: focus.width, height });
  }, [plan, floorId, focus?.x, focus?.y, focus?.width]);

  return <div ref={container} className={className} />;
}

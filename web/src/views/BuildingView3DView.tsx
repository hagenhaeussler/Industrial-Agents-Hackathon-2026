import { BuildingView3D, type BuildingScene, type BuildingView3DOptions, type Overlay, type PickResult } from "@building/view";
import { useEffect, useRef, useState } from "react";

/** React wrapper for the 3D exploded building view. */
export function BuildingView3DView({
  scene,
  focusFloorId,
  overlay,
  onPick,
  options,
  className = "",
}: {
  scene: BuildingScene;
  focusFloorId: string | null;
  overlay: Overlay;
  onPick?: (pick: PickResult | null) => void;
  options?: Partial<BuildingView3DOptions>;
  className?: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<BuildingView3D>();

  useEffect(() => {
    const created = new BuildingView3D(container.current!, options);
    setView(created);
    return () => created.destroy();
  }, []);

  useEffect(() => {
    view?.show(scene);
  }, [view, scene]);
  useEffect(() => {
    view?.setFocusFloor(focusFloorId);
  }, [view, focusFloorId]);
  useEffect(() => {
    view?.setOverlay(overlay);
  }, [view, overlay]);
  useEffect(() => (view && onPick ? view.onPick(onPick) : undefined), [view, onPick]);
  useEffect(() => {
    if (view && options) view.setOptions(options);
  }, [view, options?.labels, options?.assets, options?.floorGap, options?.wallHeight]);

  // The label renderer gives each label a z-index; isolate keeps them below the floating controls.
  return <div ref={container} className={`isolate ${className}`} />;
}

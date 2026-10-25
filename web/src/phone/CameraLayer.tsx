import { Camera, Flag, LocateFixed } from "lucide-react";
import { useEffect } from "react";
import type { Fix } from "../camera/localize";
import { useCamera } from "../camera/useCamera";
import { useLocalization } from "../camera/useLocalization";
import type { Turn } from "../route/directions";

const STATUS_TEXT = { searching: "Finding your position…", located: "Position found", unavailable: undefined };

/**
 * Full-screen camera with the next turn drawn over it. The arrow comes from the route plan. While the camera
 * runs, about one frame per second goes to the localization service; reliable positions arrive through `onFix`.
 */
export function CameraLayer({
  turn,
  buildingId,
  onFix,
}: {
  turn: Turn | undefined;
  buildingId: string;
  onFix: (fix: Fix) => void;
}) {
  const camera = useCamera();
  const live = camera.state.kind === "live";
  const localization = useLocalization(buildingId, camera.videoRef, live, onFix);
  const statusText = live ? STATUS_TEXT[localization] : undefined;

  // Start on entering the camera view; the hook stops the stream when the view closes.
  useEffect(() => {
    void camera.start();
  }, []);

  return (
    <div className="absolute inset-0 -z-10 bg-[#d8d8ce]">
      <video
        ref={camera.videoRef}
        className={`absolute inset-0 size-full object-cover ${live ? "opacity-100" : "opacity-0"}`}
        autoPlay
        playsInline
        muted
        aria-label="Live camera view"
      />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(#131a0d1f,transparent_35%,transparent_60%,#131a0d2e)]" />
      {turn && <TurnOverlay turn={turn} />}
      {statusText && (
        <p
          role="status"
          className="float absolute top-[max(150px,calc(env(safe-area-inset-top)+136px))] left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-[700] whitespace-nowrap"
        >
          <LocateFixed size={13} className={localization === "located" ? "text-accent-deep" : "text-muted"} />
          {statusText}
        </p>
      )}
      {!live && (
        <div className="absolute inset-x-6 top-[40%] mx-auto max-w-[340px]">
          <div className="float grid gap-3 rounded-[18px] p-4 text-center">
            <p className="text-sm leading-relaxed">
              {camera.state.kind === "error"
                ? camera.state.message
                : camera.state.kind === "requesting"
                  ? "Waiting for camera access…"
                  : "Show directions over your camera image."}
            </p>
            {camera.state.kind !== "requesting" && (
              <button
                type="button"
                onClick={() => void camera.start()}
                className="flex items-center justify-center gap-2 rounded-[13px] bg-ink px-4 py-3 text-sm font-[650] text-white"
              >
                <Camera size={18} /> Turn on camera
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** The route arrow from the phone prototype: straight, left or right, or a flag on arrival. */
function TurnOverlay({ turn }: { turn: Turn }) {
  if (turn === "arrive") {
    return (
      <div className="absolute top-[44%] left-1/2 grid size-20 -translate-x-1/2 place-items-center rounded-full border-[7px] border-white/50 bg-accent">
        <Flag size={34} />
      </div>
    );
  }
  const path = turn === "left" ? "M210 690 210 390 100 390" : turn === "right" ? "M210 690 210 390 320 390" : "M210 690 210 300";
  const head =
    turn === "left" ? "m125 366-26 24 26 24" : turn === "right" ? "m295 366 26 24-26 24" : "m183 332 27-32 27 32";
  return (
    <svg
      className="pointer-events-none absolute inset-y-0 left-1/2 h-full w-[min(100%,560px)] -translate-x-1/2"
      viewBox="0 0 420 820"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="routeFade" gradientUnits="userSpaceOnUse" x1="210" y1="700" x2="210" y2="300">
          <stop stopColor="#dcff58" stopOpacity=".15" />
          <stop offset=".65" stopColor="#dcff58" stopOpacity=".65" />
          <stop offset="1" stopColor="#dcff58" stopOpacity=".95" />
        </linearGradient>
      </defs>
      <path d={path} stroke="#26301d" strokeWidth="32" fill="none" strokeLinejoin="round" opacity=".12" />
      <path d={path} stroke="url(#routeFade)" strokeWidth="25" fill="none" strokeLinejoin="round" />
      <path d={head} fill="none" stroke="#e2ff77" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round" />
      <ellipse cx="210" cy="697" rx="18" ry="6" fill="#f1ffbd" />
    </svg>
  );
}

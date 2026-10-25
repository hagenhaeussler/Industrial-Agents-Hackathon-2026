import { Camera, Flag, LocateFixed } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Fix } from "../camera/localize";
import { useCamera } from "../camera/useCamera";
import { useLocalization } from "../camera/useLocalization";
import type { Turn } from "../route/directions";
import { type LiveArrow, signedDeg } from "../route/liveArrow";

const STATUS_TEXT = { searching: "Finding your position…", located: "Position found", unavailable: undefined };

/**
 * Full-screen camera with the way to go drawn over it. While the camera runs, about one frame per second goes to
 * the localization service; reliable positions arrive through `onFix`. With a position, `arrow` points along the
 * route from where the walker looks. Without one, the arrow shows the current step's turn from the route plan.
 */
export function CameraLayer({
  turn,
  arrow,
  buildingId,
  onFix,
}: {
  turn: Turn | undefined;
  arrow: LiveArrow | undefined;
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
      {arrow?.kind === "turn" ? (
        <LiveArrowOverlay turnDeg={arrow.turnDeg} />
      ) : arrow?.kind === "arrive" ? (
        <TurnOverlay turn="arrive" />
      ) : (
        turn && <TurnOverlay turn={turn} />
      )}
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

/**
 * The live arrow: it turns around the screen centre towards the route. The angle unwraps from the last one shown,
 * so a change from 170 to -170 degrees turns 20 degrees instead of a full circle.
 */
function LiveArrowOverlay({ turnDeg }: { turnDeg: number }) {
  const shown = useRef(turnDeg);
  const angle = shown.current + signedDeg(turnDeg - shown.current);
  useEffect(() => {
    shown.current = angle;
  });
  return (
    <svg
      className="pointer-events-none absolute inset-x-0 top-[22%] mx-auto h-[56%] w-full max-w-[560px]"
      viewBox="0 0 420 420"
      aria-label={`Route ${describeTurn(turnDeg)}`}
      role="img"
    >
      {/* SVG angles turn clockwise on screen, the arrow's counterclockwise. */}
      <g
        style={{ transform: `rotate(${-angle}deg)`, transformOrigin: "210px 210px", transition: "transform 0.4s ease-out" }}
      >
        <path d="M210 330 210 110" stroke="#26301d" strokeWidth="40" opacity=".12" strokeLinecap="round" />
        <path d="M210 330 210 110" stroke="#dcff58" strokeWidth="30" strokeOpacity=".9" strokeLinecap="round" />
        <path
          d="m160 150 50-56 50 56"
          fill="none"
          stroke="#e2ff77"
          strokeWidth="22"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
}

function describeTurn(turnDeg: number): string {
  if (Math.abs(turnDeg) <= 30) return "straight ahead";
  if (Math.abs(turnDeg) >= 150) return "behind you";
  return turnDeg > 0 ? "to the left" : "to the right";
}

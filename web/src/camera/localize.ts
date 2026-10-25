/** The localization service's answer, passed through by `POST /api/buildings/{id}/localize`. */
export interface LocalizeResult {
  building_id: string;
  located: boolean;
  /** At least 30 matched points. Unreliable results had a median error of 4.3 m; ignore them. */
  reliable: boolean;
  floor_id: string | null;
  space_id: string | null;
  /** Plan metres, like building.json. */
  position: [number, number] | null;
  height_m: number | null;
  /** Viewing direction, counterclockwise from +x. */
  heading_deg: number | null;
  num_inliers: number;
}

/** A position the guide can use: a reliable result with a space and a point. */
export interface Fix {
  floorId: string;
  spaceId: string;
  x: number;
  y: number;
  headingDeg: number | undefined;
}

export function toFix(result: LocalizeResult): Fix | undefined {
  if (!result.located || !result.reliable || !result.floor_id || !result.space_id || !result.position) return undefined;
  return {
    floorId: result.floor_id,
    spaceId: result.space_id,
    x: result.position[0],
    y: result.position[1],
    headingDeg: result.heading_deg ?? undefined,
  };
}

/** Frame size with the long side at most `limit` pixels, keeping the aspect ratio. */
export function frameSize(width: number, height: number, limit = 1024): { width: number; height: number } {
  const scale = Math.min(1, limit / Math.max(width, height));
  return { width: Math.round(width * scale), height: Math.round(height * scale) };
}

/** The current video frame as an upright JPEG, or null before the video has a frame. */
export async function captureFrame(video: HTMLVideoElement, canvas: HTMLCanvasElement): Promise<Blob | null> {
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || !video.videoWidth) return null;
  const size = frameSize(video.videoWidth, video.videoHeight);
  canvas.width = size.width;
  canvas.height = size.height;
  canvas.getContext("2d")?.drawImage(video, 0, 0, size.width, size.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
}

export type LocalizeOutcome =
  | { kind: "result"; result: LocalizeResult }
  /** 404 (no map for this building) or 503 (not configured or not reachable): stop sending. */
  | { kind: "unavailable" }
  | { kind: "failed" };

export async function postFrame(buildingId: string, frame: Blob, signal?: AbortSignal): Promise<LocalizeOutcome> {
  const response = await fetch(`/api/buildings/${encodeURIComponent(buildingId)}/localize`, {
    method: "POST",
    headers: { "Content-Type": "image/jpeg" },
    body: frame,
    signal,
  });
  if (response.status === 404 || response.status === 503) return { kind: "unavailable" };
  if (!response.ok) return { kind: "failed" };
  return { kind: "result", result: await response.json() };
}

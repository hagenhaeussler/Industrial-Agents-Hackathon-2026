const VOICE_SERVER: string = import.meta.env.VITE_VOICE_SERVER ?? "";
export const PHOTO_URL = `${VOICE_SERVER}/api/voice/photo`;

export interface PhotoResult {
  status: "found" | "not_visible" | "uncertain";
  answer: string;
  audio_base64: string | null;
  audio_type: "audio/mpeg";
  speech_error: string | null;
}

/** Upright, stripped of metadata and small enough to send from a phone. The original stays on the device. */
export async function preparePhoto(file: File): Promise<Blob> {
  if (!file.size || file.size > 50 * 1024 * 1024) throw new Error("Choose a photo smaller than 50 MiB.");
  if (!["image/jpeg", "image/png"].includes(file.type)) throw new Error("Choose a JPEG or PNG photo.");
  const image = await createImageBitmap(file, { imageOrientation: "from-image" });
  try {
    const scale = Math.min(1, 1600 / Math.max(image.width, image.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Your browser could not prepare the photo.");
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const photo = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", .88));
    if (!photo || photo.size > 4 * 1024 * 1024) throw new Error("The photo is too large. Try a smaller image.");
    return photo;
  } finally { image.close(); }
}

export async function analyzePhoto(photo: Blob, question: string, signal: AbortSignal): Promise<PhotoResult> {
  const response = await fetch(`${PHOTO_URL}?${new URLSearchParams({ question })}`, {
    method: "POST", headers: { "Content-Type": "image/jpeg" }, body: photo, signal, cache: "no-store",
  });
  const body = await response.json().catch(() => undefined);
  if (!response.ok) throw new Error(typeof body?.error === "string" ? body.error : "The photo could not be analyzed. Try again.");
  if (!["found", "not_visible", "uncertain"].includes(body?.status) || typeof body?.answer !== "string" || !body.answer.trim()
    || (body.audio_base64 !== null && typeof body.audio_base64 !== "string") || body.audio_type !== "audio/mpeg") {
    throw new Error("The photo service returned an invalid answer. Try again.");
  }
  return body;
}

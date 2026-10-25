import { Camera, LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Sheet } from "../ui/Sheet";
import { analyzePhoto, PHOTO_URL, preparePhoto, type PhotoResult } from "./photo";

/** A deliberate capture/upload, separate from the frames used to localize. Nothing is sent until Analyze. */
export function PhotoQuestion({ open, onClose, onAnalyze }: { open: boolean; onClose: () => void; onAnalyze: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const request = useRef<AbortController | undefined>(undefined);
  const [question, setQuestion] = useState("Where is Dido?");
  const [photo, setPhoto] = useState<Blob>();
  const [preview, setPreview] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [result, setResult] = useState<PhotoResult>();
  const [available, setAvailable] = useState<boolean>();
  const preparing = useRef(0);
  const audio = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (!open) return;
    const check = new AbortController();
    setAvailable(undefined);
    void fetch(PHOTO_URL, { signal: check.signal, cache: "no-store" })
      .then(async (response) => setAvailable(response.ok && (await response.json()).available === true))
      .catch(() => { if (!check.signal.aborted) setAvailable(false); });
    return () => {
      check.abort();
      request.current?.abort();
      preparing.current += 1;
      audio.current?.pause();
      setPhoto(undefined); setResult(undefined); setError(undefined); setBusy(false);
    };
  }, [open]);
  useEffect(() => {
    if (!photo) { setPreview(undefined); return; }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);
  useEffect(() => {
    // Mobile browsers may require the visible Play control after the network request finishes.
    if (result?.audio_base64) void audio.current?.play().catch(() => {});
  }, [result]);

  async function choose(file: File) {
    const sequence = ++preparing.current;
    setBusy(true); setError(undefined); setResult(undefined);
    try {
      const next = await preparePhoto(file);
      if (sequence === preparing.current) setPhoto(next);
    } catch {
      if (sequence === preparing.current) setError("Could not open that photo. Choose a JPEG or PNG and try again.");
    } finally { if (sequence === preparing.current) setBusy(false); }
  }

  async function analyze() {
    if (!photo || busy || !question.trim()) return;
    const active = new AbortController();
    request.current = active;
    onAnalyze(); // Stop navigation speech before the photo answer can play.
    setBusy(true); setError(undefined); setResult(undefined);
    try {
      const answer = await analyzePhoto(photo, question.trim(), active.signal);
      if (!active.signal.aborted) setResult(answer);
    } catch (cause) {
      if (!active.signal.aborted) setError(cause instanceof Error ? cause.message : "Could not reach the photo service.");
    } finally { if (!active.signal.aborted) { setBusy(false); request.current = undefined; } }
  }

  return <Sheet open={open} onClose={onClose} title="Find an object" subtitle="Take a photo when you reach your destination.">
    <div className="grid gap-4">
      <label className="grid gap-2 text-sm font-[650]">What are you looking for?
        <input value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={200} disabled={busy}
          className="rounded-xl border border-line bg-field p-3 font-normal" />
      </label>
      <p className="text-xs leading-relaxed text-muted">For an unfamiliar name like Dido, describe its appearance or include its label in the photo.</p>
      <input ref={input} hidden type="file" accept="image/jpeg,image/png" capture="environment" aria-label="Object photo" disabled={busy}
        onChange={(event) => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ""; if (file) void choose(file); }} />
      <button type="button" disabled={busy} onClick={() => input.current?.click()}
        className="flex items-center justify-center gap-2 rounded-xl bg-field p-3 text-sm font-[650]">
        <Camera size={18} /> {photo ? "Retake photo" : "Take photo"}
      </button>
      {preview && <img src={preview} alt="Photo to analyze" className="max-h-[30svh] w-full rounded-xl object-contain" />}
      <p className="text-xs leading-relaxed text-muted">Analyze sends this photo to Claude and the answer to ElevenLabs for speech. The app does not save the photo. Navigation voice pauses while you check it.</p>
      {available === false && <p role="status" className="text-sm text-muted">Photo answers are not available on the server yet. Please try again after setup.</p>}
      <button type="button" disabled={!photo || busy || !question.trim() || available !== true} onClick={() => void analyze()}
        className="flex items-center justify-center gap-2 rounded-xl bg-ink p-3 text-sm font-[700] text-white disabled:opacity-40">
        {busy && <LoaderCircle size={18} className="animate-spin" />} {busy ? "Checking photo…" : "Analyze and speak"}
      </button>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {result && <div role="status" className="grid gap-3 rounded-xl bg-field p-4">
        <p className="text-sm leading-relaxed">{result.answer}</p>
        {result.audio_base64 && <audio ref={audio} controls preload="auto" aria-label="Spoken photo answer"
          src={`data:audio/mpeg;base64,${result.audio_base64}`} className="h-10 w-full" />}
        {result.speech_error && <p className="text-xs text-muted">{result.speech_error}</p>}
      </div>}
    </div>
  </Sheet>;
}

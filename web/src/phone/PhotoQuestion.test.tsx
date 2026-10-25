import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PhotoQuestion } from "./PhotoQuestion";
import { analyzePhoto, preparePhoto } from "./photo";

vi.mock("./photo", async (original) => ({ ...await original<typeof import("./photo")>(), preparePhoto: vi.fn() }));
const prepare = vi.mocked(preparePhoto);
const answer = { status: "found", answer: "The red cup is left of the book.", audio_base64: "SUQz", audio_type: "audio/mpeg", speech_error: null };

beforeEach(() => {
  prepare.mockReset().mockResolvedValue(new Blob(["jpeg"], { type: "image/jpeg" }));
  vi.spyOn(HTMLDialogElement.prototype, "showModal").mockImplementation(function (this: HTMLDialogElement) { this.open = true; });
  vi.spyOn(HTMLDialogElement.prototype, "close").mockImplementation(function (this: HTMLDialogElement) { this.open = false; });
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:photo");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function choosePhoto() {
  fireEvent.change(screen.getByLabelText("Object photo"), { target: { files: [new File(["jpeg"], "photo.jpg", { type: "image/jpeg" })] } });
}

it("only uploads after Analyze, pauses navigation voice and exposes speech playback", async () => {
  const fetch = vi.fn(async (_url: string, init?: RequestInit) => Response.json(init?.method === "POST" ? answer : { available: true }));
  vi.stubGlobal("fetch", fetch);
  const stop = vi.fn();
  render(<PhotoQuestion open onClose={vi.fn()} onAnalyze={stop} />);
  choosePhoto();
  await screen.findByAltText("Photo to analyze");
  expect(fetch).toHaveBeenCalledTimes(1); // capability only: selecting a photo does not transmit it
  expect(stop).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Where is the red cup?" } });
  fireEvent.click(screen.getByRole("button", { name: "Analyze and speak" }));
  expect(await screen.findByText(answer.answer)).toBeTruthy();
  expect(stop).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[1]![0]).toContain("question=Where+is+the+red+cup%3F");
  expect(fetch.mock.calls[1]![1]?.body).toBeInstanceOf(Blob);
  expect(screen.getByLabelText("Spoken photo answer").getAttribute("src")).toBe("data:audio/mpeg;base64,SUQz");
});

it("keeps a clear answer when speech fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => Response.json(init?.method === "POST"
    ? { ...answer, audio_base64: null, speech_error: "Speech unavailable. Read the answer." } : { available: true })));
  render(<PhotoQuestion open onClose={vi.fn()} onAnalyze={vi.fn()} />);
  choosePhoto(); await screen.findByAltText("Photo to analyze");
  fireEvent.click(screen.getByRole("button", { name: "Analyze and speak" }));
  expect(await screen.findByText(answer.answer)).toBeTruthy();
  expect(screen.getByText("Speech unavailable. Read the answer.")).toBeTruthy();
  expect(screen.queryByLabelText("Spoken photo answer")).toBeNull();
});

it("cancels on close and ignores a late answer", async () => {
  let resolve: (response: Response) => void = () => {};
  let signal: AbortSignal | undefined;
  vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method !== "POST") return Response.json({ available: true });
    signal = init.signal as AbortSignal;
    return new Promise<Response>((settle) => { resolve = settle; });
  }));
  const { rerender } = render(<PhotoQuestion open onClose={vi.fn()} onAnalyze={vi.fn()} />);
  choosePhoto(); await screen.findByAltText("Photo to analyze");
  fireEvent.click(screen.getByRole("button", { name: "Analyze and speak" }));
  await waitFor(() => expect(signal).toBeDefined());
  rerender(<PhotoQuestion open={false} onClose={vi.fn()} onAnalyze={vi.fn()} />);
  expect(signal?.aborted).toBe(true);
  await act(async () => resolve(Response.json(answer)));
  expect(screen.queryByText(answer.answer)).toBeNull();
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:photo");
});

it("blocks paid attempts when the server is not configured", async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json({ available: false }));
  vi.stubGlobal("fetch", fetch);
  render(<PhotoQuestion open onClose={vi.fn()} onAnalyze={vi.fn()} />);
  choosePhoto(); await screen.findByAltText("Photo to analyze");
  expect(screen.getByRole<HTMLButtonElement>("button", { name: "Analyze and speak" }).disabled).toBe(true);
  expect(screen.getByText(/not available on the server/)).toBeTruthy();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("rejects an invalid provider response and preserves a useful server error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(Response.json({ status: "found", answer: "" }))
    .mockResolvedValueOnce(Response.json({ error: "Today's photo demo limit has been reached." }, { status: 429 })));
  await expect(analyzePhoto(new Blob(), "Where?", new AbortController().signal)).rejects.toThrow("invalid answer");
  await expect(analyzePhoto(new Blob(), "Where?", new AbortController().signal)).rejects.toThrow("limit has been reached");
});

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { captureFrame, postFrame, type LocalizeOutcome } from "./localize";
import { useLocalization } from "./useLocalization";

vi.mock("./localize", async (original) => ({
  ...(await original<typeof import("./localize")>()),
  captureFrame: vi.fn(),
  postFrame: vi.fn(),
}));

const capture = vi.mocked(captureFrame);
const post = vi.mocked(postFrame);
const video = { current: document.createElement("video") };
const frame = new Blob(["jpeg"]);

function run() {
  return renderHook(() => useLocalization("b1", video, true, () => {}));
}

/** Let pending promises settle, then move the clock. */
async function advance(ms: number) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
}

beforeEach(() => {
  vi.useFakeTimers();
  capture.mockResolvedValue(frame);
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("useLocalization", () => {
  it("stops for good when localization is unavailable", async () => {
    post.mockResolvedValue({ kind: "unavailable" });
    const { result } = run();
    await advance(10_000);
    expect(result.current).toBe("unavailable");
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("waits longer after each failure and keeps trying", async () => {
    post.mockResolvedValue({ kind: "failed" });
    run();
    await advance(0);
    expect(post).toHaveBeenCalledTimes(1);
    await advance(2000); // 2 s after the first failure
    expect(post).toHaveBeenCalledTimes(2);
    await advance(3999); // 4 s after the second
    expect(post).toHaveBeenCalledTimes(2);
    await advance(1);
    expect(post).toHaveBeenCalledTimes(3);
  });

  it("never sends a second frame while one is on its way", async () => {
    let answer: (outcome: LocalizeOutcome) => void = () => {};
    post.mockImplementation(() => new Promise((resolve) => (answer = resolve)));
    run();
    await advance(5000);
    expect(post).toHaveBeenCalledTimes(1);
    answer({ kind: "failed" });
    await advance(2000);
    expect(post).toHaveBeenCalledTimes(2);
  });

  it("sends nothing more after unmount, even when a capture was still running", async () => {
    let captured: (blob: Blob | null) => void = () => {};
    capture.mockImplementation(() => new Promise((resolve) => (captured = resolve)));
    const { unmount } = run();
    await advance(0);
    unmount();
    captured(null);
    capture.mockResolvedValue(frame);
    await advance(10_000);
    expect(capture).toHaveBeenCalledTimes(1);
    expect(post).not.toHaveBeenCalled();
  });
});

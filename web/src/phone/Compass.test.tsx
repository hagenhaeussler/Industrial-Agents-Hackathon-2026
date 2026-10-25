import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Compass } from "./Compass";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function sendHeading() {
  const event = new Event("ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation");
  Object.assign(event, { webkitCompassHeading: 42 });
  act(() => window.dispatchEvent(event));
}

it("shows headings without a compass tap and stops listening on unmount", () => {
  vi.stubGlobal("DeviceOrientationEvent", class extends Event {});
  const { unmount } = render(<Compass />);
  sendHeading();
  expect(screen.getByRole("button", { name: "Heading 42 degrees" })).toBeTruthy();
  const remove = vi.spyOn(window, "removeEventListener");
  unmount();
  expect(remove).toHaveBeenCalledWith(expect.stringMatching(/^deviceorientation/), expect.any(Function));
  remove.mockRestore();
});

it("requests permission on the first page interaction", async () => {
  const requestPermission = vi.fn().mockResolvedValue("granted");
  vi.stubGlobal("DeviceOrientationEvent", Object.assign(class extends Event {}, { requestPermission }));
  render(<Compass />);
  expect(requestPermission).not.toHaveBeenCalled();
  await act(async () => fireEvent.click(document.body));
  await act(async () => fireEvent.click(document.body));
  expect(requestPermission).toHaveBeenCalledTimes(1);
});

it("allows a compass retry after a rejected permission request", async () => {
  const requestPermission = vi.fn().mockRejectedValueOnce(new Error("Gesture required")).mockResolvedValue("granted");
  vi.stubGlobal("DeviceOrientationEvent", Object.assign(class extends Event {}, { requestPermission }));
  render(<Compass />);
  await act(async () => fireEvent.click(document.body));
  await act(async () => fireEvent.click(screen.getByRole("button")));
  expect(requestPermission).toHaveBeenCalledTimes(2);
});

it("hides the compass when orientation is unsupported", () => {
  vi.stubGlobal("DeviceOrientationEvent", undefined);
  const { container } = render(<Compass />);
  expect(container.innerHTML).toBe("");
});

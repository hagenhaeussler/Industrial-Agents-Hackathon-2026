import { afterEach, describe, expect, it, vi } from "vitest";
import { importBuilding } from "./importBuilding";

afterEach(() => vi.unstubAllGlobals());

describe("importBuilding", () => {
  it("sends the original file as JSON and returns the stored building ID", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ id: "new-building", status: "imported" }, { status: 201 }));
    vi.stubGlobal("fetch", fetch);
    const file = new File(['{"building": {}}'], "building.json", { type: "" });
    expect(await importBuilding(file)).toEqual({ id: "new-building", status: "imported" });
    expect(fetch).toHaveBeenCalledWith("/api/buildings/import", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: file,
    });
  });

  it.each([
    [new File(["{}"], "equipment.csv"), "Choose a file named building.json."],
    [new File([], "building.json"), "The file is empty."],
    [new File([new Uint8Array(20 * 1024 * 1024 + 1)], "building.json"), "20 MiB"],
  ])("rejects invalid files before sending: %s", async (file, message) => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(importBuilding(file)).rejects.toThrow(message);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("allows the exact size limit", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ id: "large", status: "imported" })));
    const file = new File([new Uint8Array(20 * 1024 * 1024)], "building.json");
    expect((await importBuilding(file)).id).toBe("large");
  });

  it("accepts an identical building without treating it as a failed import", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ id: "existing", status: "unchanged" })));
    expect(await importBuilding(new File(["{}"], "building.json"))).toEqual({ id: "existing", status: "unchanged" });
  });

  it.each([409, 413, 422, 503])("shows the server reason for HTTP %s", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ detail: "Specific reason" }, { status })));
    await expect(importBuilding(new File(["{}"], "building.json"))).rejects.toThrow("Specific reason");
  });

  it("handles a proxy error that returns HTML", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<h1>Unavailable</h1>", { status: 502 })));
    await expect(importBuilding(new File(["{}"], "building.json"))).rejects.toThrow("Import failed (502)");
  });

  it("gives a retry message when the connection fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(importBuilding(new File(["{}"], "building.json"))).rejects.toThrow("Check your connection and try again");
  });

  it.each([null, [], {}, { id: "", status: "imported" }, { id: "new", status: "failed" }])(
    "rejects an invalid success response: %s", async (body) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(body)));
      await expect(importBuilding(new File(["{}"], "building.json"))).rejects.toThrow("invalid import response");
    },
  );
});

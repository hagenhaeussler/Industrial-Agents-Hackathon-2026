import { describe, expect, it } from "vitest";

import { fitLabel } from "./labels";

describe("fitLabel", () => {
  it("uses the name when it fits, the ref when only that fits, and nothing in tiny rooms", () => {
    expect(fitLabel("Office 0.01", "0.01", 2)?.text).toBe("Office 0.01");
    expect(fitLabel("Coordinate measuring lab 0.21", "0.21", 0.6)?.text).toBe("0.21");
    expect(fitLabel("WC", "", 0.1)).toBeNull();
  });
});

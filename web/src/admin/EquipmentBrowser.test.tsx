import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixture } from "../../../packages/building-view/src/testing/fixture";
import { EquipmentBrowser } from "./EquipmentBrowser";

afterEach(cleanup);

function equipmentFixture() {
  const building = fixture();
  building.floors[0]!.name = "Upper floor";
  const desk = building.assets[0]!;
  building.assets.push({ ...desk, id: "D2", name: desk.name, floor_id: "F1", space_id: "C" });
  return building;
}

describe("EquipmentBrowser", () => {
  it("selects the exact item when names repeat on different floors", () => {
    const building = equipmentFixture();
    const onSelect = vi.fn();
    render(<EquipmentBrowser building={building} selectedId={undefined} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: "desk 2" }));
    fireEvent.click(screen.getByRole("button", { name: /D2/ }));
    expect(onSelect).toHaveBeenCalledWith(building.assets[1]);
  });

  it("marks only the selected item", () => {
    render(<EquipmentBrowser building={equipmentFixture()} selectedId="D2" onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "desk 2" }));
    expect(screen.getAllByRole("button", { pressed: true }).map((button) => button.textContent)).toEqual([
      "Desk 0.01-AD2Lift · Upper floor",
    ]);
  });

  it("keeps types after the eighth accessible and includes every item", () => {
    const building = fixture();
    const asset = building.assets[0]!;
    building.assets = Array.from({ length: 9 }, (_, index) => ({ ...asset, id: `T${index}`, type: `type_${index}` }));
    building.assets.push(...Array.from({ length: 45 }, (_, index) => ({ ...asset, id: `D${index}` })));
    render(<EquipmentBrowser building={building} selectedId={undefined} onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "type 8 1" }));
    expect(screen.getByRole("button", { name: /T8/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "desk 45" }));
    expect(within(screen.getByRole("list", { name: "desk" })).getAllByRole("button")).toHaveLength(45);
  });

  it.each(["d2", "desk upper", "lift", "desk 0.01-a upper"])("finds equipment by ID, name, type and location: %s", (text) => {
    render(<EquipmentBrowser building={equipmentFixture()} selectedId={undefined} onSelect={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Search equipment" }), { target: { value: text } });
    expect(screen.getAllByRole("button", { pressed: false }).map((button) => button.textContent)).toEqual([
      "Desk 0.01-AD2Lift · Upper floor",
    ]);
  });

  it("shows all matching items and restores type browsing when search is cleared", () => {
    render(<EquipmentBrowser building={equipmentFixture()} selectedId={undefined} onSelect={vi.fn()} />);
    const input = screen.getByRole("textbox", { name: "Search equipment" });
    fireEvent.change(input, { target: { value: "desk" } });
    expect(screen.getAllByRole("button", { pressed: false })).toHaveLength(2);
    fireEvent.change(input, { target: { value: "" } });
    expect(screen.getByRole("button", { name: "desk 2", expanded: false })).toBeTruthy();
  });

  it("shows a message when no equipment matches", () => {
    render(<EquipmentBrowser building={fixture()} selectedId={undefined} onSelect={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Search equipment" }), { target: { value: "missing" } });
    expect(screen.getByRole("status").textContent).toBe("No matching equipment.");
  });

  it("handles a building with no equipment", () => {
    const building = fixture();
    building.assets = [];
    render(<EquipmentBrowser building={building} selectedId={undefined} onSelect={vi.fn()} />);
    expect(screen.getByRole("status").textContent).toBe("No equipment in this building.");
  });
});

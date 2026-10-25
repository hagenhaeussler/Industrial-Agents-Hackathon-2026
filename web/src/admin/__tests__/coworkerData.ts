import type { Coworker, CoworkerSession } from "../../api/coworkers";

export function coworker(overrides: Partial<Coworker> = {}): Coworker {
  return {
    id: "maya", name: "Maya Chen", role: "Facility manager", color: "#b56843",
    position: { floorId: "ground", x: 1, y: 2, spaceId: "lobby", spaceName: "Lobby" },
    activity: "Checking the building", journey: null, ...overrides,
  };
}

export function coworkerSession(overrides: Partial<CoworkerSession> = {}): CoworkerSession {
  return {
    sessionId: "session-one", serverTime: Date.now(),
    members: [coworker(), coworker({ id: "jonas", name: "Jonas Weber", role: "Maintenance", color: "#397a91" })],
    messages: [], chatAvailable: true, unavailableReason: null, totalCostUsd: 0,
    ...overrides,
  };
}

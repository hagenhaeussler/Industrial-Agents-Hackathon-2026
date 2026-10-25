// Sample team content for the workspace. Settings marks it as sample content; nothing here is sent anywhere.

export interface Member {
  id: string;
  name: string;
  role: string;
  color: string;
  status: "online" | "away";
}

export const MEMBERS: Member[] = [
  { id: "maya", color: "#b56843", name: "Maya Chen", role: "Facility manager", status: "online" },
  { id: "jonas", color: "#397a91", name: "Jonas Weber", role: "Maintenance", status: "online" },
  { id: "priya", color: "#8568a6", name: "Priya Nair", role: "Safety officer", status: "away" },
  { id: "leo", color: "#b58c26", name: "Leo Martin", role: "Visitor desk", status: "online" },
];

export const CHANNELS = ["facility-ops", "maintenance", "visitors", "safety"] as const;
export type Channel = (typeof CHANNELS)[number];

export interface Post {
  id: string;
  channel: Channel;
  author: string;
  text: string;
  time: string;
}

export const SEED_POSTS: Post[] = [
  { id: "p1", channel: "facility-ops", author: "maya", text: "Morning! Delivery for the assembly area arrives at 10:30.", time: "08:12" },
  { id: "p2", channel: "facility-ops", author: "jonas", text: "I'll take the lift route with the pallet, the stairs are busy.", time: "08:15" },
  { id: "p3", channel: "maintenance", author: "jonas", text: "Checking the printers in the additive zone after lunch.", time: "09:02" },
  { id: "p4", channel: "visitors", author: "leo", text: "Two visitors for the quality lab. I'll send them the route by QR code.", time: "09:40" },
  { id: "p5", channel: "safety", author: "priya", text: "Reminder: keep the corridor next to the staircase clear.", time: "07:55" },
];

export function memberName(id: string): string {
  return MEMBERS.find((member) => member.id === id)?.name ?? "You";
}

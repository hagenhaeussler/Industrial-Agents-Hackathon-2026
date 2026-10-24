/**
 * Payload types from CONTRACTS C1 (§5, §7, §8, §9, §10).
 * The generated OpenAPI types (`schema.gen.ts`) keep most payloads as open dictionaries; these are the
 * precise contract shapes, and `schema.check.ts` keeps them assignable to the generated ones.
 */
export type Point = [number, number];

export type Floor = { id: string; level: number; name: string; elevation_m: number; height_m: number };
export type Space = { id: string; floor_id: string; type: string; room_type: string; name: string; ref: string; polygon: Point[]; synthetic?: boolean };
export type Opening = { id: string; floor_id: string; space_ids: string[]; kind: 'door' | 'opening' | 'entrance' | string; position: Point; width_m: number; step_free: boolean };
export type Connector = { id: string; kind: 'stairs' | 'lift' | string; name: string; floor_ids: string[]; space_ids: string[]; step_free: boolean };
export type Asset = { id: string; name: string; category: string; type: string; space_id: string; floor_id: string; position: Point; footprint?: { width_m: number; depth_m: number; rotation_deg: number } };
export type BuildingInfo = { id: string; name: string; source?: string; split?: string };
export type Building = { building: BuildingInfo; floors: Floor[]; spaces: Space[]; openings: Opening[]; vertical_connectors: Connector[]; assets: Asset[] };

export type BuildingSummary = { id: string; name: string; source: string; split: string; floors: number; has_lift: boolean; has_stairs: boolean };
export type Snapshot = {
  building: Building;
  building_version: number;
  content_hash: string;
  closed: string[];
  derived: { anchors: Record<string, Point>; areas_m2: Record<string, number> };
};

export type Constraints = { step_free: boolean; min_door_width_m: number; closed: string[]; no_transit_room_types: string[] };
export type Segment =
  | { floor_id: string; kind: 'walk'; space_id: string; points: Point[]; length_m: number }
  | { floor_id: string; kind: 'lift' | 'stairs'; element_id: string; points: Point[]; to_floor_id: string; length_m: number };
export type ManeuverKind = 'depart' | 'straight' | 'turn_left' | 'turn_right' | 'slight_left' | 'slight_right' | 'u_turn' | 'enter' | 'take_lift' | 'take_stairs' | 'arrive';
export type Maneuver = { i: number; kind: ManeuverKind; floor_id: string; at: Point; distance_m: number; text: string; landmark: string | null; element_id: string | null };
type Stamp = { constraints: Constraints; profile: string; building_id: string; building_version: number; content_hash: string; geometry?: 'provisional' | string };
export type ReachableRoute = Stamp & {
  reachable: true; from_space_id: string; to_space_id: string; length_m: number;
  space_path: string[]; element_path: string[]; node_path: string[]; segments: Segment[]; maneuvers: Maneuver[];
};
export type UnreachableReason = 'no_step_free_path' | 'blocked_by_closure' | 'too_narrow' | 'disconnected';
export type UnreachableRoute = Stamp & { reachable: false; from_space_id: string; to_space_id: string; reason: UnreachableReason; blocking_ids: string[] };
export type RouteResult = ReachableRoute | UnreachableRoute;

export type StopStatus = 'pending' | 'collected';
export type TourStop = { stop_id: string; space_id: string; asset_ids: string[]; label: string; status: StopStatus };
export type TourPoint = { space_id: string; point: Point; floor_id: string; source: PositionSource };
export type OrderPolicy = 'optimized_exact' | 'optimized_heuristic' | 'fixed';
export type UnreachableStop = { stop_id: string; reason: UnreachableReason | string; blocking_ids?: string[] };
export type Tour = {
  tour_id: string; revision: number; status: string; building_id: string; building_version: number;
  order_policy: OrderPolicy; start: TourPoint; end: TourPoint | null; stops: TourStop[]; order: string[];
  legs: RouteResult[]; length_m: number; unreachable_stops: UnreachableStop[];
  changed_because: { event_id: string; summary: string } | null; profile: string; constraints: Constraints;
  mobility_profile?: MobilityProfile;
};

export type ErrorCode = 'ambiguous' | 'not_found' | 'no_route' | 'invalid_args' | 'version_conflict' | 'forbidden' | 'not_available' | 'internal';
export type Candidate = { id: string; name: string; floor_id?: string; floor?: string; kind?: string };
export type Display = { kind: string; tour_id?: string; asset_ids?: string[]; space_ids?: string[]; space_id?: string; floor_id?: string; [key: string]: unknown };
export type TraceStep = { fn: string; args: Record<string, unknown>; ms: number };
export type ToolResponse = {
  ok: boolean; tool: string; request_id: string; building_id?: string; building_version: number;
  result?: Record<string, unknown>; speech?: string; display?: Display; trace?: TraceStep[];
  error?: { code: ErrorCode; message: string; candidates?: Candidate[] };
};
export type ChatReply = { reply: string; tool_calls: ToolResponse[]; display: Display | null };

export type MobilityProfile = 'walk' | 'wheelchair' | 'pram' | 'trolley';
export type PositionSource = 'desk' | 'tour_start' | 'marker' | 'manual';
export type Position = { space_id: string; floor_id?: string; point?: Point; heading_deg?: number | null; source: PositionSource; marker_id?: string | null; confidence: 'high' | 'medium' | 'low'; updated_at?: string };
export type Device = 'desk' | 'phone';
export type Role = 'navigator' | 'admin';
export type Session = { session_id: string; building_id: string; device: Device; role: Role; profile: MobilityProfile | string; constraints: Constraints; position: Position | null; active_tour_id: string | null; updated_at?: string };
export type Marker = { marker_id: string; building_id: string; floor_id: string; space_id: string; point: Point; heading_deg: number; label: string };

export type BuildingEvent = { event_id: string; kind: string; edit: Record<string, unknown>; summary: string };
/** Public projection (C8): no `session_id`. */
export type BuildingEventRecord = BuildingEvent & { building_id: string; building_version: number; undoes: string | null; op_id: string | null; proposal_id: string | null; author_role: string; created_at: string };
export type ValidationItem = { code: string; path: string; message: string };
export type Validation = { ok: boolean; errors: ValidationItem[]; warnings: ValidationItem[]; stats: Record<string, number> };
export type EditAction = 'close' | 'open' | 'add_door' | 'move_asset' | 'set_room_type';
export type EditPreview = {
  proposal_id: string; edit: { action: EditAction; target: string; second_target?: string | null; value?: string | null }; summary: string; base_version: number;
  effects: { active_tours_affected: number; tours: { tour_id: string; before_m: number; after_m: number | null; reachable_after: boolean }[]; newly_unreachable_spaces: number };
};
export type ServerMessage =
  | { type: 'hello'; building_id: string; building_version: number }
  | { type: 'building_changed'; building_id: string; building_version: number; event: BuildingEvent; at: string }
  | { type: 'building_reset'; building_id: string; building_version: number }
  | { type: 'tour_updated'; tour_id: string; revision: number }
  | { type: 'tour_opened'; tour_id: string; device: Device };

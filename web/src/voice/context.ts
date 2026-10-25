export interface Place {
  id: string;
  name: string;
}

/** A confirmed position and the destination displayed by the app. */
export interface VoiceContext {
  buildingId: string;
  position?: Place;
  destination?: Place;
}

export function dynamicVariables(context: VoiceContext): Record<string, string> {
  return {
    building_id: context.buildingId,
    current_space_id: context.position?.id ?? "",
    current_space_name: context.position?.name ?? "",
    destination_id: context.destination?.id ?? "",
    destination_name: context.destination?.name ?? "",
  };
}

/** A complete replacement, including explicit unknown values. This is data, not a new request. */
export function contextUpdate(context: VoiceContext): string {
  return JSON.stringify({
    type: "app_context",
    current_space: context.position ?? null,
    displayed_destination: context.destination ?? null,
  });
}

import type { BuildingImport } from "@locora/view";
import { useMutation, useQueryClient } from "@tanstack/react-query";

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** Send the file as JSON. The server owns format and reference validation. */
export async function importBuilding(file: File): Promise<BuildingImport> {
  if (file.name !== "building.json") throw new Error("Choose a file named building.json.");
  if (file.size === 0) throw new Error("The file is empty. Choose a building.json file.");
  if (file.size > MAX_UPLOAD_BYTES) throw new Error("The file exceeds the 20 MiB limit.");

  let response: Response;
  try {
    response = await fetch("/api/buildings/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: file,
    });
  } catch {
    throw new Error("Could not reach the server. Check your connection and try again.");
  }
  const body: unknown = await response.json().catch(() => undefined);
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null && "detail" in body ? body.detail : undefined;
    throw new Error(typeof detail === "string" ? detail : `Import failed (${response.status}). Try again.`);
  }
  if (
    typeof body !== "object" || body === null ||
    !("id" in body) || typeof body.id !== "string" || !body.id.trim() ||
    !("status" in body) || (body.status !== "imported" && body.status !== "unchanged")
  ) {
    throw new Error("The server returned an invalid import response. Try the upload again.");
  }
  return { id: body.id, status: body.status };
}

export function useImportBuilding() {
  const queries = useQueryClient();
  return useMutation({
    mutationFn: importBuilding,
    retry: false,
    onSuccess: async ({ id }) => {
      await Promise.all([
        queries.invalidateQueries({ queryKey: ["buildings"] }),
        queries.invalidateQueries({ queryKey: ["building", id], exact: true }),
      ]);
    },
  });
}

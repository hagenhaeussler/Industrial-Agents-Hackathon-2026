import { Upload } from "lucide-react";
import { useRef } from "react";
import { useImportBuilding } from "../api/importBuilding";
import { navigate } from "../router";

/** Import one file, then open the stored building in the workspace. */
export function ImportBuilding({ label = "Import building", inputLabel = "Building JSON file", onImported }: {
  label?: string; inputLabel?: string; onImported?: (id: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const busy = useRef(false);
  const upload = useImportBuilding();

  return (
    <section aria-label={label} className="grid min-w-0 gap-3 border-y border-line py-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={upload.isPending}
          onClick={() => input.current?.click()}
          className="flex items-center gap-2 rounded-[11px] bg-ink px-4 py-2.5 text-sm font-[650] text-white"
        >
          <Upload size={16} aria-hidden="true" />
          {upload.isPending ? "Importing…" : label}
        </button>
        <span className="text-sm text-muted">building.json, up to 20 MiB.</span>
        <input
          ref={input}
          type="file"
          aria-label={inputLabel}
          accept=".json,application/json"
          hidden
          disabled={upload.isPending}
          onChange={(event) => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (!file || busy.current) return;
            busy.current = true;
            upload.mutate(file, {
              onSuccess: ({ id }) => { onImported?.(id); navigate(`/admin/${encodeURIComponent(id)}`); },
              onSettled: () => { busy.current = false; },
            });
          }}
        />
      </div>
      {upload.isPending && <p role="status" className="text-sm text-muted">Checking and saving your building…</p>}
      {upload.isError && (
        <p role="alert" className="max-h-64 overflow-y-auto text-sm break-words whitespace-pre-wrap text-danger">
          {upload.error.message}
        </p>
      )}
    </section>
  );
}

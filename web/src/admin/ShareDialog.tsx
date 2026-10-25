import { Copy, ExternalLink } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";
import type { RouteRequest } from "../api/buildings";
import { guideLink } from "../route/link";
import { Sheet } from "../ui/Sheet";

/** A QR code with the phone link. The phone opens the guide and loads the same route itself. */
export function ShareDialog({
  open,
  onClose,
  buildingId,
  request,
  positionName,
  destinationName,
  onShared,
}: {
  open: boolean;
  onClose: () => void;
  buildingId: string;
  request: RouteRequest | undefined;
  positionName: string | undefined;
  destinationName: string | undefined;
  onShared: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const link = guideLink(location.origin, buildingId, request ?? {});
  const local = ["localhost", "127.0.0.1"].includes(location.hostname);
  const subtitle = request
    ? `${positionName ?? ""} to ${destinationName ?? ""}`
    : "No route yet. The phone opens the building and asks where to go.";
  return (
    <Sheet open={open} onClose={onClose} title="Send to phone" subtitle={subtitle}>
      <div className="grid justify-items-center gap-4 pb-1">
        <div className="rounded-[20px] border border-line p-4">
          <QRCodeSVG value={link} size={220} marginSize={0} fgColor="#191c16" title="QR code with the phone link" />
        </div>
        <p className="max-w-[340px] text-center text-[13px] text-muted">
          Scan with the phone camera. The route opens in the browser, no app needed.
        </p>
        {local && (
          <p className="max-w-[340px] rounded-[12px] bg-[#fff6dc] p-3 text-center text-xs">
            This page runs on localhost, which a phone cannot open. Open the workspace through its network address to scan.
          </p>
        )}
        <div className="flex w-full gap-2">
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard.writeText(link).then(() => setCopied(true));
              onShared();
            }}
            className="flex flex-1 items-center justify-center gap-2 rounded-[12px] bg-field px-3 py-3 text-[13px] font-[650]"
          >
            <Copy size={16} /> {copied ? "Copied" : "Copy link"}
          </button>
          <a
            href={link}
            target="_blank"
            rel="noreferrer"
            onClick={onShared}
            className="flex flex-1 items-center justify-center gap-2 rounded-[12px] bg-ink px-3 py-3 text-[13px] font-[650] text-white"
          >
            <ExternalLink size={16} /> Open guide
          </a>
        </div>
      </div>
    </Sheet>
  );
}

/** The small honesty badge: shown whenever anything on screen is mock or provisional data (CONTRACTS §15). */
export function DemoBadge({ reason, label = 'Demo data' }: { reason: string; label?: string }) {
  return <span className="demo-badge" title={reason}>{label}<span className="sr-only">: {reason}</span></span>;
}

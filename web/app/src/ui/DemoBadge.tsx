/** The small honesty badge: shown whenever anything on screen is mock or provisional data (CONTRACTS §15). */
export function DemoBadge({ reason }: { reason: string }) {
  return <span className="demo-badge" title={reason}>Demo data<span className="sr-only">: {reason}</span></span>;
}

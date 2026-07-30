import { formatDate, formatScore } from "../lib/format";

const SEVERITY = {
  high: { text: "text-heat-high", bar: "bg-heat-high" },
  medium: { text: "text-heat-med", bar: "bg-heat-med" },
  low: { text: "text-heat-low", bar: "bg-heat-low" },
};

/**
 * The risk-sorted queue. The API already sorts by score desc (INTERFACES
 * §6); filtering happens client-side against the single fetched page.
 */
export default function AlertQueue({ items, onOpen }) {
  if (items.length === 0) {
    return (
      <div className="border border-ink-700 bg-ink-900 px-6 py-16 text-center">
        <p className="text-paper-mut">No alerts match the current filters.</p>
        <p className="mt-1 text-sm text-paper-dim">
          Clear a status or typology filter to widen the queue.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-ink-700 bg-ink-900">
      {/* column header */}
      <div className="hidden grid-cols-[92px_1fr_120px_96px_104px] gap-4 border-b border-ink-700 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.16em] text-paper-dim md:grid">
        <span>Score</span>
        <span>Alert</span>
        <span>Status</span>
        <span className="text-right">Implicated</span>
        <span className="text-right">Created</span>
      </div>

      <ul className="divide-y divide-ink-700/60">
        {items.map((a) => (
          <QueueRow key={a.id} alert={a} onOpen={onOpen} />
        ))}
      </ul>
    </div>
  );
}

function QueueRow({ alert, onOpen }) {
  const sev = SEVERITY[alert.severity] ?? SEVERITY.low;
  const dismissed = alert.status === "dismissed";
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(alert.id)}
        className={`grid w-full grid-cols-[92px_1fr] items-center gap-x-4 gap-y-1 px-4 py-2.5 text-left transition-colors hover:bg-ink-800 md:grid-cols-[92px_1fr_120px_96px_104px] ${
          dismissed ? "opacity-50" : ""
        }`}
      >
        {/* score block: the heat ramp made visible */}
        <span className="flex items-center gap-2.5">
          <span className={`h-8 w-[3px] shrink-0 rounded-sm ${sev.bar}`} />
          <span>
            <span className={`block font-mono text-lg leading-none ${sev.text}`}>
              {formatScore(alert.score)}
            </span>
            <span className={`mt-0.5 block font-mono text-[9px] uppercase tracking-[0.14em] ${sev.text} opacity-70`}>
              {alert.severity}
            </span>
          </span>
        </span>

        <span className="min-w-0">
          <span className="block truncate text-[13px] font-medium text-paper">
            {alert.title}
          </span>
          <span className="mt-0.5 flex items-center gap-2 font-mono text-[10px] text-paper-dim">
            <span>{alert.id}</span>
            <span className="text-ink-700">·</span>
            <span>{alert.typology}</span>
            {alert.note && (
              <>
                <span className="text-ink-700">·</span>
                <span className="italic text-paper-mut">noted</span>
              </>
            )}
          </span>
        </span>

        <span className="hidden md:block">
          <StatusPill status={alert.status} />
        </span>
        <span className="hidden text-right font-mono text-xs text-paper-mut md:block">
          {alert.implicated_count}
        </span>
        <span className="hidden text-right font-mono text-xs text-paper-dim md:block">
          {formatDate(alert.created_at)}
        </span>
      </button>
    </li>
  );
}

export function StatusPill({ status }) {
  // "new" is the default state, so it stays quiet; the investigator-marked
  // states (reviewed/dismissed) are the visually distinct ones.
  const styles = {
    new: "border-ink-700 text-paper-dim",
    reviewed: "border-tracer/60 text-tracer",
    dismissed: "border-ink-700 text-paper-dim line-through",
  };
  return (
    <span
      className={`inline-block rounded-sm border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${styles[status] ?? styles.new}`}
    >
      {status}
    </span>
  );
}

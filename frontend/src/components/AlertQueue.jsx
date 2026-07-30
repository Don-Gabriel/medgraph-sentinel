import { formatDate, formatScore } from "../lib/format";

// Severity banding: every row carries a full-height left edge in its heat
// colour (ember/amber/ash), and high/medium rows get a whisper of the same
// hue as background tint — the hot top of the queue reads as a zone before
// any number is read. Heat ramp only; teal stays reserved for interaction.
const SEVERITY = {
  high: {
    text: "text-heat-high",
    edge: "border-l-heat-high",
    tint: "bg-heat-high/[0.05]",
  },
  medium: {
    text: "text-heat-med",
    edge: "border-l-heat-med",
    tint: "bg-heat-med/[0.04]",
  },
  low: { text: "text-heat-low", edge: "border-l-heat-low", tint: "" },
};

// Row grid: STATUS / IMPLICATED / CREATED are right-compressed to the
// minimum their content needs so the title column absorbs the dead space.
const ROW_GRID = "md:grid-cols-[92px_1fr_84px_80px_84px]";

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
      {/* column header — pl matches the rows' 3px severity edge + 13px pad */}
      <div className={`hidden ${ROW_GRID} gap-3 border-b border-ink-700 py-2 pl-4 pr-4 font-mono text-[10px] uppercase tracking-[0.16em] text-paper-dim md:grid`}>
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
        className={`grid w-full grid-cols-[92px_1fr] items-center gap-x-3 gap-y-1 border-l-[3px] py-2.5 pl-[13px] pr-4 text-left transition-colors hover:bg-ink-800 ${ROW_GRID} ${sev.edge} ${sev.tint} ${
          dismissed ? "opacity-50" : ""
        }`}
      >
        {/* score block: the heat ramp made visible */}
        <span>
          <span className={`block font-mono text-lg leading-none ${sev.text}`}>
            {formatScore(alert.score)}
          </span>
          <span className={`mt-0.5 block font-mono text-[9px] uppercase tracking-[0.14em] ${sev.text} opacity-70`}>
            {alert.severity}
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

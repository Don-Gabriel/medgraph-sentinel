import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import AlertQueue from "./components/AlertQueue";
import AlertView from "./components/AlertView";

/**
 * Investigator console (INTERFACES §7): alert queue -> alert drill-down.
 * Two screens, so plain state routing — no router dependency to explain.
 */
export default function App() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState(null); // {total, items}
  const [loadError, setLoadError] = useState(null);
  const [view, setView] = useState({ name: "queue" });
  const [statusFilter, setStatusFilter] = useState("all");
  const [typologyFilter, setTypologyFilter] = useState(null);

  const loadAll = useCallback(() => {
    setLoadError(null);
    Promise.all([api.health(), api.stats(), api.alerts()])
      .then(([h, s, a]) => {
        setHealth(h);
        setStats(s);
        setAlerts(a);
      })
      .catch((e) => setLoadError(String(e.message ?? e)));
  }, []);

  useEffect(loadAll, [loadAll]);

  // After a PATCH in the drill-down: update the queue row in place and
  // refresh the header counts, so the queue reflects changes immediately.
  const handleAlertPatched = useCallback((updated) => {
    setAlerts((prev) =>
      prev
        ? {
            ...prev,
            items: prev.items.map((it) =>
              it.id === updated.id
                ? { ...it, status: updated.status, note: updated.note }
                : it,
            ),
          }
        : prev,
    );
    api.stats().then(setStats).catch(() => {});
  }, []);

  const filtered = (alerts?.items ?? []).filter(
    (a) =>
      (statusFilter === "all" || a.status === statusFilter) &&
      (typologyFilter === null || a.typology === typologyFilter),
  );

  return (
    <div className="flex h-screen flex-col">
      <Header health={health} stats={stats} />

      {loadError && (
        <div className="mx-auto max-w-2xl px-6 py-16 text-center">
          <p className="text-paper-mut">
            API unreachable at <span className="font-mono">{api.base}</span>
          </p>
          <p className="mt-1 font-mono text-xs text-paper-dim">{loadError}</p>
          <button
            type="button"
            onClick={loadAll}
            className="mt-4 rounded-sm border border-tracer/60 px-3 py-1.5 font-mono text-xs text-tracer hover:bg-tracer/10"
          >
            Retry
          </button>
        </div>
      )}

      {!loadError && view.name === "queue" && (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="mx-auto w-full max-w-6xl px-4 pb-12 sm:px-6">
            {stats && (
              <FilterBar
                stats={stats}
                statusFilter={statusFilter}
                onStatus={setStatusFilter}
                typologyFilter={typologyFilter}
                onTypology={setTypologyFilter}
                shown={filtered.length}
              />
            )}
            {alerts ? (
              <AlertQueue
                items={filtered}
                onOpen={(id) => setView({ name: "alert", id })}
              />
            ) : (
              <p className="py-16 text-center font-mono text-xs text-paper-dim">
                loading alert queue…
              </p>
            )}
          </div>
        </div>
      )}

      {!loadError && view.name === "alert" && (
        <AlertView
          id={view.id}
          onBack={() => setView({ name: "queue" })}
          onPatched={handleAlertPatched}
        />
      )}
    </div>
  );
}

function Header({ health, stats }) {
  const degraded = health && health.status !== "ok";
  return (
    <header className="flex flex-wrap items-center gap-x-6 gap-y-1 border-b border-ink-700 bg-ink-900 px-4 py-2.5 sm:px-6">
      <div className="flex items-baseline gap-2.5">
        <span aria-hidden="true" className="text-heat-high">&#9670;</span>
        <h1 className="font-mono text-sm font-medium uppercase tracking-[0.24em] text-paper">
          MedGraph Sentinel
        </h1>
        <span className="hidden text-[11px] text-paper-dim md:inline">
          cross-border claims intelligence · synthetic data
        </span>
      </div>
      <div className="ml-auto flex items-center gap-4 font-mono text-[11px] text-paper-mut">
        {stats && (
          <>
            <span>
              <span className="text-paper">{stats.nodes.toLocaleString()}</span>{" "}
              <span className="text-paper-dim">nodes</span>
            </span>
            <span>
              <span className="text-paper">{stats.relationships.toLocaleString()}</span>{" "}
              <span className="text-paper-dim">relationships</span>
            </span>
          </>
        )}
        {health && (
          <span
            className={`flex items-center gap-1.5 ${degraded ? "text-heat-med" : "text-tracer"}`}
            title={degraded ? "API degraded — see /api/v1/health" : "API healthy"}
          >
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${degraded ? "bg-heat-med" : "bg-tracer"}`}
            />
            {health.status}
          </span>
        )}
      </div>
    </header>
  );
}

/** Counts at a glance; every count is also the filter that produces it. */
function FilterBar({ stats, statusFilter, onStatus, typologyFilter, onTypology, shown }) {
  const a = stats.alerts;
  const statusOptions = [
    ["all", "all", a.total],
    ["new", "new", a.new],
    ["reviewed", "reviewed", a.reviewed],
    ["dismissed", "dismissed", a.dismissed],
  ];
  const typologies = Object.entries(stats.by_typology ?? {}).sort(
    (x, y) => y[1] - x[1],
  );

  return (
    <div className="py-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div>
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-paper-dim">
            Alert queue
          </h2>
          <p className="mt-0.5 text-xs text-paper-mut">
            {shown} of {a.total} alerts · sorted by risk score
          </p>
        </div>

        {/* status segmented filter, counts inline */}
        <div className="flex overflow-hidden rounded-sm border border-ink-700">
          {statusOptions.map(([value, label, count]) => (
            <button
              key={value}
              type="button"
              onClick={() => onStatus(value)}
              className={`border-r border-ink-700 px-2.5 py-1 font-mono text-[11px] last:border-r-0 transition-colors ${
                statusFilter === value
                  ? "bg-ink-800 text-paper"
                  : "text-paper-mut hover:bg-ink-850 hover:text-paper"
              }`}
            >
              {label} <span className="text-paper-dim">{count}</span>
            </button>
          ))}
        </div>

        {/* the heat ramp, explained once */}
        <div className="ml-auto hidden items-center gap-3 font-mono text-[10px] text-paper-dim lg:flex">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm bg-heat-high" /> high
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm bg-heat-med" /> medium
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm bg-heat-low" /> low
          </span>
        </div>
      </div>

      {/* typology chips double as filters */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {typologies.map(([name, count]) => (
          <button
            key={name}
            type="button"
            onClick={() => onTypology(typologyFilter === name ? null : name)}
            className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors ${
              typologyFilter === name
                ? "border-tracer/70 bg-tracer/10 text-tracer"
                : "border-ink-700 text-paper-mut hover:border-paper-dim hover:text-paper"
            }`}
          >
            {name} <span className="opacity-60">{count}</span>
          </button>
        ))}
        {typologyFilter && (
          <button
            type="button"
            onClick={() => onTypology(null)}
            className="px-2 font-mono text-[11px] text-tracer hover:underline"
          >
            clear
          </button>
        )}
      </div>
    </div>
  );
}

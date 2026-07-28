import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * M1 slice: header stats wired to the real API (INTERFACES §6-7).
 * M2/M3 replace the placeholder body with the alert queue and drill-down.
 */
export default function App() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/health`).then((r) => r.json()),
      fetch(`${API}/api/v1/stats`).then((r) => r.json()),
    ])
      .then(([h, s]) => {
        setHealth(h);
        setStats(s);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <header className="flex items-baseline gap-4 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-semibold">MedGraph Sentinel</h1>
        <span className="text-sm text-slate-400">
          investigator console — synthetic data only
        </span>
        {health && (
          <span
            className={`ml-auto rounded px-2 py-1 text-xs font-mono ${
              health.status === "ok" ? "bg-emerald-900" : "bg-amber-900"
            }`}
          >
            {health.status}
          </span>
        )}
      </header>

      {error && (
        <p className="mt-6 text-amber-400">
          API unreachable at {API} — {error}
        </p>
      )}

      {stats && (
        <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4 max-w-3xl">
          <Stat label="nodes" value={stats.nodes} />
          <Stat label="relationships" value={stats.relationships} />
          <Stat label="alerts" value={stats.alerts.total} />
          <Stat label="new alerts" value={stats.alerts.new} />
        </dl>
      )}

      <p className="mt-10 text-slate-500">
        Alert queue arrives with M3 — see docs/MILESTONES.md.
      </p>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg bg-slate-900 p-4">
      <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-1 text-2xl font-mono">{value.toLocaleString()}</dd>
    </div>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";

/** Risk-forecast strip (ADR-037): per-typology flagged exposure with a
 *  next-30-day projection. The method line keeps the claim honest — this
 *  is a linear projection from the observed monthly trend, said so on
 *  screen, never dressed up as ML prophecy. Fails silent: if the
 *  endpoint is missing (older API image) the strip simply doesn't render. */
export default function Forecast() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;
    api
      .forecast()
      .then((d) => alive && setData(d))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, []);

  if (!data || !data.flagged?.length) return null;

  return (
    <section className="mb-6 rounded-sm border border-ink-700 bg-ink-900/60 px-4 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.25em] text-paper-dim">
          Risk forecast — flagged exposure
        </h2>
        <span className="hidden font-mono text-[9px] text-paper-dim/70 sm:block">
          {data.method}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        {data.flagged.map((f) => (
          <TypologyCard key={f.typology} f={f} />
        ))}
      </div>
    </section>
  );
}

const ARROWS = {
  rising: { glyph: "↗", cls: "text-heat-high" },
  falling: { glyph: "↘", cls: "text-tracer" },
  flat: { glyph: "→", cls: "text-paper-dim" },
};

function TypologyCard({ f }) {
  const arrow = ARROWS[f.next_month?.direction] ?? ARROWS.flat;
  return (
    <div className="rounded-sm border border-ink-700 bg-ink-950/60 px-3 py-2">
      <div className="truncate font-mono text-[10px] text-paper-dim">
        {f.typology}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-mono text-sm font-semibold text-paper">
          ${Math.round(f.amount_usd_total).toLocaleString()}
        </span>
        <span className={`font-mono text-xs ${arrow.cls}`}>{arrow.glyph}</span>
      </div>
      <Sparkline series={f.series} />
      <div className="mt-1 font-mono text-[9px] text-paper-dim/80">
        next 30d ~${Math.round(f.next_month?.amount_usd ?? 0).toLocaleString()}
      </div>
    </div>
  );
}

/** Inline SVG sparkline of monthly flagged amounts — no chart library. */
function Sparkline({ series }) {
  if (!series || series.length < 2) return null;
  const values = series.map((s) => s.amount_usd);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const width = 96;
  const height = 20;
  const step = width / (values.length - 1);
  const points = values
    .map(
      (v, i) =>
        `${(i * step).toFixed(1)},${(height - 2 - ((v - min) / span) * (height - 4)).toFixed(1)}`,
    )
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="mt-1 h-5 w-full text-tracer/80"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  );
}

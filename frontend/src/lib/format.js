// Evidence-value formatting. summary_params keys are self-describing per
// rule (see api/titles.py / detection rule YAMLs), so formatting is keyed
// off the key name and the value's shape. Dates stay ISO 8601 — the
// project-wide convention (CLAUDE.md).

const nf = new Intl.NumberFormat("en-US");

export function labelize(key) {
  return key.replace(/_/g, " ");
}

// impossible_travel packs claim pairs as {countries: [a,b], dates: [a,b]}.
function formatPair(p) {
  if (p && Array.isArray(p.countries) && Array.isArray(p.dates)) {
    return `${p.countries[0]} ${p.dates[0]} <> ${p.countries[1]} ${p.dates[1]}`;
  }
  return JSON.stringify(p);
}

export function formatValue(key, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) {
    return value
      .map((v) => (typeof v === "object" ? formatPair(v) : String(v)))
      .join(", ");
  }
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "number") {
    if (/_usd$/.test(key)) return `$${nf.format(Math.round(value))}`;
    if (/_pct$/.test(key)) return `${value}%`; // already on a 0–100 scale
    if (/(share|ratio|softening)/.test(key) && value >= 0 && value <= 1) {
      return `${(value * 100).toFixed(1)}%`; // fraction on a 0–1 scale
    }
    return nf.format(value);
  }
  return String(value);
}

// "2026-08-05T18:22:00Z" -> "2026-08-05" (ISO date, project convention).
export function formatDate(iso) {
  return typeof iso === "string" ? iso.slice(0, 10) : "—";
}

export function formatScore(score) {
  return Number(score).toFixed(1);
}

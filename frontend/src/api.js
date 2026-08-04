// Thin client for the REST contract (docs/INTERFACES.md §6). The console
// talks only to this API (§7). Every helper returns parsed JSON or throws
// an Error carrying the server's `detail` message so callers can show it.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${BASE}/api/v1${path}`, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      // non-JSON error body: keep the bare status
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  base: BASE,
  health: () => request("/health"),
  stats: () => request("/stats"),
  // 82 alerts in the committed dataset (81 + typology 4, ADR-037); one
  // page at the contract's max limit (200) keeps filtering client-side
  // and instant.
  alerts: () => request("/alerts?limit=200"),
  alert: (id) => request(`/alerts/${encodeURIComponent(id)}`),
  subgraph: (id, hops = 1) =>
    request(`/alerts/${encodeURIComponent(id)}/subgraph?hops=${hops}`),
  narration: (id) => request(`/alerts/${encodeURIComponent(id)}/narration`),
  forecast: () => request("/forecast"),
  report: (id) => request(`/alerts/${encodeURIComponent(id)}/report`),
  chat: (id, messages) =>
    request(`/alerts/${encodeURIComponent(id)}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    }),
  entity: (id) => request(`/entities/${encodeURIComponent(id)}`),
  patchAlert: (id, body) =>
    request(`/alerts/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};

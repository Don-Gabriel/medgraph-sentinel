# frontend/

React + Vite + Tailwind + Cytoscape.js investigator console. Contracts:
[docs/INTERFACES.md](../docs/INTERFACES.md) §6–7 — renders the API's
Cytoscape `elements` verbatim, never the full graph (ADR-009).

Current state (M1 slice): header stats wired to `/api/v1/health` and
`/api/v1/stats`. Alert queue + drill-down land M2/M3.

Dev: `npm install` then `npm run dev` (API base URL via
`VITE_API_BASE_URL`, default `http://localhost:8000`). Dependency versions
are best-known majors pinned by caret; the first `npm install` resolves and
locks them — commit the generated `package-lock.json` when it appears.

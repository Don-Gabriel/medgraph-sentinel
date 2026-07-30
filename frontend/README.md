# frontend/

React + Vite + Tailwind + Cytoscape.js investigator console (ADR-007).
Contracts: [docs/INTERFACES.md](../docs/INTERFACES.md) §6–7 — talks only to
the API, renders the subgraph endpoint's Cytoscape `elements` verbatim,
never the full graph (ADR-009).

## Current state (M3 console, 2026-07-30)

- **Alert queue** — risk-sorted (server order, score desc), severity as a
  three-step heat ramp (ember/amber/ash — one hue family, not a traffic
  light), status segments and typology chips that are both counts and
  filters, per-row title/typology/score/severity/status/implicated/created.
- **Alert view** — case file (left) + evidence subgraph hero (right):
  - Subgraph from `GET /alerts/{id}/subgraph` at `hops=1` by default;
    **"Expand to 2 hops" is an explicit async control** with a loading
    veil, because the server takes 3–5 s at 2 hops. This is our
    interpretation of "click to expand one hop" — the API has no per-node
    expansion endpoint, only the whole-subgraph `hops` parameter.
  - Node styling keyed off `data.type` / `data.implicated` / `data.role`
    only (§7): one colour+shape per label (legend rendered from the types
    present), implicated nodes get ~1.7× size + ember border + ember halo
    — never colour alone. Graphs over 150 nodes drop neighbour labels
    (implicated stay labelled). "Trimmed by server cap" badge when
    `truncated: true`.
  - Hover tooltip (label, type, role, up to 4 props); node click →
    `GET /entities/{id}` inspector panel; implicated-list click focuses
    the node in the graph.
  - Evidence panel: rule key + version, `summary_params` formatted by key
    shape (`*_usd` → $, `*_pct` → %, 0–1 shares/ratios → %, dates stay
    ISO), implicated entities grouped by role, narration with an honest
    source tag (cached/live AI vs deterministic fallback).
  - Status + note (≤2000 chars) wired to PATCH with optimistic update and
    rollback on failure; the queue row and header counts update in place.

## OPEN_QUESTIONS #6 — cose vs extension (finding)

Built-in `cose` is **readable for 100–300 node evidence subgraphs and no
layout extension is needed**, but only after tuning spacing (defaults
verified against the installed cytoscape source): `idealEdgeLength 48`
(default 32), `nodeRepulsion 6144` (default 2048), `nodeOverlap 24`
(default 4), `edgeElasticity 64` (default 32). Untuned defaults stacked
densely-connected hub pairs (broker + clinic) on top of each other. Values
live in `src/lib/graphStyle.js` (`COSE_LAYOUT`).

## Design tokens

`tailwind.config.js` is the single source of colour/type tokens (ink
chrome, paper text, heat ramp, teal tracer for interaction). IBM Plex
Sans/Mono/Serif are bundled locally via `@fontsource` packages so the
build needs no network at the venue (Sans = UI, Mono = data, Serif =
narration prose).

## Dev

`npm install` then `npm run dev` (default port 5173; use
`npm run dev -- --port 5174` when the compose frontend container occupies
5173). API base URL via `VITE_API_BASE_URL`, default
`http://localhost:8000`. `npm run build` produces `dist/` (gitignored).
Commit `package-lock.json` once generated so the Dockerfile can move to
`npm ci`.

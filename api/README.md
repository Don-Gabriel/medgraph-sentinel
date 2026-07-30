# api/

FastAPI backend for the investigator console. Contracts:
[docs/INTERFACES.md](../docs/INTERFACES.md) §6 (endpoints), §8 (narration).

Current state: the full §6 surface is implemented —
`/api/v1/health` (incl. the ADR-018 narration-cache validation), `/stats`,
`/alerts` (filters status/typology/min_severity, pagination, score-desc,
server-composed titles), `/alerts/{id}`, `/alerts/{id}/subgraph`
(hops 1–2, 300-node hard cap with relevance trimming, Cytoscape elements),
`/alerts/{id}/narration` (cache-first, deterministic fallback),
`PATCH /alerts/{id}` (status/note) and `/entities/{id}`.

Layout:

- `main.py` — app wiring, CORS, `/health` + `/stats`, and the 422 handler
  that flattens validation errors into the contract's `{"detail": "<msg>"}`
  shape.
- `graph.py` — driver + the `get_session` dependency (the test seam: the
  suite overrides it with an in-memory fake, `tests/conftest.py`), the
  id-prefix→label routing, label/temporal shaping helpers.
- `alerts.py` / `entities.py` — the endpoints and their Cypher (module
  constants, so tests dispatch fakes on the exact query text).
- `subgraph.py` — pure cap/trim logic (relevance rule documented inline:
  implicated always kept, then bridge nodes, then by degree; deterministic).
- `titles.py` — one title template per typology from `summary_params`;
  unknown typologies degrade to a generic title (ADR-008: a Day-2 rule
  surfaces with zero API changes).
- `narration/` — `fallback.py` holds the deterministic per-typology
  fallback templates (pure functions of `summary_params`); the cache
  builder lands Aug 7 with the ADR-018 build chain. `narration_cache/` is
  the **committed** cache the offline demo serves from (ADR-010/018 — do
  not gitignore, do not rebuild partially).

Deliberate behaviour notes:

- **No live Claude call path exists.** ADR-010 makes the live call optional
  and it is off: narration is cache → template, nothing ever waits on the
  network. `source` is therefore only ever `claude-cached` or `fallback`
  (`claude-live` returns if someone ever implements the optional path).
- Per-entry `prompt_sha256` validation activates with the narration
  builder (it defines the prompt to hash against); until then a cache hit
  requires a well-formed entry whose `alert_id` matches the file.
- The evidence subgraph excludes Alert nodes and IMPLICATES edges —
  it shows the economy, not other alerts — and collapses parallel
  same-type edges (the elements shape carries no edge properties).
- `/entities/{id}` degree counts all relationships, IMPLICATES included
  (raw inspector, no filtering).

Run locally: `uvicorn api.main:app --reload` (needs `.env` values exported
or a running compose Neo4j). Tests: `python -m pytest tests/ -q` — the API
tests need no database.

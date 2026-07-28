# api/

FastAPI backend for the investigator console. Contracts:
[docs/INTERFACES.md](../docs/INTERFACES.md) §6 (endpoints), §8 (narration).

Current state (M1 slice): `/api/v1/health` (incl. the ADR-018
narration-cache validation) and `/api/v1/stats`, both degrade-never-500.
M3 adds the alert endpoints. `narration/` holds the cache builder + fallback
templates (stub); `narration_cache/` is the **committed** cache the offline
demo serves from (ADR-010/018 — do not gitignore, do not rebuild partially).

Run locally: `uvicorn api.main:app --reload` (needs `.env` values exported
or a running compose Neo4j).

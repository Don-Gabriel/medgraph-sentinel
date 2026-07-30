"""MedGraph Sentinel API — health, stats, alerts, entities.

Contracts: docs/INTERFACES.md section 6. Everything here must degrade,
never 500 — the demo depends on it (ADR-010, DEMO_RUNBOOK). Narration-cache
validation per ADR-018: loud at startup, surfaced at /health, never silent
at request time. Alert/entity endpoints live in api/alerts.py and
api/entities.py behind the get_session dependency (api/graph.py) so tests
can fake the database in-process.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import alerts, entities, narration
from api.graph import close_driver, get_driver

log = logging.getLogger("medgraph.api")


def _query_one(cypher: str) -> dict | None:
    """Run a single-row read query; None on any failure (degrade, don't raise)."""
    try:
        with get_driver().session() as session:
            record = session.run(cypher).single()
            return dict(record) if record else None
    except Exception as exc:  # any driver/connectivity error means "degraded"
        log.warning("neo4j query failed: %s", exc)
        return None


def _query_all(cypher: str) -> list[dict] | None:
    """Run a multi-row read query; None on any failure (degrade, don't raise)."""
    try:
        with get_driver().session() as session:
            return [dict(r) for r in session.run(cypher)]
    except Exception as exc:
        log.warning("neo4j query failed: %s", exc)
        return None


def _alert_ids() -> set[str] | None:
    rows = _query_all("MATCH (a:Alert) RETURN a.id AS id")
    return {r["id"] for r in rows} if rows is not None else None


def _cached_narration_ids() -> set[str]:
    if not narration.CACHE_DIR.is_dir():
        return set()
    return {p.stem for p in narration.CACHE_DIR.glob("ALT_*.json")}


def narration_cache_status() -> dict:
    """ADR-018 guard, tightened per ADR-032: COMPLETENESS, not just counts.
    Every alert id in the graph must have its own cache file — equal counts
    with mismatched ids (e.g. cache from a different detection run) must
    still fail loudly, because per-entry fallback would mask it mid-demo."""
    alert_ids = _alert_ids()
    cached_ids = _cached_narration_ids()
    missing = sorted(alert_ids - cached_ids) if alert_ids is not None else []
    match = alert_ids is not None and not missing
    return {
        "alerts": len(alert_ids) if alert_ids is not None else 0,
        "cached": len(cached_ids),
        "match": match,
        "missing": len(missing),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    status = narration_cache_status()
    if not status["match"]:
        log.critical(
            "CRITICAL NARRATION CACHE MISMATCH: %s cached / %s alerts "
            "- re-run the ADR-018 build chain from the top",
            status["cached"],
            status["alerts"],
        )
    yield
    close_driver()


app = FastAPI(title="MedGraph Sentinel API", lifespan=lifespan)

# The console (:5173) is a different origin than the API (:8000); without
# CORS the browser blocks every fetch (found at the M1 browser check).
# Wide-open is deliberate: localhost demo tool, no auth by design (ADR-011).
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(alerts.router)
app.include_router(entities.router)


@app.exception_handler(RequestValidationError)
async def validation_error_as_detail_string(request, exc) -> JSONResponse:
    """Contract (INTERFACES §6): every error is {"detail": "<message>"}.
    FastAPI's default 422 carries a structured list instead — flatten it to
    one readable string so the frontend has a single error shape."""
    messages = "; ".join(
        "{}: {}".format(
            ".".join(str(part) for part in err["loc"] if part != "body"),
            err["msg"],
        )
        for err in exc.errors()
    )
    return JSONResponse(status_code=422, content={"detail": messages})


@app.get("/api/v1/health")
def health() -> dict:
    neo4j_up = _query_one("RETURN 1 AS ok") is not None
    cache = narration_cache_status()
    alerts = cache["alerts"]  # same id-set query — one source of truth
    degraded = not neo4j_up or not cache["match"]
    return {
        "status": "degraded" if degraded else "ok",
        "neo4j": neo4j_up,
        "alert_count": alerts if alerts is not None else 0,
        "narration_cache": cache,
    }


@app.get("/api/v1/stats")
def stats() -> dict:
    nodes = _query_one("MATCH (n) RETURN count(n) AS n")
    rels = _query_one("MATCH ()-[r]->() RETURN count(r) AS n")
    by_status_rows = None
    try:
        with get_driver().session() as session:
            by_status_rows = [
                (r["status"], r["n"])
                for r in session.run(
                    "MATCH (a:Alert) RETURN a.status AS status, count(a) AS n"
                )
            ]
    except Exception as exc:
        log.warning("stats alert query failed: %s", exc)
    by_status = dict(by_status_rows) if by_status_rows else {}
    by_typology_rows = None
    try:
        with get_driver().session() as session:
            by_typology_rows = [
                (r["typology"], r["n"])
                for r in session.run(
                    "MATCH (a:Alert) RETURN a.typology AS typology, count(a) AS n"
                )
            ]
    except Exception as exc:
        log.warning("stats typology query failed: %s", exc)
    total_alerts = sum(by_status.values())
    return {
        "nodes": nodes["n"] if nodes else 0,
        "relationships": rels["n"] if rels else 0,
        "alerts": {
            "total": total_alerts,
            "new": by_status.get("new", 0),
            "reviewed": by_status.get("reviewed", 0),
            "dismissed": by_status.get("dismissed", 0),
        },
        "by_typology": dict(by_typology_rows) if by_typology_rows else {},
    }

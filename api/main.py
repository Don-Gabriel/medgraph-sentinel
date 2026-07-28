"""MedGraph Sentinel API — M1 slice: /health and /stats only.

Contracts: docs/INTERFACES.md section 6. Alert endpoints land with M3.
Everything here must degrade, never 500 — the demo depends on it (ADR-010,
DEMO_RUNBOOK). Narration-cache validation per ADR-018: loud at startup,
surfaced at /health, never silent at request time.
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from neo4j import GraphDatabase

log = logging.getLogger("medgraph.api")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
NARRATION_CACHE_DIR = Path(__file__).parent / "narration_cache"

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), connection_timeout=3
        )
    return _driver


def _query_one(cypher: str) -> dict | None:
    """Run a single-row read query; None on any failure (degrade, don't raise)."""
    try:
        with _get_driver().session() as session:
            record = session.run(cypher).single()
            return dict(record) if record else None
    except Exception as exc:  # any driver/connectivity error means "degraded"
        log.warning("neo4j query failed: %s", exc)
        return None


def _alert_count() -> int | None:
    row = _query_one("MATCH (a:Alert) RETURN count(a) AS n")
    return row["n"] if row else None


def _cached_narration_count() -> int:
    if not NARRATION_CACHE_DIR.is_dir():
        return 0
    return sum(1 for p in NARRATION_CACHE_DIR.glob("*.json"))


def narration_cache_status() -> dict:
    """ADR-018 guard: cached narration count must match alert count."""
    alerts = _alert_count()
    cached = _cached_narration_count()
    match = alerts is not None and alerts == cached
    return {"alerts": alerts if alerts is not None else 0, "cached": cached, "match": match}


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
    if _driver is not None:
        _driver.close()


app = FastAPI(title="MedGraph Sentinel API", lifespan=lifespan)


@app.get("/api/v1/health")
def health() -> dict:
    neo4j_up = _query_one("RETURN 1 AS ok") is not None
    alerts = _alert_count()
    cache = narration_cache_status()
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
        with _get_driver().session() as session:
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
        with _get_driver().session() as session:
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

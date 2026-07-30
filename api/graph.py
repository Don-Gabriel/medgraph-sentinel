"""Shared Neo4j access + shaping helpers for the v1 endpoints.

Why this file exists: the endpoints in api/alerts.py and api/entities.py
never construct a driver themselves — they take a session from the
`get_session` dependency. That single seam is what lets the test suite
swap in an in-memory fake (tests/conftest.py) and what keeps connection
handling in one explainable place.
"""
import logging
import os

from fastapi import HTTPException
from neo4j import GraphDatabase
from neo4j.time import Date, DateTime, Duration, Time

log = logging.getLogger("medgraph.api")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), connection_timeout=3
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def get_session():
    """FastAPI dependency: one session per request, closed afterwards."""
    with get_driver().session() as session:
        yield session


def run_query(session, query: str, **params) -> list:
    """All endpoint data access goes through here so a dead database becomes
    a clean 503 {"detail": ...} (INTERFACES §6 error shape), never a raw 500
    mid-demo."""
    try:
        return list(session.run(query, **params))
    except HTTPException:
        raise
    except Exception as exc:  # driver/connectivity errors of any flavour
        log.warning("neo4j query failed: %s", exc)
        raise HTTPException(
            status_code=503, detail="graph database unavailable"
        ) from exc


# ID prefix -> node label (DATA_MODEL.md conventions). Same routing trick the
# loader uses for IMPLICATES targets (ADR-029): a labelled MATCH hits the
# per-label unique-id index, an unlabelled one is a full store scan.
LABEL_BY_PREFIX = {
    "PAT": "Patient", "DOC": "Doctor", "CLI": "Clinic", "BRK": "Broker",
    "CLM": "Claim", "CRD": "Credential", "ACC": "PaymentAccount",
    "DEV": "Device", "ADR": "Address", "PRC": "Procedure", "INS": "Insurer",
    "ALT": "Alert",
}


def label_and_key_for(entity_id: str) -> tuple[str, str] | None:
    """Map an entity id to its (label, id property). Country nodes are keyed
    on `code` (2-letter ISO), everything else on prefixed `id`. None ⇒ the id
    can't belong to any label — caller 404s without touching the database."""
    if len(entity_id) == 2 and entity_id.isalpha() and entity_id.isupper():
        return ("Country", "code")
    prefix = entity_id.split("_", 1)[0]
    label = LABEL_BY_PREFIX.get(prefix)
    return (label, "id") if label else None


def display_label(props: dict, node_id: str) -> str:
    """Human-readable node label: name/full_name/code/id fallback
    (INTERFACES §6, alert detail)."""
    return (props.get("name") or props.get("full_name")
            or props.get("code") or node_id)


def to_jsonable(value):
    """Neo4j temporal values are not JSON-serializable; convert to ISO
    strings, recursing into containers. to_native() drops the driver's
    nanosecond padding (created_at renders 2026-07-30T12:47:37Z, not
    ...37.000000000+00:00 — verified against the live store)."""
    if isinstance(value, (Date, DateTime, Time)):
        return value.to_native().isoformat()
    if isinstance(value, Duration):
        return str(value)
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    return value


def iso_datetime(value) -> str:
    """Alert.created_at as the contract shows it: UTC with a trailing Z."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else to_jsonable(value)
    return text.replace("+00:00", "Z")

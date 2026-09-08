"""Alert endpoints — the investigator console's data source.

Contract: docs/INTERFACES.md §6 (list/detail/subgraph/narration/PATCH).
Alerts were written by the detection run and shipped as committed data
(ADR-008/029); this module only reads them and updates status/note.
Narration is cache-first, then an optional Gemini live call that is OFF
unless BOTH NARRATION_LIVE and GEMINI_API_KEY are set (api/narration/live.py),
then a deterministic template. The venue is assumed offline, so the demo
path is cache-only: with the committed cache complete the live branch is
unreachable, and it degrades to the template on any failure.
"""
import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api import narration
from api.graph import display_label, get_session, run_query, to_jsonable, iso_datetime
from api.narration import live
from api.narration.fallback import fallback_text
from api.subgraph import NODE_CAP, to_elements, trim_to_cap
from api.titles import compose_title, parse_summary_params

log = logging.getLogger("medgraph.api")

router = APIRouter(prefix="/api/v1")

STATUSES = ("new", "reviewed", "dismissed")
SEVERITY_ORDER = ("low", "medium", "high")

# ---- Cypher (module constants so tests can dispatch fakes on them) ----

# List filters: NULL parameter = filter not applied. min_severity arrives as
# the expanded list of acceptable bands (computed in Python — keeps the
# ordering low<medium<high in one visible place instead of in Cypher).
ALERT_FILTER = """\
MATCH (a:Alert)
WHERE ($status IS NULL OR a.status = $status)
  AND ($typology IS NULL OR a.typology = $typology)
  AND ($severities IS NULL OR a.severity IN $severities)
"""

Q_ALERT_COUNT = ALERT_FILTER + "RETURN count(a) AS total"

# Page first, then count IMPLICATES only for the page (cheap), then re-sort:
# the aggregation after SKIP/LIMIT does not guarantee row order survives.
Q_ALERT_LIST = ALERT_FILTER + """\
WITH a ORDER BY a.score DESC, a.id ASC
SKIP $offset LIMIT $limit
OPTIONAL MATCH (a)-[i:IMPLICATES]->()
WITH a, count(i) AS implicated_count
RETURN a.id AS id, a.typology AS typology, a.rule_version AS rule_version,
       a.score AS score, a.severity AS severity, a.status AS status,
       a.note AS note, a.created_at AS created_at,
       a.summary_params AS summary_params, implicated_count
ORDER BY score DESC, id ASC
"""

Q_ALERT_ONE = """\
MATCH (a:Alert {id: $id})
RETURN a.id AS id, a.typology AS typology, a.rule_version AS rule_version,
       a.score AS score, a.severity AS severity, a.status AS status,
       a.note AS note, a.created_at AS created_at,
       a.summary_params AS summary_params
"""

# coalesce(n.id, n.code): Country nodes are keyed on `code` (DATA_MODEL).
Q_ALERT_IMPLICATED = """\
MATCH (a:Alert {id: $id})-[i:IMPLICATES]->(n)
RETURN coalesce(n.id, n.code) AS id, labels(n)[0] AS type,
       properties(n) AS props, i.role AS role
ORDER BY id
"""

# Subgraph expansion works on elementId frontiers: entity ids are only
# unique per label, so id-based lookups without a label would be full store
# scans; elementId equality is a direct fetch.
Q_SUBGRAPH_SEEDS = """\
MATCH (a:Alert {id: $id})-[i:IMPLICATES]->(n)
RETURN elementId(n) AS eid, coalesce(n.id, n.code) AS id,
       labels(n)[0] AS type, properties(n) AS props, i.role AS role
ORDER BY id
"""

# One hop outward from the current frontier. Alert nodes are excluded: the
# evidence subgraph shows the economy, not other alerts — otherwise every
# shared entity would drag in its whole alert neighbourhood via IMPLICATES.
Q_SUBGRAPH_EXPAND = """\
UNWIND $eids AS eid
MATCH (n)-[r]-(m)
WHERE elementId(n) = eid AND NOT m:Alert
RETURN DISTINCT elementId(m) AS eid, coalesce(m.id, m.code) AS id,
       labels(m)[0] AS type, properties(m) AS props
"""

# Induced edges among the kept nodes, direction preserved. DISTINCT collapses
# parallel same-type edges (e.g. repeated TRANSFERRED between two accounts):
# the elements shape carries no edge properties, so duplicates render as
# identical lines. IMPLICATES never appears — Alert nodes are not in $eids.
Q_SUBGRAPH_EDGES = """\
UNWIND $eids AS eid
MATCH (n)-[r]->(m)
WHERE elementId(n) = eid AND elementId(m) IN $all_eids
RETURN DISTINCT coalesce(n.id, n.code) AS source,
       coalesce(m.id, m.code) AS target, type(r) AS type
"""

# coalesce keeps the old value when a field is not being patched (note: ""
# is a real value — clearing a note — and coalesce passes it through).
Q_ALERT_PATCH = """\
MATCH (a:Alert {id: $id})
SET a.status = coalesce($status, a.status),
    a.note = coalesce($note, a.note)
RETURN a.id AS id
"""


# ---- shared shaping ----

def _list_item(row) -> dict:
    """One alert queue row: list fields + server-composed title."""
    params = parse_summary_params(row["summary_params"])
    return {
        "id": row["id"], "typology": row["typology"],
        "rule_version": row["rule_version"], "score": row["score"],
        "severity": row["severity"], "status": row["status"],
        "note": row["note"], "created_at": iso_datetime(row["created_at"]),
        "title": compose_title(row["typology"], params),
        "implicated_count": row["implicated_count"],
    }


def _alert_detail(session, alert_id: str) -> dict:
    rows = run_query(session, Q_ALERT_ONE, id=alert_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown alert {alert_id}")
    row = rows[0]
    params = parse_summary_params(row["summary_params"])
    implicated = [
        {"id": r["id"], "type": r["type"],
         "label": display_label(r["props"], r["id"]), "role": r["role"]}
        for r in run_query(session, Q_ALERT_IMPLICATED, id=alert_id)
    ]
    return {
        "id": row["id"], "typology": row["typology"],
        "rule_version": row["rule_version"], "score": row["score"],
        "severity": row["severity"], "status": row["status"],
        "note": row["note"], "created_at": iso_datetime(row["created_at"]),
        "title": compose_title(row["typology"], params),
        "implicated_count": len(implicated),
        "summary_params": params,
        "implicated": implicated,
    }


# ---- endpoints ----

@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    typology: str | None = None,
    min_severity: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session=Depends(get_session),
) -> dict:
    if status is not None and status not in STATUSES:
        raise HTTPException(422, detail=f"status must be one of {'|'.join(STATUSES)}")
    if min_severity is not None and min_severity not in SEVERITY_ORDER:
        raise HTTPException(
            422, detail=f"min_severity must be one of {'|'.join(SEVERITY_ORDER)}")
    # min_severity=medium means medium AND high — expand to the accepted list
    severities = (list(SEVERITY_ORDER[SEVERITY_ORDER.index(min_severity):])
                  if min_severity else None)
    # typology is NOT validated against a fixed list: a Day-2 rule's alerts
    # must be filterable without an API change (ADR-008); unknown = empty.
    filters = {"status": status, "typology": typology, "severities": severities}
    total_row = run_query(session, Q_ALERT_COUNT, **filters)
    items = [_list_item(r) for r in run_query(
        session, Q_ALERT_LIST, **filters, offset=offset, limit=limit)]
    return {"total": total_row[0]["total"] if total_row else 0, "items": items}


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: str, session=Depends(get_session)) -> dict:
    return _alert_detail(session, alert_id)


@router.get("/alerts/{alert_id}/subgraph")
def alert_subgraph(
    alert_id: str,
    hops: int = Query(1, ge=1, le=2),  # 1 default, 2 max; else 422 (contract)
    session=Depends(get_session),
) -> dict:
    seed_rows = run_query(session, Q_SUBGRAPH_SEEDS, id=alert_id)
    if not seed_rows:
        # No IMPLICATES ⇒ either the alert doesn't exist (404) or it exists
        # with zero edges (legal per schema, empty subgraph).
        if not run_query(session, Q_ALERT_ONE, id=alert_id):
            raise HTTPException(status_code=404, detail=f"unknown alert {alert_id}")
        return {"truncated": False, "elements": {"nodes": [], "edges": []}}

    # nodes: id -> {type, label, implicated, role, props}; eids drive Cypher.
    nodes, eid_of = {}, {}
    for r in seed_rows:
        nodes[r["id"]] = {"type": r["type"],
                          "label": display_label(r["props"], r["id"]),
                          "implicated": True, "role": r["role"],
                          "props": to_jsonable(r["props"])}
        eid_of[r["id"]] = r["eid"]

    frontier = sorted(eid_of.values())
    for _hop in range(hops):
        if not frontier:
            break
        new_eids = []
        for r in run_query(session, Q_SUBGRAPH_EXPAND, eids=frontier):
            if r["id"] in nodes:
                continue
            nodes[r["id"]] = {"type": r["type"],
                              "label": display_label(r["props"], r["id"]),
                              "implicated": False, "role": None,
                              "props": to_jsonable(r["props"])}
            eid_of[r["id"]] = r["eid"]
            new_eids.append(r["eid"])
        frontier = sorted(new_eids)

    all_eids = sorted(eid_of.values())
    edges = [(r["source"], r["target"], r["type"])
             for r in run_query(session, Q_SUBGRAPH_EDGES,
                                eids=all_eids, all_eids=all_eids)]

    implicated_ids = {nid for nid, n in nodes.items() if n["implicated"]}
    kept, truncated = trim_to_cap(set(nodes), edges, implicated_ids, NODE_CAP)
    kept_nodes = {nid: n for nid, n in nodes.items() if nid in kept}
    kept_edges = [e for e in edges if e[0] in kept and e[1] in kept]
    return {"truncated": truncated,
            "elements": to_elements(kept_nodes, kept_edges)}


@router.get("/alerts/{alert_id}/narration")
def alert_narration(alert_id: str, session=Depends(get_session)) -> dict:
    rows = run_query(session, Q_ALERT_ONE, id=alert_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown alert {alert_id}")
    # Cache-first (ADR-010/018): a committed JSON per alert. Any read/parse
    # problem falls through to the deterministic template — an existing
    # alert never 404s here and nothing ever waits on a network call
    # (the optional live path is deliberately not implemented).
    cache_file = narration.CACHE_DIR / f"{alert_id}.json"
    try:
        entry = json.loads(cache_file.read_text(encoding="utf-8"))
        if entry.get("alert_id") == alert_id and entry.get("text"):
            return {"alert_id": alert_id, "text": entry["text"],
                    "source": "claude-cached"}
        log.warning("narration cache entry for %s is malformed; falling back",
                    alert_id)
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        log.warning("narration cache read failed for %s: %s", alert_id, exc)
    params = parse_summary_params(rows[0]["summary_params"])
    # Cache missed. Only now — and only if BOTH live switches are set — try
    # Gemini. With the committed cache complete this is unreachable, so the
    # offline demo never depends on it; live.generate() returns None on any
    # failure and we drop to the template below.
    if live.is_enabled():
        implicated = [
            {"role": r["role"], "type": r["type"], "id": r["id"],
             "label": display_label(r["props"], r["id"])}
            for r in run_query(session, Q_ALERT_IMPLICATED, id=alert_id)
        ]
        text = live.narrate_alert(alert_id, rows[0]["typology"],
                                  rows[0]["score"], rows[0]["severity"],
                                  params, implicated)
        if text:
            return {"alert_id": alert_id, "text": text,
                    "source": "gemini-live"}
    return {"alert_id": alert_id,
            "text": fallback_text(rows[0]["typology"], params),
            "source": "fallback"}


class AlertPatch(BaseModel):
    """PATCH body: status and/or note (INTERFACES §6). Literal + max_length
    make Pydantic produce the 422s the contract requires."""
    status: Literal["new", "reviewed", "dismissed"] | None = None
    note: str | None = Field(default=None, max_length=2000)


@router.patch("/alerts/{alert_id}")
def patch_alert(alert_id: str, patch: AlertPatch,
                session=Depends(get_session)) -> dict:
    if patch.status is None and patch.note is None:
        # "status and/or note" — an empty patch is a caller bug, say so.
        raise HTTPException(422, detail="provide status and/or note")
    rows = run_query(session, Q_ALERT_PATCH, id=alert_id,
                     status=patch.status, note=patch.note)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown alert {alert_id}")
    return _alert_detail(session, alert_id)

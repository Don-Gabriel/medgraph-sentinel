"""Helpers shared by rule implementations.

The scale() ramp is the whole scoring vocabulary: every feature becomes a
0..1 value via an explicit lower/upper reference, weights turn features
into points, and the YAML carries the references — so "why did this score
73?" is always answerable from the rule file alone.
"""
from collections import Counter

# GDS calls verified live against 2.13.11 via CALL gds.list(...) on
# 2026-07-30 (gds.graph.project, gds.louvain.stream, gds.util.asNode,
# gds.graph.drop) — hard rule 2: signatures come from the install, not memory.
_LOUVAIN_GRAPH = "mg_detect_louvain"
# readConcurrency: 1 — parallel projection loads adjacency lists in a
# nondeterministic order, which moves Louvain's tie-breaks between runs
# (observed live: community sizes drifted a few % between two identical
# fresh loads). Single-threaded projection + single-threaded Louvain was
# measured byte-stable across independent load->detect->export cycles.
_PROJECT = (
    f"CALL gds.graph.project('{_LOUVAIN_GRAPH}', "
    "['Claim','Patient','Clinic','Broker','PaymentAccount'], "
    "{FOR_PATIENT: {orientation: 'UNDIRECTED'}, "
    " AT_CLINIC: {orientation: 'UNDIRECTED'}, "
    " ARRANGED_BY: {orientation: 'UNDIRECTED'}, "
    " PAID_TO: {orientation: 'UNDIRECTED'}, "
    " TRANSFERRED: {orientation: 'UNDIRECTED'}}, "
    "{readConcurrency: 1})"
)
# concurrency: 1 — measured on this graph (34,078 nodes, twice, 0 diffs):
# single-threaded Louvain gives identical partitions run-to-run, parallel
# Louvain does NOT. Determinism outranks the ~2 s saved (ADR-006 spirit:
# identical graph => identical alerts, byte-identical re-export, ADR-029).
_STREAM = (
    f"CALL gds.louvain.stream('{_LOUVAIN_GRAPH}', {{concurrency: 1}}) "
    "YIELD nodeId, communityId "
    "RETURN gds.util.asNode(nodeId).id AS id, communityId"
)
# Explicit YIELD: without it the procedure returns its full row including
# the deprecated `schema` field, and the server sends a DEPRECATION
# notification the driver prints on every run (verified live on GDS
# 2.13.11 / driver 6.2.0: bare call warns, YIELD graphName is silent).
_DROP = f"CALL gds.graph.drop('{_LOUVAIN_GRAPH}', false) YIELD graphName"

_louvain_cache: dict[str, str] | None = None


def louvain_communities(session) -> dict[str, str]:
    """entity id -> Louvain community on the claim-participation projection
    (ADR-026 baseline: 2.4 s at 51k nodes). Computed once per process — both
    typology 1 and 3 attach it as ring *context*, never as a gate (ADR-028).
    The in-memory graph is dropped immediately; nothing lingers in GDS.

    Community labels are canonicalized to the smallest member entity id
    (GDS's raw communityId is an internal node id — a different number for
    the same partition on every run, useless in committed evidence)."""
    global _louvain_cache
    if _louvain_cache is None:
        session.run(_DROP).consume()  # stale projection from a crashed run
        session.run(_PROJECT).consume()
        try:
            raw = {r["id"]: r["communityId"] for r in session.run(_STREAM)}
        finally:
            session.run(_DROP).consume()
        members: dict[int, list[str]] = {}
        for entity_id, community in raw.items():
            members.setdefault(community, []).append(entity_id)
        canonical = {c: min(ids) for c, ids in members.items()}
        _louvain_cache = {eid: canonical[c] for eid, c in raw.items()}
    return _louvain_cache


def community_sizes(communities: dict[str, int]) -> Counter:
    return Counter(communities.values())


def reset_cache() -> None:
    """Test hook."""
    global _louvain_cache
    _louvain_cache = None


def scale(value: float, lo: float, hi: float) -> float:
    """Linear ramp: 0.0 at/below lo, 1.0 at/above hi."""
    if hi <= lo:
        raise ValueError(f"scale needs hi > lo (got {lo}, {hi})")
    return min(1.0, max(0.0, (value - lo) / (hi - lo)))

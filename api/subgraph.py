"""Evidence-subgraph shaping: the 300-node hard cap and the Cytoscape.js
elements format (INTERFACES §6; cap raised 200→300 by owner decision
2026-07-30).

Pure functions over plain node/edge collections — no Neo4j here, so the
cap, trim order and determinism are unit-testable without a database.
"""
NODE_CAP = 300


def _adjacency(node_ids: set, edges: list[tuple[str, str, str]]) -> dict:
    adj = {nid: set() for nid in node_ids}
    for source, target, _type in edges:
        if source in adj and target in adj and source != target:
            adj[source].add(target)
            adj[target].add(source)
    return adj


def _bridge_nodes(node_ids: set, edges: list, implicated: set) -> set:
    """Non-implicated nodes that survive repeatedly deleting non-implicated
    nodes of degree <= 1. Survivors are the connective tissue *between*
    implicated nodes (exact on trees; a pendant cycle can also survive,
    which errs on the side of keeping structure — acceptable and cheap)."""
    adj = _adjacency(node_ids, edges)
    alive = set(node_ids)
    while True:
        leaves = [n for n in alive
                  if n not in implicated and len(adj[n] & alive) <= 1]
        if not leaves:
            return {n for n in alive if n not in implicated}
        alive -= set(leaves)


def trim_to_cap(node_ids: set, edges: list[tuple[str, str, str]],
                implicated: set, cap: int = NODE_CAP) -> tuple[set, bool]:
    """Relevance rule (documented per the §6 cap decision):
      1. implicated nodes are never trimmed — they ARE the alert's evidence
         (and the detection runner caps them at 200, safely under 300);
      2. bridge nodes — on the connective paths between implicated nodes —
         are kept next;
      3. remaining slots fill by subgraph degree, descending.
    Dropping the lowest-relevance nodes first means the periphery leaves
    (degree-1 patients, procedures, devices two hops out) go before anything
    structural. Ties break on node id ascending, so the same graph always
    yields the same subgraph. Returns (kept_ids, truncated)."""
    if len(node_ids) <= cap:
        return set(node_ids), False
    bridges = _bridge_nodes(node_ids, edges, implicated)
    degree = {nid: 0 for nid in node_ids}
    for source, target, _type in edges:
        if source in degree and target in degree:
            degree[source] += 1
            degree[target] += 1
    candidates = sorted(
        (nid for nid in node_ids if nid not in implicated),
        key=lambda nid: (0 if nid in bridges else 1, -degree[nid], nid),
    )
    slots = max(0, cap - len(implicated))
    kept = set(implicated) | set(candidates[:slots])
    return kept, True


def to_elements(nodes: dict, edges: list[tuple[str, str, str]]) -> dict:
    """Exact Cytoscape.js elements shape from INTERFACES §6, rendered
    verbatim by the frontend. Nodes sorted by id, edges by (source, target,
    type) with ids e0..eN assigned in that order — deterministic output for
    the same graph. `nodes` maps id -> {type, label, implicated, role, props}."""
    node_elements = [
        {"data": {"id": nid, "type": n["type"], "label": n["label"],
                  "implicated": n["implicated"], "role": n["role"],
                  "props": n["props"]}}
        for nid, n in sorted(nodes.items())
    ]
    edge_elements = [
        {"data": {"id": f"e{i}", "source": source, "target": target,
                  "type": rel_type}}
        for i, (source, target, rel_type) in enumerate(sorted(edges))
    ]
    return {"nodes": node_elements, "edges": edge_elements}

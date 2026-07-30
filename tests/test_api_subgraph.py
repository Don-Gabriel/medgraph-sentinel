"""Evidence-subgraph tests: the pure 300-node cap/trim logic
(api/subgraph.py) and the endpoint against the fake session — Cytoscape
elements shape, hops semantics, cap + truncated flag, and determinism
under shuffled database row order (INTERFACES §6)."""
import pytest

from api.alerts import (Q_ALERT_ONE, Q_SUBGRAPH_EDGES, Q_SUBGRAPH_EXPAND,
                        Q_SUBGRAPH_SEEDS)
from api.subgraph import to_elements, trim_to_cap

# ---- pure trim logic ----

def test_trim_noop_under_cap():
    kept, truncated = trim_to_cap({"A", "B"}, [("A", "B", "X")], {"A"}, cap=300)
    assert kept == {"A", "B"} and truncated is False


def test_trim_keeps_implicated_then_bridges_then_degree():
    # I1 -- b1 -- b2 -- I2 is the bridge chain; h is a degree-3 hub off I1
    # with leaves l1/l2. At cap=5 the two bridges outrank the hub (tier 2
    # before tier 3), the hub's degree beats the leaves, so exactly l1/l2 go.
    nodes = {"I1", "I2", "b1", "b2", "h", "l1", "l2"}
    edges = [("I1", "b1", "R"), ("b1", "b2", "R"), ("b2", "I2", "R"),
             ("I1", "h", "R"), ("h", "l1", "R"), ("h", "l2", "R")]
    kept, truncated = trim_to_cap(nodes, edges, {"I1", "I2"}, cap=5)
    assert truncated is True
    assert kept == {"I1", "I2", "b1", "b2", "h"}


def test_trim_tie_breaks_on_id_ascending():
    # star: implicated centre, four degree-1 leaves; cap leaves room for 2 —
    # the two lexicographically-smallest leaf ids survive, always.
    nodes = {"CTR", "N1", "N2", "N3", "N4"}
    edges = [("CTR", n, "R") for n in ("N1", "N2", "N3", "N4")]
    kept, truncated = trim_to_cap(nodes, edges, {"CTR"}, cap=3)
    assert truncated is True and kept == {"CTR", "N1", "N2"}


def test_elements_shape_and_deterministic_edge_ids():
    nodes = {"B": {"type": "Broker", "label": "B Corp", "implicated": True,
                   "role": "kickback_broker", "props": {"id": "B"}},
             "A": {"type": "Clinic", "label": "A Clinic", "implicated": False,
                   "role": None, "props": {"id": "A"}}}
    edges = [("B", "A", "OWNS_STAKE_IN"), ("A", "B", "TRANSFERRED")]
    elements = to_elements(nodes, edges)
    assert [n["data"]["id"] for n in elements["nodes"]] == ["A", "B"]
    assert elements["edges"] == [
        {"data": {"id": "e0", "source": "A", "target": "B",
                  "type": "TRANSFERRED"}},
        {"data": {"id": "e1", "source": "B", "target": "A",
                  "type": "OWNS_STAKE_IN"}},
    ]


# ---- endpoint fixture graph: 321 nodes, slightly over the 300 cap ----
#
# CLI_000001 (implicated) joined by 5 implicated claims, each with a leaf
# patient, plus 310 non-implicated claims. Candidates for trimming are all
# degree-1 non-bridges, so the id tie-break decides: CLM_0001001..294 stay,
# CLM_0001295..310 and the 5 PAT_ leaves go.

CLINIC = "CLI_000001"
IMPL_CLAIMS = [f"CLM_{i:07d}" for i in range(1, 6)]
PATIENTS = [f"PAT_{i:06d}" for i in range(1, 6)]
EXTRA_CLAIMS = [f"CLM_{i:07d}" for i in range(1001, 1311)]


def build_fixture_graph():
    nodes = {CLINIC: ("Clinic", {"id": CLINIC, "name": "Elysium Care Clinic",
                                 "bed_count": 0})}
    edges = []
    for claim, patient in zip(IMPL_CLAIMS, PATIENTS):
        nodes[claim] = ("Claim", {"id": claim, "amount_usd": 900.0})
        nodes[patient] = ("Patient", {"id": patient, "full_name": "P. Fictional"})
        edges += [(claim, CLINIC, "AT_CLINIC"), (claim, patient, "FOR_PATIENT")]
    for claim in EXTRA_CLAIMS:
        nodes[claim] = ("Claim", {"id": claim, "amount_usd": 500.0})
        edges.append((claim, CLINIC, "AT_CLINIC"))
    implicated = {CLINIC: "ghost_clinic",
                  **{c: "suspect_claim" for c in IMPL_CLAIMS}}
    return nodes, edges, implicated


def install_subgraph_handlers(fake, alert_id, nodes, edges, implicated,
                              reverse_rows=False):
    """Generic fake for the three subgraph queries over an in-memory graph.
    eid == node id (elementId is opaque to the endpoint anyway).
    reverse_rows flips every row ordering to prove the endpoint sorts."""

    def order(rows):
        return list(reversed(rows)) if reverse_rows else rows

    neighbours = {nid: set() for nid in nodes}
    for source, target, _t in edges:
        neighbours[source].add(target)
        neighbours[target].add(source)

    def node_row(nid):
        node_type, props = nodes[nid]
        return {"eid": nid, "id": nid, "type": node_type, "props": dict(props)}

    def seeds(params):
        if params["id"] != alert_id:
            return []
        return order([{**node_row(nid), "role": role}
                      for nid, role in sorted(implicated.items())])

    def expand(params):
        found = sorted({m for eid in params["eids"] for m in neighbours[eid]})
        return order([node_row(nid) for nid in found])

    def induced(params):
        eids, all_eids = set(params["eids"]), set(params["all_eids"])
        rows = [{"source": s, "target": t, "type": rel_type}
                for s, t, rel_type in edges if s in eids and t in all_eids]
        return order(rows)

    def alert_one(params):
        return [{"id": alert_id}] if params["id"] == alert_id else []

    fake.handle(Q_SUBGRAPH_SEEDS, seeds)
    fake.handle(Q_SUBGRAPH_EXPAND, expand)
    fake.handle(Q_SUBGRAPH_EDGES, induced)
    fake.handle(Q_ALERT_ONE, alert_one)


@pytest.fixture
def big_graph_api(client, fake_session):
    install_subgraph_handlers(fake_session, "ALT_000001",
                              *build_fixture_graph())
    return client


def test_subgraph_cap_truncated_and_relevance(big_graph_api):
    body = big_graph_api.get("/api/v1/alerts/ALT_000001/subgraph?hops=1").json()
    assert body["truncated"] is True
    node_ids = [n["data"]["id"] for n in body["elements"]["nodes"]]
    assert len(node_ids) == 300  # the hard cap, exactly
    assert node_ids == sorted(node_ids)  # deterministic ordering
    # implicated always survive the trim
    for nid in [CLINIC, *IMPL_CLAIMS]:
        assert nid in node_ids
    # all-tied leaves: id ascending keeps CLM_0001294, drops 1295+ and PAT_
    assert "CLM_0001294" in node_ids and "CLM_0001295" not in node_ids
    assert not any(nid.startswith("PAT_") for nid in node_ids)
    # edges only among kept nodes: 5 implicated + 294 kept extra claims
    edges = body["elements"]["edges"]
    assert len(edges) == 299
    assert [e["data"]["id"] for e in edges] == [f"e{i}" for i in range(299)]
    clinic = next(n["data"] for n in body["elements"]["nodes"]
                  if n["data"]["id"] == CLINIC)
    assert clinic == {"id": CLINIC, "type": "Clinic",
                      "label": "Elysium Care Clinic", "implicated": True,
                      "role": "ghost_clinic",
                      "props": {"id": CLINIC, "name": "Elysium Care Clinic",
                                "bed_count": 0}}
    extra = next(n["data"] for n in body["elements"]["nodes"]
                 if n["data"]["id"] == "CLM_0001001")
    assert extra["implicated"] is False and extra["role"] is None


def test_subgraph_deterministic_under_row_order(client, fake_session):
    install_subgraph_handlers(fake_session, "ALT_000001",
                              *build_fixture_graph())
    first = client.get("/api/v1/alerts/ALT_000001/subgraph").json()
    second = client.get("/api/v1/alerts/ALT_000001/subgraph").json()
    assert first == second
    # now feed every row in reverse database order — output must not move
    install_subgraph_handlers(fake_session, "ALT_000001",
                              *build_fixture_graph(), reverse_rows=True)
    assert client.get("/api/v1/alerts/ALT_000001/subgraph").json() == first


def test_subgraph_hops_semantics(client, fake_session):
    # chain: implicated clinic -- claim -- patient; the patient is 2 hops out
    nodes = {"CLI_000009": ("Clinic", {"id": "CLI_000009", "name": "One"}),
             "CLM_0000009": ("Claim", {"id": "CLM_0000009"}),
             "PAT_000009": ("Patient", {"id": "PAT_000009"})}
    edges = [("CLM_0000009", "CLI_000009", "AT_CLINIC"),
             ("CLM_0000009", "PAT_000009", "FOR_PATIENT")]
    install_subgraph_handlers(fake_session, "ALT_000002", nodes, edges,
                              {"CLI_000009": "ghost_clinic"})
    one_hop = client.get("/api/v1/alerts/ALT_000002/subgraph").json()
    assert [n["data"]["id"] for n in one_hop["elements"]["nodes"]] == [
        "CLI_000009", "CLM_0000009"]  # default hops=1
    assert one_hop["truncated"] is False
    two_hop = client.get("/api/v1/alerts/ALT_000002/subgraph?hops=2").json()
    assert [n["data"]["id"] for n in two_hop["elements"]["nodes"]] == [
        "CLI_000009", "CLM_0000009", "PAT_000009"]


def test_subgraph_hops_validation(big_graph_api):
    for hops in (0, 3, -1):
        response = big_graph_api.get(
            f"/api/v1/alerts/ALT_000001/subgraph?hops={hops}")
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)


def test_subgraph_404_unknown_alert(big_graph_api):
    assert big_graph_api.get(
        "/api/v1/alerts/ALT_999999/subgraph").status_code == 404

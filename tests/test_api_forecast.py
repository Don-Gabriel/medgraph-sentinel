"""Forecast endpoint tests (ADR-037): response shape, per-typology
grouping, the least-squares projection math, and empty-graph safety."""
from api.forecast import Q_MONTHLY_ALL, Q_MONTHLY_FLAGGED, slope_per_month

MONTHS_ALL = [
    {"month": "2026-01", "claims": 100, "amount": 100000.0},
    {"month": "2026-02", "claims": 110, "amount": 120000.0},
    {"month": "2026-03", "claims": 120, "amount": 140000.0},
]
MONTHS_FLAGGED = [
    {"typology": "ghost_clinic", "month": "2026-01", "claims": 10, "amount": 10000.0},
    {"typology": "ghost_clinic", "month": "2026-02", "claims": 12, "amount": 14000.0},
    {"typology": "ghost_clinic", "month": "2026-03", "claims": 15, "amount": 18000.0},
    {"typology": "template_cloning", "month": "2026-02", "claims": 4, "amount": 5000.0},
    {"typology": "template_cloning", "month": "2026-03", "claims": 5, "amount": 6800.0},
]


def test_slope_per_month():
    assert slope_per_month([100.0, 200.0, 300.0]) == 100.0
    assert slope_per_month([500.0]) == 0.0
    assert slope_per_month([]) == 0.0
    assert slope_per_month([300.0, 200.0, 100.0]) == -100.0


def test_forecast_shape_and_projection(client, fake_session):
    fake_session.handle(Q_MONTHLY_ALL, MONTHS_ALL)
    fake_session.handle(Q_MONTHLY_FLAGGED, MONTHS_FLAGGED)
    body = client.get("/api/v1/forecast").json()

    assert body["window"] == {"start": "2026-01", "end": "2026-03"}
    assert "linear projection" in body["method"]
    # overall: perfectly linear +20k/month -> next = 140k + 20k
    nm = body["overall"]["next_month"]
    assert nm["amount_usd"] == 160000.0
    assert nm["slope_usd_per_month"] == 20000.0
    assert nm["direction"] == "rising"
    assert [s["month"] for s in body["overall"]["series"]] == [
        "2026-01", "2026-02", "2026-03"]

    # flagged: grouped per typology, sorted, totals and projections attached
    assert [f["typology"] for f in body["flagged"]] == [
        "ghost_clinic", "template_cloning"]
    ghost = body["flagged"][0]
    assert ghost["amount_usd_total"] == 42000.0
    assert ghost["next_month"]["amount_usd"] == 22000.0  # 18k + 4k slope
    assert ghost["next_month"]["direction"] == "rising"
    mill = body["flagged"][1]
    assert mill["amount_usd_total"] == 11800.0
    assert mill["next_month"]["amount_usd"] == 8600.0  # 6800 + 1800 slope


def test_forecast_empty_graph_is_safe(client, fake_session):
    fake_session.handle(Q_MONTHLY_ALL, [])
    fake_session.handle(Q_MONTHLY_FLAGGED, [])
    body = client.get("/api/v1/forecast").json()
    assert body["window"] == {"start": None, "end": None}
    assert body["flagged"] == []
    assert body["overall"]["series"] == []
    assert body["overall"]["next_month"]["amount_usd"] == 0.0
    assert body["overall"]["next_month"]["direction"] == "flat"

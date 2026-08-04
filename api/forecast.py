"""Risk-forecast endpoint (ADR-037 — the 'prediction' layer, honestly).

GET /api/v1/forecast returns the observed monthly claim series plus, per
typology, the flagged-exposure series (amounts of alert-implicated
claims) and a NEXT-MONTH projection. The projection is a least-squares
linear extrapolation of the observed monthly amounts — deliberately so:
it is explainable in one sentence, calibrated by nothing but the data on
screen, and the UI labels it "projection from observed trend". No model
is trained and nothing reads ground truth (hard rule 5).
"""
from fastapi import APIRouter, Depends

from api.graph import get_session, run_query

router = APIRouter(prefix="/api/v1")

# toString() tolerates both date-typed and string-typed procedure_date.
Q_MONTHLY_ALL = """\
MATCH (c:Claim)
WITH substring(toString(c.procedure_date), 0, 7) AS month,
     count(c) AS claims, sum(c.amount_usd) AS amount
RETURN month, claims, amount ORDER BY month
"""

# DISTINCT: a claim implicated by several alerts of one typology counts once.
Q_MONTHLY_FLAGGED = """\
MATCH (a:Alert)-[:IMPLICATES]->(c:Claim)
WITH DISTINCT a.typology AS typology, c
WITH typology, substring(toString(c.procedure_date), 0, 7) AS month,
     count(c) AS claims, sum(c.amount_usd) AS amount
RETURN typology, month, claims, amount ORDER BY typology, month
"""


def slope_per_month(amounts: list[float]) -> float:
    """Ordinary least-squares slope over equally spaced months. Pure
    stdlib on purpose — the whole 'model' must be explainable aloud."""
    n = len(amounts)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(amounts) / n
    sxx = sum((i - mean_x) ** 2 for i in range(n))
    sxy = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(amounts))
    return sxy / sxx if sxx else 0.0


def _projection(series: list[dict]) -> dict:
    amounts = [float(r["amount"]) for r in series]
    slope = slope_per_month(amounts)
    last = amounts[-1] if amounts else 0.0
    mean = sum(amounts) / len(amounts) if amounts else 0.0
    direction = "flat"
    if mean > 0 and abs(slope) >= 0.05 * mean:
        direction = "rising" if slope > 0 else "falling"
    return {"amount_usd": round(max(last + slope, 0.0), 2),
            "slope_usd_per_month": round(slope, 2),
            "direction": direction}


def _series(rows: list[dict]) -> list[dict]:
    return [{"month": r["month"], "claims": r["claims"],
             "amount_usd": round(float(r["amount"]), 2)} for r in rows]


@router.get("/forecast")
def forecast(session=Depends(get_session)) -> dict:
    overall_rows = run_query(session, Q_MONTHLY_ALL)
    flagged_rows = run_query(session, Q_MONTHLY_FLAGGED)

    by_typology: dict[str, list[dict]] = {}
    for r in flagged_rows:
        by_typology.setdefault(r["typology"], []).append(r)

    overall = _series(overall_rows)
    flagged = []
    for typology in sorted(by_typology):
        series = _series(by_typology[typology])
        flagged.append({
            "typology": typology,
            "series": series,
            "amount_usd_total": round(sum(s["amount_usd"] for s in series), 2),
            "next_month": _projection(by_typology[typology]),
        })
    return {
        "window": {"start": overall[0]["month"] if overall else None,
                   "end": overall[-1]["month"] if overall else None},
        "method": "least-squares linear projection of observed monthly amounts",
        "overall": {"series": overall,
                    "next_month": _projection(overall_rows)},
        "flagged": flagged,
    }

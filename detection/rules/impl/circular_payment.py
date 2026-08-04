"""Typology 6 — Circular payment (DETECTION_SPEC §6, revived per ADR-038).

Money leaves an account and returns to it through 1-3 intermediaries —
laundering kickbacks or recycling payouts to simulate turnover. Approach
exactly as specified: bounded variable-length Cypher enumerates cycle
candidates (cheap at this scale — the honest economy's transfers are
one-directional commission flows, so candidates are rare); Python does
the date-monotonicity, window and attrition filtering and the scoring.

FP guard (spec §6): refund/netting 2-cycles are legitimate business —
a 2-cycle scores above `low` only with amount similarity AND a short
window. Longer cycles through shell accounts (no OWNED_BY owner) are
what raise the score.
"""
from datetime import date

from .common import scale

# Each match is one rotation of a cycle: a cycle of length L appears L
# times (once per start node). Python dedupes on the relationship-id set.
# Pattern comprehension for owners: [] on shells (no OWNED_BY).
Q_CYCLES = """\
MATCH p = (a:PaymentAccount)-[ts:TRANSFERRED*2..5]->(a)
WITH nodes(p) AS ns, relationships(p) AS ts
RETURN [n IN ns | n.id] AS accounts,
       [n IN ns | [(n)-[:OWNED_BY]->(o) | o.id][0]] AS owners,
       [t IN ts | t.amount_usd] AS amounts,
       [t IN ts | toString(t.date)] AS dates,
       [t IN ts | elementId(t)] AS rel_ids
"""


def _valid_cycle(hops: list[dict], params: dict) -> bool:
    dates = [date.fromisoformat(h["date"][:10]) for h in hops]
    if any(b < a for a, b in zip(dates, dates[1:])):
        return False  # money must move forward in time
    if (dates[-1] - dates[0]).days > params["window_days"]:
        return False
    drop = 1 - params["max_hop_drop_pct"] / 100.0
    gain = 1 + params["max_hop_gain_pct"] / 100.0
    for prev, cur in zip(hops, hops[1:]):
        if not (prev["amount"] * drop <= cur["amount"] <= prev["amount"] * gain):
            return False  # not the same money moving on
    return True


def run(session, params: dict) -> list[dict]:
    w = params["weights"]
    seen: set[frozenset] = set()
    drafts = []
    for rec in session.run(Q_CYCLES):
        key = frozenset(rec["rel_ids"])
        if key in seen:
            continue  # another rotation of a cycle already processed
        seen.add(key)
        hops = [{"amount": float(a), "date": d}
                for a, d in zip(rec["amounts"], rec["dates"])]
        if not _valid_cycle(hops, params):
            continue
        # nodes(p) repeats the start account at the end — drop the echo
        accounts = list(rec["accounts"][:-1])
        owners = list(rec["owners"][:-1])
        shells = [acc for acc, own in zip(accounts, owners) if own is None]
        cycle_len = len(hops)
        first = date.fromisoformat(hops[0]["date"][:10])
        last = date.fromisoformat(hops[-1]["date"][:10])
        window = (last - first).days
        value = hops[0]["amount"]
        returned = hops[-1]["amount"]

        features = {
            "value": scale(value, 0.0, params["value_ref_usd"]),
            "shells": scale(len(shells), 0, params["shells_ref"]),
            "length": scale(cycle_len, 2, params["max_cycle_len"]),
        }
        score = 100.0 * sum(w[k] * features[k] for k in w)
        if cycle_len == 2:
            similar = abs(returned - value) <= value * (
                params["two_cycle_amount_tol_pct"] / 100.0)
            if not (similar and window <= params["two_cycle_window_days"]):
                # spec §6 FP mode: refund / netting between counterparties
                score = min(score, 49.9)
        if score < params["emit_min_score"]:
            continue

        owner_ids = sorted({o for o in owners if o})
        anchor = owner_ids[0] if owner_ids else accounts[0]
        implicated = [{"id": o, "role": "cycle_owner"} for o in owner_ids]
        implicated += [{"id": acc,
                        "role": "shell_account" if acc in shells
                        else "cycle_account"}
                       for acc in sorted(set(accounts))]

        drafts.append({
            "anchor_id": anchor,
            "score": score,
            "summary_params": {
                "cycle_len": cycle_len,
                "amount_out_usd": round(value, 2),
                "amount_back_usd": round(returned, 2),
                "attrition_pct": round((1 - returned / value) * 100, 1)
                if value else 0.0,
                "shell_count": len(shells),
                "window_days": window,
                "start_date": hops[0]["date"][:10],
                "owner_count": len(owner_ids),
                "features": {k: round(v, 3) for k, v in features.items()},
            },
            "implicated": implicated,
        })
    return drafts

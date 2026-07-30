"""Typology 5 — impossible travel (DETECTION_SPEC §5).

One targeted Cypher fetch (claim -> patient / treatment country / insurer),
then a plain consecutive-pair walk in Python:

- Identity group = all patients sharing a passport_no; a patient with no
  passport is a group of one. Shared passports are deliberately non-unique
  in the model — that is the typology's identity-multiplexing signal.
- Within a group, claims are ordered by procedure_date; each consecutive
  pair in *different* treatment countries is checked against the
  minimum-travel-days table (whole days, conservative: at 1 day everywhere,
  only same-day cross-country treatment is flagged — see the YAML).
- Same-country pairs are never flagged (ancillary claims of one journey
  land on nearby dates at the same clinic by design).

Scoring: a single flagged pair on a single identity is a low-severity
anomaly (our dates have day granularity — spec FP mode); the score climbs
with more pairs, with pairs that span different patient identities on one
passport, and with conflicting claims billed to different insurers.
"""
from collections import defaultdict
from datetime import date

Q_CLAIM_ROWS = """
MATCH (c:Claim)-[:FOR_PATIENT]->(p:Patient)
MATCH (c)-[:AT_CLINIC]->(:Clinic)-[:LOCATED_AT]->(:Address)
      -[:IN_COUNTRY]->(co:Country)
MATCH (c)-[:BILLED_TO]->(ins:Insurer)
RETURN p.id AS patient, p.passport_no AS passport, c.id AS claim,
       toString(c.procedure_date) AS day, co.code AS country, ins.id AS insurer
"""


def impossible_pairs(rows: list[dict], table: dict) -> list[dict]:
    """Consecutive-pair walk over one identity group's claims. Pure function
    (unit-tested without a database): rows need claim/day/country keys."""
    rows = sorted(rows, key=lambda x: (x["day"], x["claim"]))
    pairs = []
    for a, b in zip(rows, rows[1:]):
        if a["country"] == b["country"]:
            continue
        gap = (date.fromisoformat(b["day"]) - date.fromisoformat(a["day"])).days
        if gap < table[a["country"]][b["country"]]:
            pairs.append({"a": a, "b": b, "gap_days": gap})
    return pairs


def run(session, params: dict) -> list[dict]:
    table = params["travel_time_days"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in session.run(Q_CLAIM_ROWS):
        row = dict(r)
        # empty string = null (INTERFACES §2); no passport -> group of one
        key = row["passport"] or f"solo:{row['patient']}"
        groups[key].append(row)

    drafts = []
    for key in sorted(groups):
        rows = groups[key]
        pairs = impossible_pairs(rows, table)
        if not pairs:
            continue

        pair_patients = sorted({p[s]["patient"] for p in pairs for s in ("a", "b")})
        pair_insurers = sorted({p[s]["insurer"] for p in pairs for s in ("a", "b")})
        group_patients = sorted({r["patient"] for r in rows})
        score = params["base_score"]
        score += min(params["extra_pair_cap"],
                     params["extra_pair_bonus"] * (len(pairs) - 1))
        if len(pair_patients) > 1:
            score += params["multi_identity_bonus"]
            # Cross-insurer only escalates when identities multiplex: the
            # honest economy picks an insurer per journey, so a lone return
            # patient hitting two insurers on a same-day date artifact is
            # noise (measured: 6 such cases at seed 42), while one passport
            # billing several insurers under several names is the typology.
            if len(pair_insurers) > 1:
                score += params["multi_insurer_bonus"]

        patient_role = ("recycled_identity" if len(pair_patients) > 1
                        else "traveling_patient")
        claim_ids = sorted({p[s]["claim"] for p in pairs for s in ("a", "b")})
        drafts.append({
            "anchor_id": min(group_patients),
            "score": score,
            "summary_params": {
                "passport_shared": len(group_patients) > 1,
                "identity_count": len(group_patients),
                "conflicting_identities": len(pair_patients),
                "impossible_pairs": len(pairs),
                "insurers_involved": len(pair_insurers),
                "min_gap_days": min(p["gap_days"] for p in pairs),
                # first three pairs verbatim — the evidence a narrator needs
                "pairs": [{
                    "claims": [p["a"]["claim"], p["b"]["claim"]],
                    "countries": [p["a"]["country"], p["b"]["country"]],
                    "dates": [p["a"]["day"], p["b"]["day"]],
                    "gap_days": p["gap_days"],
                } for p in pairs[:3]],
            },
            "implicated": ([{"id": pid, "role": patient_role}
                            for pid in pair_patients]
                           + [{"id": cid, "role": "conflicting_claim"}
                              for cid in claim_ids]),
        })
    return drafts

"""Dev-set evaluation: detection alerts vs EMERGENT ground truth.

    NEO4J_URI=... NEO4J_PASSWORD=... DATA_DIR=data python -m evaluation.evaluate

THIS is the one place allowed to read data/ground_truth/ (INTERFACES §2:
detection/, api/, frontend/ never touch it — the circularity defense).
It reads alerts from the live graph and ground truth from DATA_DIR, and
prints per-typology precision/recall — including the misses. The held-out
evaluation (Aug 9) reuses this script against a separate data directory.

How "affected entities" are DERIVED per typology (fraud is parameterized,
never labeled — DATA_GENERATION §3), from actor_params.csv + generator
behaviour (generator/fraud.py, generator/economy.py):

- Typology 3 (kickback_ring): actor_params rows `steering_greed` name the
  steering brokers; `steering_partners` lists each broker's partner
  clinics (pipe-separated). A TP alert implicates a steering broker as
  kickback_broker; pair-level truth additionally requires the implicated
  clinic to be one of that broker's recorded partners.

- Typology 5 (impossible_travel): actor_params rows `identity_recycling`
  name the RECYCLING BROKERS; the affected patients are derived, not
  listed. Per generator/economy.py (build_journeys), a recycled journey
  clones the source patient into a NEW Patient node — new id and alias,
  same passport_no, dob and a shared device — so the clone groups are
  exactly the sets of >1 Patient sharing a non-empty passport_no whose
  claims run through a recycling broker. Cross-check (also from
  economy.py): build_static creates exactly the configured patient
  population before any journey runs, so clone ids are the tail beyond it
  (seed 42: PAT_010001..PAT_010008). A TP alert implicates any patient of
  a clone group.

- Typologies 1 and 2 (ghost_clinic, credential_laundering): their fraud is
  PLANTED, not emergent (DATA_GENERATION §4), and data/ground_truth/
  planted.csv is empty — the planted-cell generator lands Jul 31. Until
  then they are NOT EVALUABLE on the dev set; this report says so and
  gives honest-economy FP counts and emitted volume instead.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from neo4j import GraphDatabase

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

# Honest-economy alert counts at the FINAL committed thresholds — measured
# 2026-07-30 on seed 42 with every fraud gate zeroed (DATA_GENERATION §6
# calibration; procedure in detection/README.md). These are the documented
# FP rates: zero medium+ everywhere.
HONEST_FP = {
    "ghost_clinic": {"low": 5, "medium": 0, "high": 0},
    "credential_laundering": {"low": 62, "medium": 0, "high": 0},
    "kickback_ring": {"low": 0, "medium": 0, "high": 0},
    "impossible_travel": {"low": 6, "medium": 0, "high": 0},
}


def load_actor_params() -> list[dict]:
    with (DATA_DIR / "ground_truth" / "actor_params.csv").open(
            encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_planted() -> list[dict]:
    with (DATA_DIR / "ground_truth" / "planted.csv").open(
            encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def fetch_alerts(session) -> dict[str, list[dict]]:
    by_typology = defaultdict(list)
    result = session.run(
        "MATCH (a:Alert) OPTIONAL MATCH (a)-[r:IMPLICATES]->(n) "
        "RETURN a.id AS id, a.typology AS typology, a.score AS score, "
        "a.severity AS severity, a.summary_params AS summary, "
        "collect({id: coalesce(n.id, n.code), role: r.role}) AS implicated "
        "ORDER BY a.id")
    for rec in result:
        by_typology[rec["typology"]].append({
            "id": rec["id"], "score": rec["score"], "severity": rec["severity"],
            "summary": json.loads(rec["summary"]),
            "implicated": rec["implicated"],
        })
    return by_typology


def clone_groups(session, recycling_brokers: set[str]) -> list[dict]:
    """Derive recycled-identity groups (see module docstring, typology 5)."""
    groups = []
    result = session.run(
        # >1 patient on one passport; keep groups whose claims touch a
        # recycling broker — the passport index makes this cheap.
        "MATCH (p:Patient) WHERE p.passport_no IS NOT NULL "
        "WITH p.passport_no AS passport, collect(p) AS pats "
        "WHERE size(pats) > 1 "
        "UNWIND pats AS p "
        "OPTIONAL MATCH (c:Claim)-[:FOR_PATIENT]->(p) "
        "OPTIONAL MATCH (c)-[:ARRANGED_BY]->(b:Broker) "
        "OPTIONAL MATCH (c)-[:AT_CLINIC]->(:Clinic)-[:LOCATED_AT]->(:Address)"
        "-[:IN_COUNTRY]->(co:Country) "
        "RETURN passport, collect(DISTINCT p.id) AS patients, "
        "collect(DISTINCT b.id) AS brokers, "
        "collect({day: toString(c.procedure_date), country: co.code}) AS claims")
    for rec in result:
        if not recycling_brokers & set(b for b in rec["brokers"] if b):
            continue  # honest passport-format collision, not recycling
        days = sorted((c["day"], c["country"]) for c in rec["claims"] if c["day"])
        # tightest consecutive cross-country gap this group ever produced —
        # was an impossible-travel alert achievable at all?
        min_gap = None
        for (d1, c1), (d2, c2) in zip(days, days[1:]):
            if c1 != c2:
                gap = (date.fromisoformat(d2) - date.fromisoformat(d1)).days
                if min_gap is None or gap < min_gap:
                    min_gap = gap
        groups.append({"passport": rec["passport"],
                       "patients": sorted(rec["patients"]),
                       "min_cross_country_gap_days": min_gap})
    return groups


def evaluate_kickback(alerts: list[dict], params: list[dict]) -> dict:
    true_brokers = {r["actor_id"] for r in params
                    if r["param_name"] == "steering_greed"}
    partners = {r["actor_id"]: set(r["value"].split("|")) for r in params
                if r["param_name"] == "steering_partners"}
    tp_alerts, fp_alerts, hit_brokers, hit_pairs = [], [], set(), set()
    for a in alerts:
        broker = a["summary"].get("broker_id")
        clinic = a["summary"].get("clinic_id")
        if broker in true_brokers:
            tp_alerts.append(a["id"])
            hit_brokers.add(broker)
            if clinic in partners.get(broker, set()):
                hit_pairs.add((broker, clinic))
        else:
            fp_alerts.append(a["id"])
    n = len(alerts)
    return {
        "alerts": n, "tp": len(tp_alerts), "fp": len(fp_alerts),
        "precision": round(len(tp_alerts) / n, 3) if n else None,
        "recall_brokers": f"{len(hit_brokers)}/{len(true_brokers)}"
                          f" = {len(hit_brokers) / len(true_brokers):.3f}",
        "pair_level_tp": len(hit_pairs),
        "missed_brokers": sorted(true_brokers - hit_brokers),
        "fp_alert_ids": fp_alerts,
    }


def evaluate_impossible_travel(alerts: list[dict], groups: list[dict]) -> dict:
    truth_patients = {p for g in groups for p in g["patients"]}
    tp_alerts, fp_alerts, hit_groups = [], [], set()
    for a in alerts:
        implicated_patients = {e["id"] for e in a["implicated"]
                               if e["id"] and e["id"].startswith("PAT_")}
        if implicated_patients & truth_patients:
            tp_alerts.append(a["id"])
            for i, g in enumerate(groups):
                if implicated_patients & set(g["patients"]):
                    hit_groups.add(i)
        else:
            fp_alerts.append(a["id"])
    n = len(alerts)
    return {
        "alerts": n, "tp": len(tp_alerts), "fp": len(fp_alerts),
        "precision": round(len(tp_alerts) / n, 3) if n else None,
        "recall_groups": (f"{len(hit_groups)}/{len(groups)}"
                          + (f" = {len(hit_groups) / len(groups):.3f}"
                             if groups else " (no groups)")),
        "groups": groups,
    }


def severity_histogram(alerts: list[dict]) -> dict:
    hist = {"low": 0, "medium": 0, "high": 0}
    for a in alerts:
        hist[a["severity"]] += 1
    return hist


def main() -> int:
    params = load_actor_params()
    planted = load_planted()
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"),
              os.environ.get("NEO4J_PASSWORD", "")))
    try:
        with driver.session() as session:
            alerts = fetch_alerts(session)
            recyclers = {r["actor_id"] for r in params
                         if r["param_name"] == "identity_recycling"}
            groups = clone_groups(session, recyclers)
    finally:
        driver.close()

    report = {"dataset": str(DATA_DIR), "planted_rows": len(planted)}

    for key in ("ghost_clinic", "credential_laundering"):
        typology_planted = [r for r in planted if r["typology"] == key]
        if not typology_planted:
            report[key] = {
                "status": "not evaluable on the dev set until planted cells "
                          "land (scheduled Jul 31) — typologies 1/2 use "
                          "PLANTED fraud (DATA_GENERATION §4) and "
                          "planted.csv is empty",
                "emitted": len(alerts.get(key, [])),
                "emitted_severity": severity_histogram(alerts.get(key, [])),
                "honest_economy_fp": HONEST_FP[key],
            }
        else:  # ready for the moment planted cells exist
            truth = {r["entity_id"] for r in typology_planted}
            tp = [a["id"] for a in alerts.get(key, [])
                  if {e["id"] for e in a["implicated"]} & truth]
            n = len(alerts.get(key, []))
            hit = {e for a in alerts.get(key, [])
                   for e in (x["id"] for x in a["implicated"]) if e in truth}
            report[key] = {
                "alerts": n, "tp": len(tp), "fp": n - len(tp),
                "precision": round(len(tp) / n, 3) if n else None,
                "recall_entities": f"{len(hit)}/{len(truth)}",
                "honest_economy_fp": HONEST_FP[key],
            }

    report["kickback_ring"] = {
        **evaluate_kickback(alerts.get("kickback_ring", []), params),
        "emitted_severity": severity_histogram(alerts.get("kickback_ring", [])),
        "honest_economy_fp": HONEST_FP["kickback_ring"],
    }
    report["impossible_travel"] = {
        **evaluate_impossible_travel(alerts.get("impossible_travel", []), groups),
        "emitted_severity": severity_histogram(alerts.get("impossible_travel", [])),
        "honest_economy_fp": HONEST_FP["impossible_travel"],
    }
    json.dump(report, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
  claims run through a recycling broker. fraud.parallel_recycling
  (2026-07-31, the typology-5 fix) additionally books a fraction of clone
  events in PARALLEL windows: same identity, same day, different treatment
  country. Groups are therefore split against the travel-time table
  (generator/config.yaml travel_time_days, the same table the rule
  mirrors) into IMPOSSIBLE (some consecutive cross-country pair violates
  the table — detectable by construction) and FEASIBLE (reused but
  temporally consistent — undetectable by a whole-day travel rule, by
  design). Recall is reported against the impossible subset; the feasible
  remainder is reported separately, never counted as a miss.

- Typologies 1 and 2 (ghost_clinic, credential_laundering): their fraud is
  PLANTED with exact labels (DATA_GENERATION §4, generator/plant.py) in
  data/ground_truth/planted.csv (entity_id, cell_id, typology). Labels
  list CREATED cell entities only — honest entities a cell touches stay
  unlabeled so an alert pointing only at those still counts as a false
  positive. An alert is a TP if it implicates any labeled entity of its
  typology; a CELL counts as detected if any alert implicates any of its
  members. Both entity coverage and cell-level recall are reported. On an
  honest run (planted zeroed) the file is empty and the section reports
  honest FP counts only.
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
#
# Re-measured 2026-07-31 (dataset-freeze session) on an honest generation
# byte-identical to the pre-session generator's output: ghost_clinic 7 low
# (two entries at 32.3/32.5, just above the 32.0 emit floor),
# credential_laundering 63 low, kickback_ring 0, impossible_travel 6 low.
# Zero medium+ everywhere still holds — the calibration property survives;
# the low-count deltas vs the 07-30 note could not be reproduced from the
# committed rules + honest bytes and are flagged in the session report
# (drift is reported, never tuned away — DATA_GENERATION §6).
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


def load_travel_table() -> dict[str, dict[str, int]]:
    """The whole-day minimum-travel table (generator/config.yaml,
    travel_time_days) — the shared config the detection rule mirrors
    (OQ #5; tests keep the two in sync). Used here to derive which recycled
    groups are IMPOSSIBLE by construction, not merely reused."""
    import yaml
    cfg_path = Path(__file__).parent.parent / "generator" / "config.yaml"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))["travel_time_days"]


def clone_groups(session, recycling_brokers: set[str],
                 travel_table: dict) -> list[dict]:
    """Derive recycled-identity groups (see module docstring, typology 5),
    each classified impossible (some consecutive cross-country pair beats
    the travel table) or feasible (reused, but temporally consistent)."""
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
        # tightest consecutive cross-country pair this group ever produced,
        # and whether any pair violates the whole-day travel table — was an
        # impossible-travel alert achievable at all?
        min_gap, impossible = None, False
        for (d1, c1), (d2, c2) in zip(days, days[1:]):
            if c1 != c2:
                gap = (date.fromisoformat(d2) - date.fromisoformat(d1)).days
                if min_gap is None or gap < min_gap:
                    min_gap = gap
                required = travel_table.get(c1, {}).get(c2)
                if required is not None and gap < required:
                    impossible = True
        groups.append({"passport": rec["passport"],
                       "patients": sorted(rec["patients"]),
                       "min_cross_country_gap_days": min_gap,
                       "impossible": impossible})
    return groups


def evaluate_kickback(alerts: list[dict], params: list[dict],
                      planted: list[dict]) -> dict:
    """Truth = emergent steering brokers (actor_params). FPs are split:
    a "false positive" that implicates a PLANTED cell (e.g. a ghost-clinic
    feeder pair tripping the concentration gate) is fraud detected under
    the wrong typology, not honest noise — reported separately, still
    counted as FP for typology-3 precision."""
    true_brokers = {r["actor_id"] for r in params
                    if r["param_name"] == "steering_greed"}
    partners = {r["actor_id"]: set(r["value"].split("|")) for r in params
                if r["param_name"] == "steering_partners"}
    planted_ids = {r["entity_id"] for r in planted}
    tp_alerts, fp_alerts, fp_planted = [], [], []
    hit_brokers, hit_pairs = set(), set()
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
            if {e["id"] for e in a["implicated"] if e["id"]} & planted_ids:
                fp_planted.append(a["id"])
    n = len(alerts)
    return {
        "alerts": n, "tp": len(tp_alerts), "fp": len(fp_alerts),
        "fp_cross_typology_planted": fp_planted,
        "precision": round(len(tp_alerts) / n, 3) if n else None,
        "recall_brokers": f"{len(hit_brokers)}/{len(true_brokers)}"
                          f" = {len(hit_brokers) / len(true_brokers):.3f}",
        "pair_level_tp": len(hit_pairs),
        "missed_brokers": sorted(true_brokers - hit_brokers),
        "fp_alert_ids": fp_alerts,
    }


def evaluate_impossible_travel(alerts: list[dict], groups: list[dict]) -> dict:
    """Recall counts IMPOSSIBLE groups only — a whole-day travel rule cannot
    flag a feasible reuse, so scoring those as misses would measure the
    generator, not the rule. The feasible remainder is reported alongside."""
    truth_patients = {p for g in groups for p in g["patients"]}
    impossible = [g for g in groups if g["impossible"]]
    feasible = [g for g in groups if not g["impossible"]]
    tp_alerts, fp_alerts = [], []
    hit_impossible, hit_feasible = set(), set()
    for a in alerts:
        implicated_patients = {e["id"] for e in a["implicated"]
                               if e["id"] and e["id"].startswith("PAT_")}
        if implicated_patients & truth_patients:
            tp_alerts.append(a["id"])
            for g in impossible:
                if implicated_patients & set(g["patients"]):
                    hit_impossible.add(g["passport"])
            for g in feasible:
                if implicated_patients & set(g["patients"]):
                    hit_feasible.add(g["passport"])
        else:
            fp_alerts.append(a["id"])
    n = len(alerts)
    return {
        "alerts": n, "tp": len(tp_alerts), "fp": len(fp_alerts),
        "precision": round(len(tp_alerts) / n, 3) if n else None,
        "recall_impossible_groups": (
            f"{len(hit_impossible)}/{len(impossible)}"
            + (f" = {len(hit_impossible) / len(impossible):.3f}"
               if impossible else " (no impossible groups)")),
        "feasible_reused_groups": len(feasible),
        "feasible_reused_flagged": len(hit_feasible),
        "missed_impossible": sorted(g["passport"] for g in impossible
                                    if g["passport"] not in hit_impossible),
        "groups": groups,
    }


def evaluate_planted(alerts: list[dict], planted_rows: list[dict]) -> dict:
    """Typologies 1/2: alert-level precision against the labeled entities,
    plus cell-level recall (a cell is detected when any alert implicates
    any of its members) and per-cell entity coverage."""
    cells: dict[str, set[str]] = defaultdict(set)
    for r in planted_rows:
        cells[r["cell_id"]].add(r["entity_id"])
    truth = {e for members in cells.values() for e in members}
    tp_alerts, fp_alerts, hit = [], [], set()
    for a in alerts:
        implicated = {e["id"] for e in a["implicated"] if e["id"]}
        overlap = implicated & truth
        if overlap:
            tp_alerts.append(a["id"])
            hit |= overlap
        else:
            fp_alerts.append(a["id"])
    n = len(alerts)
    per_cell = {}
    for cell_id, members in sorted(cells.items()):
        per_cell[cell_id] = {
            "detected": bool(members & hit),
            "entities": len(members),
            "entities_implicated": len(members & hit),
        }
    detected = sum(1 for c in per_cell.values() if c["detected"])
    return {
        "alerts": n, "tp": len(tp_alerts), "fp": len(fp_alerts),
        "precision": round(len(tp_alerts) / n, 3) if n else None,
        "recall_cells": (f"{detected}/{len(cells)}"
                         + (f" = {detected / len(cells):.3f}" if cells else "")),
        "entity_coverage": f"{len(hit)}/{len(truth)}",
        "per_cell": per_cell,
        "missed_cells": sorted(c for c, v in per_cell.items() if not v["detected"]),
        "fp_alert_ids": fp_alerts,
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
            groups = clone_groups(session, recyclers, load_travel_table())
    finally:
        driver.close()

    report = {"dataset": str(DATA_DIR), "planted_rows": len(planted)}

    for key in ("ghost_clinic", "credential_laundering"):
        typology_planted = [r for r in planted if r["typology"] == key]
        if not typology_planted:
            report[key] = {
                "status": "no planted cells in this dataset (honest run or "
                          "planted gates zeroed) — typologies 1/2 use "
                          "PLANTED fraud (DATA_GENERATION §4); emitted "
                          "alerts below are all against unlabeled data",
                "emitted": len(alerts.get(key, [])),
                "emitted_severity": severity_histogram(alerts.get(key, [])),
                "honest_economy_fp": HONEST_FP[key],
            }
        else:
            report[key] = {
                **evaluate_planted(alerts.get(key, []), typology_planted),
                "emitted_severity": severity_histogram(alerts.get(key, [])),
                "honest_economy_fp": HONEST_FP[key],
            }

    report["kickback_ring"] = {
        **evaluate_kickback(alerts.get("kickback_ring", []), params, planted),
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

"""Held-out evaluation scorer — written BEFORE the one-shot run (ADR-034).

    NEO4J_URI=... NEO4J_PASSWORD=... DATA_DIR=<heldout data dir> \
        python -m evaluation.heldout

Reads scenario ground truth (data-dir ground_truth/scenario_*.csv) and the
alerts in the live graph, and reports, per scenario and per typology, which
scenario entities were implicated by which rules. Scenario-name -> expected
typology mapping is fixed here, blind, from the scenario filenames alone
(the sealed files carry no typology key by design).

What held-out scoring MEANS here, stated before results existed: the
scenario world adds only fraudulent structure (no new honest actors), so
this measures DETECTION of independently-parameterized fraud — recall per
scenario leg. Precision remains a dev-set property (ADR-031). Alerts that
implicate no scenario entity are the dev-set world re-firing and are
reported only as a count.
"""
import csv
import json
import os
import sys
from pathlib import Path

from api.graph import get_driver

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

# Fixed blind mapping: which rule each scenario is EXPECTED to trip.
# S5 is the deliberately-hard composite: every leg individually weak.
EXPECTED = {
    "heldout_S1_ghost_satellite": ["ghost_clinic"],
    "heldout_S2_license_shadow": ["credential_laundering"],
    "heldout_S3_quiet_kickback": ["kickback_ring"],
    "heldout_S4_split_ledger": ["impossible_travel"],
    "heldout_S5_confluence": ["ghost_clinic", "credential_laundering",
                              "kickback_ring", "impossible_travel"],
}


def scenario_entities() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in sorted((DATA_DIR / "ground_truth").glob("scenario_*.csv")):
        name = path.stem.removeprefix("scenario_")
        with path.open(encoding="utf-8") as fh:
            out[name] = {row["entity_id"] for row in csv.DictReader(fh)}
    return out


def main() -> int:
    scenarios = scenario_entities()
    if not scenarios:
        print(f"heldout: no scenario ground truth under {DATA_DIR}",
              file=sys.stderr)
        return 2

    with get_driver().session() as session:
        rows = [dict(r) for r in session.run(
            "MATCH (a:Alert)-[:IMPLICATES]->(n) "
            "RETURN a.id AS alert, a.typology AS typology, "
            "a.severity AS severity, a.score AS score, "
            "collect(coalesce(n.id, n.code)) AS targets ORDER BY a.id")]

    all_scenario_ents = set().union(*scenarios.values())
    report: dict = {"total_alerts": len(rows),
                    "alerts_touching_scenarios": 0, "scenarios": {}}
    legs_expected, legs_detected = 0, 0

    for name, ents in scenarios.items():
        touching = [r for r in rows if ents & set(r["targets"])]
        by_typ: dict[str, list] = {}
        for r in touching:
            by_typ.setdefault(r["typology"], []).append(
                {"alert": r["alert"], "severity": r["severity"],
                 "score": r["score"]})
        expected = EXPECTED[name]
        detected = [t for t in expected if t in by_typ]
        missed = [t for t in expected if t not in by_typ]
        unexpected = sorted(set(by_typ) - set(expected))
        legs_expected += len(expected)
        legs_detected += len(detected)
        report["scenarios"][name] = {
            "entities": len(ents), "expected_typologies": expected,
            "detected": detected, "missed": missed,
            "cross_typology_hits": unexpected, "alerts": by_typ,
        }

    report["alerts_touching_scenarios"] = sum(
        1 for r in rows if all_scenario_ents & set(r["targets"]))
    report["leg_recall"] = f"{legs_detected}/{legs_expected}"
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

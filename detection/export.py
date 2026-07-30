"""Export Alert nodes + IMPLICATES edges to committed CSVs (ADR-029).

Run ONCE per demo build, after the build-phase detection run:

    python -m detection.run          # writes alerts into the graph
    python -m detection.export       # graph -> data/csv/alerts.csv
                                     #        + data/csv/rel_implicates.csv
                                     #        + manifest count entries

The loader then loads alerts like any other data, so `docker compose up`
never computes detection (ADR-018 one-way chain; ADR-029). Rows are sorted
by id so re-exporting an identical graph is byte-identical.
"""
import csv
import json
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

ALERT_COLS = ["id", "typology", "rule_version", "score", "severity",
              "status", "note", "summary_params", "created_at"]
IMPL_COLS = ["source_id", "target_id", "role"]


def fetch_alerts(session) -> list[dict]:
    result = session.run(
        "MATCH (a:Alert) RETURN a ORDER BY a.id"
    )
    rows = []
    for record in result:
        node = record["a"]
        rows.append({
            "id": node["id"],
            "typology": node["typology"],
            "rule_version": node["rule_version"],
            "score": f"{float(node['score']):.1f}",
            "severity": node["severity"],
            "status": node["status"],
            "note": node.get("note", ""),
            "summary_params": node.get("summary_params", "{}"),
            "created_at": node["created_at"].iso_format(),
        })
    return rows


def fetch_implicates(session) -> list[dict]:
    result = session.run(
        "MATCH (a:Alert)-[r:IMPLICATES]->(n) "
        "RETURN a.id AS source_id, coalesce(n.id, n.code) AS target_id, "
        "r.role AS role ORDER BY source_id, target_id, role"
    )
    return [dict(record) for record in result]


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    # INTERFACES §2 conventions: UTF-8, header row, \n endings, RFC 4180
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            alerts = fetch_alerts(session)
            implicates = fetch_implicates(session)
    finally:
        driver.close()

    csv_dir = DATA_DIR / "csv"
    write_csv(csv_dir / "alerts.csv", ALERT_COLS, alerts)
    write_csv(csv_dir / "rel_implicates.csv", IMPL_COLS, implicates)

    manifest_path = DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["alerts"] = len(alerts)
    manifest["counts"]["rel_implicates"] = len(implicates)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"export: {len(alerts)} alerts, {len(implicates)} IMPLICATES edges "
          f"-> {csv_dir} ; manifest counts updated")
    if not alerts:
        print("export: WARNING — zero alerts exported (fine in dev, wrong "
              "for a demo build)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

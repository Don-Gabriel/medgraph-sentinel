"""Batch detection runner — registry-driven (docs/INTERFACES.md §5, ADR-008).

    python -m detection.run [--rules a,b] [--dry-run] [--created-at ISO]

Each rule is a YAML registry entry (detection/rules/<key>.yaml) plus an
implementation: a Python module (kind: python) or a parameterized Cypher
file (kind: cypher). Implementations never write to the graph — they return
*alert drafts*; this runner owns deletion, ID assignment, capping, severity
banding, and the writes. That split keeps every rule a pure "features in,
drafts out" function that one person can explain aloud.

Determinism (ADR-029): alert IDs are assigned by sorting all drafts of a run
by (rule key, -score, anchor entity id), so the same graph + same registry
always yields the same ALT_ numbering, and --created-at pins the timestamp
so a re-export is byte-identical. A full run numbers from ALT_000001; a
--rules subset run continues after the highest surviving alert ID (the
committed demo build is always a full run).
"""
import argparse
import importlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from neo4j import GraphDatabase

from .db import connect

RULES_DIR = Path(__file__).parent / "rules"
REQUIRED_KEYS = {"key", "name", "typology", "version", "kind", "impl",
                 "params", "severity_bands"}
KINDS = {"cypher", "python"}
IMPLICATED_CAP = 300  # per alert — mirrors the API subgraph cap (raised
                      # 200 -> 300 by owner decision 2026-07-30, INTERFACES §6)

# Draft contract (what every implementation returns, one dict per alert):
#   anchor_id      str   stable entity/pair key the alert is "about"
#   score          float raw 0-100 (runner clamps + rounds to one decimal)
#   summary_params dict  evidence numbers for narration (JSON-serializable)
#   implicated     list  of {"id": <entity id>, "role": <role string>}


class RuleConfigError(ValueError):
    """A registry YAML is malformed — fail before touching the graph."""


def load_registry(rules_dir: Path = RULES_DIR) -> list[dict]:
    """Parse + validate every rules/<key>.yaml, sorted by key (stable order)."""
    rules = []
    for path in sorted(rules_dir.glob("*.yaml")):
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate_rule(rule, path.stem)
        rules.append(rule)
    if not rules:
        raise RuleConfigError(f"no rule YAML files found under {rules_dir}")
    return rules


def validate_rule(rule: dict, stem: str) -> None:
    if not isinstance(rule, dict):
        raise RuleConfigError(f"{stem}.yaml: not a mapping")
    missing = REQUIRED_KEYS - set(rule)
    if missing:
        raise RuleConfigError(f"{stem}.yaml: missing keys {sorted(missing)}")
    if rule["key"] != stem:
        raise RuleConfigError(f"{stem}.yaml: key '{rule['key']}' != filename")
    if rule["kind"] not in KINDS:
        raise RuleConfigError(f"{stem}.yaml: kind must be one of {sorted(KINDS)}")
    if not isinstance(rule["params"], dict):
        raise RuleConfigError(f"{stem}.yaml: params must be a mapping")
    bands = rule["severity_bands"]
    if set(bands) != {"high", "medium"} or not bands["high"] > bands["medium"]:
        raise RuleConfigError(
            f"{stem}.yaml: severity_bands needs high > medium (got {bands})")
    if not isinstance(rule["version"], str):
        raise RuleConfigError(f"{stem}.yaml: version must be a string (quote it)")


def severity_for(score: float, bands: dict) -> str:
    """DATA_MODEL banding: high >= band, medium >= band, else low."""
    if score >= bands["high"]:
        return "high"
    if score >= bands["medium"]:
        return "medium"
    return "low"


def clamp_score(raw: float) -> float:
    """0-100, one decimal (DATA_MODEL Alert.score)."""
    return round(min(100.0, max(0.0, float(raw))), 1)


def cap_implicated(draft: dict) -> dict:
    """Enforce the 200-entity cap, dropping excess claims first (they are
    volume, not structure); whatever remains is trimmed from the highest IDs
    down so the cut is deterministic. The evidence counts survive in
    summary_params either way."""
    implicated = draft["implicated"]
    draft["summary_params"]["implicated_count"] = len(implicated)
    if len(implicated) <= IMPLICATED_CAP:
        return draft
    claims = sorted((e for e in implicated if e["id"].startswith("CLM_")),
                    key=lambda e: e["id"])
    core = [e for e in implicated if not e["id"].startswith("CLM_")]
    keep_claims = claims[:max(0, IMPLICATED_CAP - len(core))]
    kept = (core + keep_claims)[:IMPLICATED_CAP]  # core alone may exceed the cap
    draft["summary_params"]["truncated_implicates"] = len(implicated) - len(kept)
    draft["implicated"] = kept
    return draft


def run_rule(session, rule: dict) -> list[dict]:
    """Execute one rule implementation and normalize its drafts."""
    if rule["kind"] == "python":
        module = importlib.import_module(rule["impl"])
        drafts = module.run(session, rule["params"])
    else:  # cypher: the query returns one row per alert with the draft columns
        query = (RULES_DIR / rule["impl"]).read_text(encoding="utf-8")
        drafts = [
            {"anchor_id": r["anchor_id"], "score": r["score"],
             "summary_params": dict(r["summary_params"]),
             "implicated": [dict(e) for e in r["implicated"]]}
            for r in session.run(query, **rule["params"])
        ]
    for d in drafts:
        d["score"] = clamp_score(d["score"])
        cap_implicated(d)
    return drafts


def assign_ids(drafts_by_rule: dict[str, list[dict]], start: int = 1) -> list[dict]:
    """Deterministic ALT_ numbering: sorted (rule key, -score, anchor id)."""
    ordered = sorted(
        ((key, d) for key, drafts in drafts_by_rule.items() for d in drafts),
        key=lambda kd: (kd[0], -kd[1]["score"], kd[1]["anchor_id"]),
    )
    out = []
    for i, (key, d) in enumerate(ordered):
        out.append({**d, "rule_key": key, "id": f"ALT_{start + i:06d}"})
    return out


def max_surviving_alert_number(session) -> int:
    """Highest ALT_ number still in the graph (0 if none) — a --rules subset
    run must not collide with alerts owned by rules it did not touch."""
    rec = session.run("MATCH (a:Alert) RETURN max(a.id) AS m").single()
    return int(rec["m"].split("_")[1]) if rec and rec["m"] else 0


def delete_existing(session, key: str, version: str) -> int:
    """Idempotency per rule+version (INTERFACES §5)."""
    rec = session.run(
        "MATCH (a:Alert {typology: $k, rule_version: $v}) "
        "DETACH DELETE a RETURN count(*) AS n", k=key, v=version).single()
    return rec["n"]


# ID prefix -> label so IMPLICATES targets hit their uniqueness-constraint
# index (same routing trick as the loader, ADR-029). Country deliberately
# absent: no shipping rule implicates a Country.
PREFIX_LABEL = {
    "PAT_": "Patient", "DOC_": "Doctor", "CLI_": "Clinic", "BRK_": "Broker",
    "CLM_": "Claim", "CRD_": "Credential", "ACC_": "PaymentAccount",
    "DEV_": "Device", "ADR_": "Address", "PRC_": "Procedure", "INS_": "Insurer",
}


def write_alerts(session, rule: dict, alerts: list[dict], created_at: str) -> None:
    session.run(
        "UNWIND $rows AS row "
        "CREATE (a:Alert {id: row.id, typology: $typology, "
        "rule_version: $version, score: row.score, severity: row.severity, "
        "status: 'new', note: '', summary_params: row.summary_params, "
        "created_at: datetime($created_at)})",
        rows=[{"id": a["id"], "score": a["score"], "severity": a["severity"],
               "summary_params": json.dumps(a["summary_params"],
                                            separators=(",", ":"), sort_keys=True)}
              for a in alerts],
        typology=rule["key"], version=rule["version"], created_at=created_at,
    ).consume()
    edges: dict[str, list[dict]] = {}
    for a in alerts:
        for e in a["implicated"]:
            label = PREFIX_LABEL.get(e["id"][:4])
            if label is None:
                raise RuleConfigError(
                    f"{rule['key']}: implicated id '{e['id']}' has no routable prefix")
            edges.setdefault(label, []).append(
                {"alert_id": a["id"], "id": e["id"], "role": e["role"]})
    for label, rows in edges.items():
        session.run(
            f"UNWIND $rows AS row "
            f"MATCH (a:Alert {{id: row.alert_id}}) "
            f"MATCH (n:{label} {{id: row.id}}) "
            f"CREATE (a)-[:IMPLICATES {{role: row.role}}]->(n)",
            rows=rows).consume()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m detection.run")
    parser.add_argument("--rules", help="comma-separated rule keys (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="compute and summarize; write nothing")
    parser.add_argument("--created-at",
                        default=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        help="pin Alert.created_at (ADR-029 byte-identical builds)")
    args = parser.parse_args(argv)
    datetime.fromisoformat(args.created_at.replace("Z", "+00:00"))  # fail fast

    registry = load_registry()
    if args.rules:
        wanted = [k.strip() for k in args.rules.split(",") if k.strip()]
        known = {r["key"] for r in registry}
        unknown = [k for k in wanted if k not in known]
        if unknown:
            print(f"detection: unknown rule keys {unknown} "
                  f"(registry has {sorted(known)})", file=sys.stderr)
            return 2
        registry = [r for r in registry if r["key"] in wanted]

    t0 = time.monotonic()
    drafts_by_rule: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}
    driver = connect()
    try:
        with driver.session() as session:
            for rule in registry:
                t_rule = time.monotonic()
                try:
                    drafts_by_rule[rule["key"]] = run_rule(session, rule)
                    print(f"detection: {rule['key']} v{rule['version']} -> "
                          f"{len(drafts_by_rule[rule['key']])} draft alerts "
                          f"({time.monotonic() - t_rule:.1f}s)", file=sys.stderr)
                except Exception as exc:  # a broken rule must not sink the others
                    errors[rule["key"]] = f"{type(exc).__name__}: {exc}"
                    print(f"detection: RULE FAILED {rule['key']}: "
                          f"{errors[rule['key']]}", file=sys.stderr)

            by_rule = {r["key"]: r for r in registry}
            if args.dry_run:
                for key, drafts in drafts_by_rule.items():
                    bands = by_rule[key]["severity_bands"]
                    top = sorted(drafts, key=lambda d: (-d["score"], d["anchor_id"]))[:3]
                    for d in top:
                        print(f"  dry-run {key}: {d['anchor_id']} "
                              f"score={d['score']} "
                              f"sev={severity_for(d['score'], bands)}",
                              file=sys.stderr)
            else:
                for key in drafts_by_rule:  # replace-then-write per rule+version
                    n = delete_existing(session, key, by_rule[key]["version"])
                    if n:
                        print(f"detection: replaced {n} prior alerts for "
                              f"{key} v{by_rule[key]['version']}", file=sys.stderr)
                start = max_surviving_alert_number(session) + 1
                alerts = assign_ids(drafts_by_rule, start)
                for key in drafts_by_rule:
                    rule = by_rule[key]
                    mine = [a for a in alerts if a["rule_key"] == key]
                    for a in mine:
                        a["severity"] = severity_for(a["score"], rule["severity_bands"])
                    write_alerts(session, rule, mine, args.created_at)
    finally:
        driver.close()

    summary = {
        "rules_run": list(drafts_by_rule),
        "alerts_written": {k: len(v) for k, v in drafts_by_rule.items()}
        if not args.dry_run else {k: 0 for k in drafts_by_rule},
        "duration_s": round(time.monotonic() - t0, 1),
    }
    json.dump(summary, sys.stdout)
    print()
    if args.dry_run:
        for k, v in drafts_by_rule.items():
            print(f"dry-run: {k} would write {len(v)} alerts", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

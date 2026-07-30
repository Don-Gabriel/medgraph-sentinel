"""Wipe-and-load of data/csv/ into Neo4j per docs/INTERFACES.md §4.

Mechanism: LOAD CSV in batched implicit transactions (ADR-025, resolves
OQ #1 by benchmark). The CSVs are read by the *server*, so the compose file
mounts ./data/csv into the neo4j container's import directory; `file:///x.csv`
resolves there. The manifest is read by *this* process from DATA_DIR.

Every column is typed below; the table IS the mapping between INTERFACES §2
CSV columns and DATA_MODEL.md properties — change those docs first, then
this table.
"""
import json
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
SCHEMA_PATH = Path(os.environ.get("SCHEMA_PATH", "graph/schema.cypher"))
BOLT_WAIT_S = 120
BATCH_ROWS = 5000

# column type -> Cypher conversion expression ("empty string = null", INTERFACES §2)
_CONV = {
    "str": "CASE row.{c} WHEN '' THEN null ELSE row.{c} END",
    "int": "toInteger(row.{c})",
    "float": "toFloat(row.{c})",
    "date": "CASE row.{c} WHEN '' THEN null ELSE date(row.{c}) END",
    "datetime": "CASE row.{c} WHEN '' THEN null ELSE datetime(row.{c}) END",
    # rawstr: keep empty strings as-is (Alert.note/summary_params default "")
    "rawstr": "row.{c}",
}

# file stem -> (label, key column, {column: type})  — DATA_MODEL.md node tables
NODES: dict[str, tuple[str, str, dict[str, str]]] = {
    "patients": ("Patient", "id",
                 {"full_name": "str", "dob": "date", "gender": "str", "passport_no": "str"}),
    "doctors": ("Doctor", "id", {"full_name": "str", "specialty": "str"}),
    "clinics": ("Clinic", "id",
                {"name": "str", "bed_count": "int", "registration_date": "date",
                 "accreditation_status": "str"}),
    "brokers": ("Broker", "id", {"name": "str", "agency_name": "str"}),
    "claims": ("Claim", "id",
               {"amount_usd": "float", "procedure_date": "date", "submission_date": "date",
                "status": "str", "line_item_count": "int", "narrative_fingerprint": "str"}),
    "credentials": ("Credential", "id",
                    {"license_no": "str", "issuing_body": "str", "issue_date": "date",
                     "status": "str", "revocation_date": "date"}),
    "payment_accounts": ("PaymentAccount", "id",
                         {"account_ref": "str", "bank_name": "str", "opened_date": "date"}),
    "devices": ("Device", "id", {"device_hash": "str", "device_type": "str"}),
    "addresses": ("Address", "id", {"street": "str", "city": "str", "postcode": "str"}),
    "procedures": ("Procedure", "id",
                   {"code": "str", "category": "str", "name": "str", "base_cost_usd": "float"}),
    "insurers": ("Insurer", "id", {"name": "str"}),
    "countries": ("Country", "code", {"name": "str", "role": "str", "cost_multiplier": "float"}),
}

# file stem -> (TYPE, source label, target label, {prop: type})
# DATA_MODEL.md relationship table. Country nodes are keyed on `code`.
RELS: dict[str, tuple[str, str, str, dict[str, str]]] = {
    "rel_resides_in": ("RESIDES_IN", "Patient", "Country", {}),
    "rel_used_device": ("USED_DEVICE", "Patient", "Device",
                        {"first_seen": "date", "last_seen": "date"}),
    "rel_for_patient": ("FOR_PATIENT", "Claim", "Patient", {}),
    "rel_at_clinic": ("AT_CLINIC", "Claim", "Clinic", {}),
    "rel_performed_by": ("PERFORMED_BY", "Claim", "Doctor", {}),
    "rel_for_procedure": ("FOR_PROCEDURE", "Claim", "Procedure", {}),
    "rel_billed_to": ("BILLED_TO", "Claim", "Insurer", {}),
    "rel_arranged_by": ("ARRANGED_BY", "Claim", "Broker", {"commission_pct": "float"}),
    "rel_paid_to": ("PAID_TO", "Claim", "PaymentAccount", {}),
    "rel_holds": ("HOLDS", "Doctor", "Credential", {}),
    "rel_issued_in": ("ISSUED_IN", "Credential", "Country", {}),
    "rel_practises_at": ("PRACTISES_AT", "Doctor", "Clinic", {"since": "date"}),
    "rel_located_at": ("LOCATED_AT", "Clinic", "Address", {}),
    "rel_operates_from": ("OPERATES_FROM", "Broker", "Address", {}),
    "rel_in_country": ("IN_COUNTRY", "Address", "Country", {}),
    # OWNED_BY targets Clinic OR Broker (DATA_MODEL): loaded in two passes on
    # the ID prefix so both sides hit their uniqueness-constraint index.
    "rel_owned_by": ("OWNED_BY", "PaymentAccount", "Clinic|Broker", {}),
    "rel_owns_stake_in": ("OWNS_STAKE_IN", "Broker", "Clinic", {"pct": "float"}),
    "rel_transferred": ("TRANSFERRED", "PaymentAccount", "PaymentAccount",
                        {"amount_usd": "float", "date": "date"}),
    "rel_based_in": ("BASED_IN", "Insurer", "Country", {}),
}

_KEY = {"Country": "code"}  # node label -> id property (default "id")

# ---- Alert artifacts (ADR-029): written by `python -m detection.export`
# after the one-time build-phase detection run, committed like any other
# data, loaded here so compose-up never computes detection. OPTIONAL: a
# dataset regenerated before detection has run simply omits them from the
# manifest and these stems are skipped.
OPTIONAL_NODES: dict[str, tuple[str, str, dict[str, str]]] = {
    "alerts": ("Alert", "id",
               {"typology": "str", "rule_version": "str", "score": "float",
                "severity": "str", "status": "str", "note": "rawstr",
                "summary_params": "rawstr", "created_at": "datetime"}),
}
OPTIONAL_RELS: dict[str, tuple[str, str, str, dict[str, str]]] = {
    # target is ANY entity node: rows are routed to an indexed per-label
    # MATCH by ID prefix (same trick as OWNED_BY, generalized).
    "rel_implicates": ("IMPLICATES", "Alert", "*", {"role": "str"}),
}

# ID prefix -> label, for prefix-routed multi-label targets. Country is
# deliberately absent: no shipping rule implicates a Country node, and an
# unrouted row surfaces as a count mismatch rather than a silent skip.
PREFIX_LABEL: dict[str, str] = {
    "PAT_": "Patient", "DOC_": "Doctor", "CLI_": "Clinic", "BRK_": "Broker",
    "CLM_": "Claim", "CRD_": "Credential", "ACC_": "PaymentAccount",
    "DEV_": "Device", "ADR_": "Address", "PRC_": "Procedure", "INS_": "Insurer",
}


def _props_cypher(cols: dict[str, str]) -> str:
    return ", ".join(f"{c}: {_CONV[t].format(c=c)}" for c, t in cols.items())


def node_query(stem: str) -> str:
    label, key, cols = {**NODES, **OPTIONAL_NODES}[stem]
    props = f"{key}: row.{key}"
    if cols:
        props += ", " + _props_cypher(cols)
    return (
        f"LOAD CSV WITH HEADERS FROM 'file:///{stem}.csv' AS row "
        f"CALL (row) {{ CREATE (:{label} {{{props}}}) }} "
        f"IN TRANSACTIONS OF {BATCH_ROWS} ROWS"
    )


def rel_queries(stem: str) -> list[str]:
    rtype, src, dst, cols = {**RELS, **OPTIONAL_RELS}[stem]
    props = f" {{{_props_cypher(cols)}}}" if cols else ""
    # "*" = any entity label (IMPLICATES); "A|B" = explicit multi-label
    if dst == "*":
        targets = list(PREFIX_LABEL.values())
    else:
        targets = dst.split("|")
    label_prefix = {label: pfx for pfx, label in PREFIX_LABEL.items()}
    queries = []
    for target in targets:
        # multi-label targets: route rows by ID prefix so each MATCH is indexed
        prefix_filter = ""
        if len(targets) > 1:
            prefix_filter = (
                f"WITH row WHERE row.target_id STARTS WITH '{label_prefix[target]}' "
            )
        queries.append(
            f"LOAD CSV WITH HEADERS FROM 'file:///{stem}.csv' AS row "
            f"{prefix_filter}"
            f"CALL (row) {{ "
            f"MATCH (a:{src} {{{_KEY.get(src, 'id')}: row.source_id}}) "
            f"MATCH (b:{target} {{{_KEY.get(target, 'id')}: row.target_id}}) "
            f"CREATE (a)-[:{rtype}{props}]->(b) }} "
            f"IN TRANSACTIONS OF {BATCH_ROWS} ROWS"
        )
    return queries


def wait_for_bolt(driver, timeout_s: int = BOLT_WAIT_S) -> None:
    deadline = time.monotonic() + timeout_s
    attempt = 0
    while True:
        attempt += 1
        try:
            driver.verify_connectivity()
            print(f"loader: neo4j reachable (attempt {attempt})")
            return
        except Exception as exc:
            if time.monotonic() >= deadline:
                raise SystemExit(
                    f"loader: neo4j not reachable within {timeout_s}s: {exc}"
                ) from exc
            time.sleep(2)


def split_statements(cypher_text: str) -> list[str]:
    """Comments out, then split on ';' — a ';' inside a // comment must not
    split a statement (bit us on first M1 run). schema.cypher contains no
    string literals, so per-line comment stripping is safe."""
    code_lines = [raw.split("//", 1)[0] for raw in cypher_text.splitlines()]
    return [s.strip() for s in "\n".join(code_lines).split(";") if s.strip()]


def apply_schema(session) -> int:
    statements = split_statements(SCHEMA_PATH.read_text(encoding="utf-8"))
    for stmt in statements:
        session.run(stmt).consume()
    # relationship loading MATCHes on the constraint-backed indexes; make
    # sure they are online before the first LOAD CSV touches them
    session.run("CALL db.awaitIndexes()").consume()
    return len(statements)


def wipe(session) -> None:
    # implicit (auto-commit) transaction required for CALL ... IN TRANSACTIONS
    session.run(
        "MATCH (n) CALL (n) { DETACH DELETE n } "
        f"IN TRANSACTIONS OF {BATCH_ROWS} ROWS"
    ).consume()


def load_all(session, manifest_counts: dict[str, int]) -> None:
    node_stems = list(NODES) + [s for s in OPTIONAL_NODES if s in manifest_counts]
    rel_stems = list(RELS) + [s for s in OPTIONAL_RELS if s in manifest_counts]
    for stem in node_stems:
        t0 = time.monotonic()
        session.run(node_query(stem)).consume()
        print(f"loader: nodes  {stem:<18} {manifest_counts.get(stem, '?'):>7} rows "
              f"{time.monotonic() - t0:6.1f}s")
    for stem in rel_stems:
        t0 = time.monotonic()
        for q in rel_queries(stem):
            session.run(q).consume()
        print(f"loader: rels   {stem:<18} {manifest_counts.get(stem, '?'):>7} rows "
              f"{time.monotonic() - t0:6.1f}s")


def loaded_counts(session, expected: dict[str, int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    node_items = list(NODES.items()) + [
        (s, v) for s, v in OPTIONAL_NODES.items() if s in expected]
    rel_items = list(RELS.items()) + [
        (s, v) for s, v in OPTIONAL_RELS.items() if s in expected]
    for stem, (label, _key, _cols) in node_items:
        rec = session.run(f"MATCH (n:{label}) RETURN count(n) AS n").single()
        counts[stem] = rec["n"]
    for stem, (rtype, _s, _d, _cols) in rel_items:
        rec = session.run(f"MATCH ()-[r:{rtype}]->() RETURN count(r) AS n").single()
        counts[stem] = rec["n"]
    return counts


def diff_counts(expected: dict[str, int], actual: dict[str, int]) -> list[str]:
    """Human-readable mismatch lines; empty list means valid."""
    lines = []
    for key in sorted(set(expected) | set(actual)):
        e, a = expected.get(key), actual.get(key)
        if e != a:
            lines.append(f"  {key}: manifest={e} loaded={a}")
    return lines


def main() -> int:
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.is_file():
        print(f"loader: missing {manifest_path} — generate and commit the "
              "dataset first (ADR-005)", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected: dict[str, int] = manifest["counts"]

    known = set(NODES) | set(RELS) | set(OPTIONAL_NODES) | set(OPTIONAL_RELS)
    missing = [s for s in list(NODES) + list(RELS) if s not in expected]
    unknown = [s for s in expected if s not in known]
    if missing or unknown:
        print(f"loader: manifest/loader table mismatch — missing={missing} "
              f"unknown={unknown}", file=sys.stderr)
        return 2

    t_start = time.monotonic()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        wait_for_bolt(driver)
        with driver.session() as session:
            n = apply_schema(session)
            print(f"loader: schema applied ({n} statements)")
            t0 = time.monotonic()
            wipe(session)
            print(f"loader: wiped existing graph in {time.monotonic() - t0:.1f}s")
            load_all(session, expected)
            actual = loaded_counts(session, expected)
    finally:
        driver.close()

    problems = diff_counts(expected, actual)
    total_s = time.monotonic() - t_start
    if problems:
        print("loader: COUNT MISMATCH — refusing to declare success "
              "(INTERFACES §4):", file=sys.stderr)
        print("\n".join(problems), file=sys.stderr)
        return 1

    total_nodes = sum(v for k, v in actual.items() if not k.startswith("rel_"))
    total_rels = sum(v for k, v in actual.items() if k.startswith("rel_"))
    print(f"loader: OK — {total_nodes} nodes, {total_rels} relationships, "
          f"all {len(actual)} counts match manifest, {total_s:.1f}s total")
    return 0

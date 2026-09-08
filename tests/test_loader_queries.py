"""Loader pure-function tests (no Neo4j needed): the CSV->Cypher table must
cover the full INTERFACES §2 file set, and validation must fail loudly."""
import json
from pathlib import Path

from loader.load import (NODES, OPTIONAL_NODES, OPTIONAL_RELS, PREFIX_LABEL,
                         RELS, diff_counts, node_query, rel_queries,
                         split_statements)

DATA = Path(__file__).parent.parent / "data"
SCHEMA = Path(__file__).parent.parent / "graph" / "schema.cypher"


def test_split_statements_ignores_semicolons_in_comments():
    text = "// note; with semicolon\nCREATE INDEX a IF NOT EXISTS; // tail; comment\nCREATE INDEX b"
    assert split_statements(text) == ["CREATE INDEX a IF NOT EXISTS", "CREATE INDEX b"]


def test_real_schema_splits_into_only_create_statements():
    statements = split_statements(SCHEMA.read_text(encoding="utf-8"))
    assert len(statements) == 19  # 13 constraints + 6 indexes (ADR-024)
    assert all(s.startswith("CREATE ") for s in statements)


def test_table_covers_manifest_exactly():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    counts = set(manifest["counts"])
    mandatory = set(NODES) | set(RELS)
    optional = set(OPTIONAL_NODES) | set(OPTIONAL_RELS)
    # every mandatory stem present; nothing outside mandatory + optional
    assert mandatory <= counts <= mandatory | optional


def test_node_query_shapes():
    q = node_query("patients")
    assert "LOAD CSV WITH HEADERS FROM 'file:///patients.csv'" in q
    assert "CREATE (:Patient" in q and "IN TRANSACTIONS" in q
    # empty string = null convention applied to nullable strings
    assert "CASE row.passport_no WHEN '' THEN null" in q
    # countries key on `code`, not `id`
    assert "code: row.code" in node_query("countries")


def test_rel_query_shapes():
    (q,) = rel_queries("rel_arranged_by")
    assert "MATCH (a:Claim {id: row.source_id})" in q
    assert "MATCH (b:Broker {id: row.target_id})" in q
    assert "commission_pct: toFloat(row.commission_pct)" in q
    # OWNED_BY splits into two indexed passes on the target-ID prefix
    qs = rel_queries("rel_owned_by")
    assert len(qs) == 2
    assert any("STARTS WITH 'CLI_'" in q and "(b:Clinic" in q for q in qs)
    assert any("STARTS WITH 'BRK_'" in q and "(b:Broker" in q for q in qs)


def test_alert_stem_queries():
    # Alert nodes: datetime conversion + rawstr coalesces to "" (note
    # default ""). LOAD CSV yields null for an empty field, so the bare
    # `row.note` this once used stored no property and Neo4j warned
    # "property key does not exist" on every alert query.
    q = node_query("alerts")
    assert "CREATE (:Alert" in q
    assert "created_at: CASE row.created_at WHEN '' THEN null ELSE datetime(row.created_at) END" in q
    assert "note: coalesce(row.note, '')" in q
    assert "summary_params: coalesce(row.summary_params, '')" in q
    # IMPLICATES fans out to one indexed MATCH per entity label by ID prefix
    qs = rel_queries("rel_implicates")
    assert len(qs) == len(PREFIX_LABEL)
    assert all("MATCH (a:Alert {id: row.source_id})" in q for q in qs)
    assert any("STARTS WITH 'ACC_'" in q and "(b:PaymentAccount" in q for q in qs)
    assert any("STARTS WITH 'CLM_'" in q and "(b:Claim" in q for q in qs)
    assert all("role: CASE row.role WHEN '' THEN null ELSE row.role END" in q
               for q in qs)


def test_diff_counts_reports_all_mismatches():
    assert diff_counts({"a": 1}, {"a": 1}) == []
    lines = diff_counts({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
    assert len(lines) == 2
    assert any("b: manifest=2 loaded=3" in line for line in lines)
    assert any("c: manifest=None loaded=4" in line for line in lines)

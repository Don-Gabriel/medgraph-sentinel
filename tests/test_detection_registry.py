"""Detection pure-function tests (no Neo4j needed): registry validation,
severity banding, score clamping, deterministic alert numbering, the
implicated cap, the impossible-travel pair walk, and the OQ #5 contract
that the travel table in generator/config.yaml stays mirrored in the
impossible_travel rule params."""
from pathlib import Path

import pytest
import yaml

from detection.run import (RULES_DIR, RuleConfigError, assign_ids,
                           cap_implicated, clamp_score, load_registry,
                           severity_for, validate_rule)
from detection.rules.impl.common import scale
from detection.rules.impl.impossible_travel import impossible_pairs

REPO = Path(__file__).parent.parent
BANDS = {"high": 80, "medium": 50}


# ---- registry ----

def test_registry_loads_all_four_shipping_rules():
    rules = load_registry()
    assert [r["key"] for r in rules] == sorted(r["key"] for r in rules)
    assert {r["key"] for r in rules} == {"ghost_clinic", "credential_laundering",
                                         "kickback_ring", "impossible_travel"}
    assert {r["typology"] for r in rules} == {1, 2, 3, 5}  # ADR-024 descopes 4/6
    for r in rules:
        assert r["kind"] in ("cypher", "python")
        assert isinstance(r["version"], str)
        assert r["severity_bands"]["high"] > r["severity_bands"]["medium"]


def _valid_rule():
    return {"key": "x", "name": "X", "typology": 9, "version": "1.0",
            "kind": "python", "impl": "detection.rules.impl.x",
            "params": {}, "severity_bands": {"high": 80, "medium": 50}}


def test_validate_rule_rejects_bad_entries():
    rule = _valid_rule()
    validate_rule(rule, "x")  # sanity: the fixture itself is valid
    with pytest.raises(RuleConfigError):
        validate_rule(rule, "not_x")  # key must match filename
    for corrupt in (
        lambda r: r.pop("impl"),                                   # missing key
        lambda r: r.update(kind="sql"),                            # unknown kind
        lambda r: r.update(severity_bands={"high": 50, "medium": 80}),
        lambda r: r.update(severity_bands={"high": 80}),           # medium gone
        lambda r: r.update(params=[1, 2]),                         # not a mapping
        lambda r: r.update(version=1.0),                           # unquoted float
    ):
        rule = _valid_rule()
        corrupt(rule)
        with pytest.raises(RuleConfigError):
            validate_rule(rule, "x")


# ---- scoring primitives ----

def test_severity_banding_boundaries():
    assert severity_for(80.0, BANDS) == "high"
    assert severity_for(79.9, BANDS) == "medium"
    assert severity_for(50.0, BANDS) == "medium"
    assert severity_for(49.9, BANDS) == "low"
    assert severity_for(0.0, BANDS) == "low"


def test_clamp_score_range_and_precision():
    assert clamp_score(123.45) == 100.0
    assert clamp_score(-3) == 0.0
    assert clamp_score(59.96) == 60.0  # one decimal (DATA_MODEL)


def test_scale_is_a_clamped_linear_ramp():
    assert scale(5, 10, 20) == 0.0
    assert scale(15, 10, 20) == 0.5
    assert scale(25, 10, 20) == 1.0
    with pytest.raises(ValueError):
        scale(1, 5, 5)


# ---- alert-id determinism (INTERFACES §5 / ADR-029) ----

def _draft(anchor, score):
    return {"anchor_id": anchor, "score": score, "summary_params": {},
            "implicated": []}


def test_assign_ids_orders_by_rule_key_then_score_then_anchor():
    drafts = {
        "b_rule": [_draft("E2", 90.0), _draft("E1", 90.0), _draft("E3", 10.0)],
        "a_rule": [_draft("E9", 5.0)],
    }
    out = assign_ids(drafts)
    assert [(a["id"], a["rule_key"], a["anchor_id"]) for a in out] == [
        ("ALT_000001", "a_rule", "E9"),        # rule key sorts first
        ("ALT_000002", "b_rule", "E1"),        # then score desc, anchor asc
        ("ALT_000003", "b_rule", "E2"),
        ("ALT_000004", "b_rule", "E3"),
    ]
    # same input, same numbering — and a subset run continues after survivors
    assert [a["id"] for a in assign_ids(drafts)] == [a["id"] for a in out]
    assert assign_ids(drafts, start=69)[0]["id"] == "ALT_000069"


# ---- implicated cap ----

def test_cap_implicated_drops_claims_first_and_records_truncation():
    core = [{"id": "CLI_000001", "role": "ghost_clinic"},
            {"id": "BRK_000001", "role": "feeder_broker"}]
    # exceed the cap (300 since the 2026-07-30 contract change) by 101
    claims = [{"id": f"CLM_{i:07d}", "role": "suspect_claim"} for i in range(1, 400)]
    draft = {"anchor_id": "CLI_000001", "score": 90.0, "summary_params": {},
             "implicated": core + claims}
    capped = cap_implicated(draft)
    kept = capped["implicated"]
    assert len(kept) == 300
    assert kept[0]["id"] == "CLI_000001" and kept[1]["id"] == "BRK_000001"
    kept_claims = [e["id"] for e in kept if e["id"].startswith("CLM_")]
    assert kept_claims == sorted(kept_claims)  # deterministic cut
    assert capped["summary_params"]["implicated_count"] == 401
    assert capped["summary_params"]["truncated_implicates"] == 101


def test_cap_implicated_untouched_when_small():
    draft = {"anchor_id": "x", "score": 1.0, "summary_params": {},
             "implicated": [{"id": "PAT_000001", "role": "p"}]}
    assert "truncated_implicates" not in cap_implicated(draft)["summary_params"]
    assert cap_implicated(draft)["summary_params"]["implicated_count"] == 1


# ---- impossible-travel pair walk ----

TABLE = {"IN": {"TH": 1}, "TH": {"IN": 1}}


def _row(claim, day, country):
    return {"claim": claim, "day": day, "country": country}


def test_impossible_pairs_flags_only_same_day_cross_country():
    rows = [_row("CLM_1", "2026-01-01", "IN"),
            _row("CLM_2", "2026-01-01", "TH"),   # same day, other country -> hit
            _row("CLM_3", "2026-01-02", "IN")]   # next day -> possible
    pairs = impossible_pairs(rows, TABLE)
    assert len(pairs) == 1
    assert pairs[0]["a"]["claim"] == "CLM_1" and pairs[0]["b"]["claim"] == "CLM_2"
    assert pairs[0]["gap_days"] == 0


def test_impossible_pairs_ignores_same_country_and_orders_by_date():
    rows = [_row("CLM_2", "2026-01-05", "IN"),
            _row("CLM_1", "2026-01-01", "IN")]
    assert impossible_pairs(rows, TABLE) == []


# ---- OQ #5: travel table is shared config, mirrored in the rule ----

def test_travel_table_mirrors_generator_config():
    gen = yaml.safe_load((REPO / "generator" / "config.yaml")
                         .read_text(encoding="utf-8"))
    rule = yaml.safe_load((RULES_DIR / "impossible_travel.yaml")
                          .read_text(encoding="utf-8"))
    table = gen["travel_time_days"]
    assert rule["params"]["travel_time_days"] == table
    treatments = {c["code"] for c in gen["countries"]["treatment"]}
    assert set(table) == treatments
    for code, row in table.items():
        assert set(row) == treatments - {code}
        for other, days in row.items():
            assert days >= 1                      # whole-day, conservative
            assert table[other][code] == days     # symmetric

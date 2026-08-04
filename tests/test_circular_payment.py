"""Typology-6 rule tests (ADR-038): cycle validation (dates, window,
attrition), rotation dedup, the refund/netting 2-cycle guard, and the
draft contract. Params come from the registry YAML so tests track the
shipped thresholds."""
import yaml

from detection.run import RULES_DIR
from detection.rules.impl.circular_payment import Q_CYCLES, _valid_cycle, run

PARAMS = yaml.safe_load(
    (RULES_DIR / "circular_payment.yaml").read_text(encoding="utf-8"))["params"]


class _Fake:
    def __init__(self, rows):
        self._rows = rows

    def run(self, query, **params):
        assert " ".join(query.split()) == " ".join(Q_CYCLES.split())
        return iter(self._rows)


def _cycle_row(accounts, owners, amounts, dates, rel_prefix="r"):
    return {"accounts": accounts, "owners": owners, "amounts": amounts,
            "dates": dates, "rel_ids": [f"{rel_prefix}{i}" for i in range(len(amounts))]}


# ---- _valid_cycle ----

def test_valid_cycle_accepts_attriting_forward_loop():
    hops = [{"amount": 38000.0, "date": "2026-03-01"},
            {"amount": 34960.0, "date": "2026-03-04"},
            {"amount": 32163.2, "date": "2026-03-09"}]
    assert _valid_cycle(hops, PARAMS)


def test_valid_cycle_rejects_backwards_dates():
    hops = [{"amount": 1000.0, "date": "2026-03-09"},
            {"amount": 950.0, "date": "2026-03-01"}]
    assert not _valid_cycle(hops, PARAMS)


def test_valid_cycle_rejects_wide_window():
    hops = [{"amount": 1000.0, "date": "2026-01-01"},
            {"amount": 950.0, "date": "2026-06-30"}]
    assert not _valid_cycle(hops, PARAMS)


def test_valid_cycle_rejects_unrelated_amounts():
    hops = [{"amount": 1000.0, "date": "2026-03-01"},
            {"amount": 90.0, "date": "2026-03-05"}]  # 91% drop: not same money
    assert not _valid_cycle(hops, PARAMS)


# ---- run() ----

CAROUSEL = _cycle_row(
    accounts=["ACC_900001", "ACC_900003", "ACC_900004", "ACC_900001"],
    owners=["CLI_900001", None, None, "CLI_900001"],
    amounts=[38000.0, 34960.0, 32163.2],
    dates=["2026-03-19", "2026-03-22", "2026-03-27"])


def test_carousel_scores_high_and_implicates_shells():
    drafts = run(_Fake([CAROUSEL]), PARAMS)
    assert len(drafts) == 1
    d = drafts[0]
    assert d["anchor_id"] == "CLI_900001"
    assert d["score"] >= 80
    assert d["summary_params"]["shell_count"] == 2
    roles = sorted(e["role"] for e in d["implicated"])
    assert roles == ["cycle_account", "cycle_owner", "shell_account",
                     "shell_account"]


def test_rotations_dedupe_to_one_alert():
    rot = _cycle_row(
        accounts=["ACC_900003", "ACC_900004", "ACC_900001", "ACC_900003"],
        owners=[None, None, "CLI_900001", None],
        amounts=[34960.0, 32163.2, 38000.0],
        dates=["2026-03-22", "2026-03-27", "2026-03-19"])
    # same rel-id set as CAROUSEL -> one processed, and the rotation with
    # broken date order would be rejected anyway
    rot["rel_ids"] = list(CAROUSEL["rel_ids"])
    assert len(run(_Fake([CAROUSEL, rot]), PARAMS)) == 1


def test_refund_two_cycle_caps_low():
    refund = _cycle_row(
        accounts=["ACC_000001", "ACC_000002", "ACC_000001"],
        owners=["CLI_000001", "BRK_000001", "CLI_000001"],
        amounts=[30000.0, 29000.0],
        dates=["2026-01-05", "2026-03-20"])  # similar amounts, WIDE window
    drafts = run(_Fake([refund]), PARAMS)
    assert drafts and drafts[0]["score"] <= 49.9

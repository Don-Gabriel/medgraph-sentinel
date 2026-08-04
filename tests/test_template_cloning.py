"""Typology-4 rule tests (ADR-037): Hamming math, union-find clustering,
the run() draft contract against the fake session, and the spec §4
standardized-package FP guard. Params come from the real registry YAML so
the tests can never drift from the shipped thresholds."""
import yaml

from detection.run import RULES_DIR
from detection.rules.impl.template_cloning import (Q_BLOCKS, Q_SHARED_DEVICES,
                                                   _clusters, _hamming, run)


class _Fake:
    """Minimal stand-in for the conftest FakeSession (not importable here:
    a site-packages `tests` package shadows relative conftest imports)."""

    def __init__(self):
        self._h = {}

    def handle(self, query, rows):
        self._h[" ".join(query.split())] = rows

    def run(self, query, **params):
        return iter(self._h[" ".join(query.split())])


FakeSession = _Fake

PARAMS = yaml.safe_load(
    (RULES_DIR / "template_cloning.yaml").read_text(encoding="utf-8"))["params"]


def _claim(i, fp, amount=1000.0, patient=None, insurer="INS_000001",
           clinic="CLI_900001", broker="BRK_900001"):
    return {"id": f"CLM_90000{i:02d}", "fp": fp, "amount": amount,
            "patient": patient or f"PAT_9000{i:02d}", "clinic": clinic,
            "clinic_name": "Meridian Dental Institute", "insurer": insurer,
            "broker": broker}


# ---- pure functions ----

def test_hamming():
    assert _hamming("0" * 16, "0" * 16) == 0
    assert _hamming("0" * 16, "f" * 16) == 64
    assert _hamming("0000000000000001", "0000000000000003") == 1


def test_clusters_identical_and_near_join_distant_stay_out():
    a = "aaaaaaaaaaaaaaaa"
    near = f"{int(a, 16) ^ 0b111:016x}"          # 3 bits away
    far = f"{int(a, 16) ^ ((1 << 40) - 1):016x}"  # 40 bits away
    claims = [_claim(1, a), _claim(2, a), _claim(3, near), _claim(4, far)]
    groups = _clusters(claims, max_hamming=6)
    assert len(groups) == 1 and len(groups[0]) == 3
    assert {c["id"] for c in groups[0]} == {"CLM_9000001", "CLM_9000002",
                                            "CLM_9000003"}


# ---- run() against the fake session ----

def _session(claims, shared_devices):
    fake = FakeSession()
    fake.handle(Q_BLOCKS, [{"proc_id": "PRC_000010",
                            "proc_name": "Dental Implant Placement",
                            "line_items": 9, "claims": claims}])
    fake.handle(Q_SHARED_DEVICES, shared_devices)
    return fake

MILL_FP = "abcdefabcdefabcd"


def test_mill_cluster_scores_high_with_full_evidence():
    claims = [_claim(i, MILL_FP, amount=1000 + 10 * i,
                     insurer=f"INS_00000{i % 3 + 1}") for i in range(8)]
    shared = [{"id": "DEV_900001", "user_count": 5},
              {"id": "DEV_900002", "user_count": 4}]
    drafts = run(_session(claims, shared), PARAMS)
    assert len(drafts) == 1
    d = drafts[0]
    assert d["anchor_id"] == "CLI_900001"
    assert d["score"] >= 80, d["summary_params"]
    p = d["summary_params"]
    assert p["cluster_size"] == 8 and p["distinct_insurers"] == 3
    assert p["shared_devices"] == 2
    roles = {e["role"] for e in d["implicated"]}
    assert roles == {"mill_clinic", "feeder_broker", "shared_device",
                     "package_patient", "cloned_claim"}


def test_standardized_package_guard_caps_below_medium():
    # same clinic, ONE insurer, no shared devices: the honest LASIK-package
    # shape from spec §4 — must stay in the low band no matter the size
    claims = [_claim(i, MILL_FP, amount=1000, insurer="INS_000001",
                     broker=None) for i in range(12)]
    drafts = run(_session(claims, []), PARAMS)
    assert len(drafts) == 1
    assert drafts[0]["score"] <= 49.9
    assert drafts[0]["summary_params"]["distinct_insurers"] == 1


def test_loose_amounts_are_not_a_package():
    claims = [_claim(i, MILL_FP, amount=500 + 300 * i) for i in range(6)]
    assert run(_session(claims, []), PARAMS) == []


def test_single_patient_resubmission_is_not_this_typology():
    claims = [_claim(i, MILL_FP, patient="PAT_900001") for i in range(5)]
    assert run(_session(claims, []), PARAMS) == []


def test_small_clusters_never_emit():
    claims = [_claim(1, MILL_FP), _claim(2, MILL_FP),
              _claim(3, "0" * 16), _claim(4, "f" * 16)]
    assert run(_session(claims, []), PARAMS) == []

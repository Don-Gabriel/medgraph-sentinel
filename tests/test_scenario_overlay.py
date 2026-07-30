"""Scenario-overlay tests (INTERFACES §3, incl. the 2026-07-30 extensions).

The committed fixtures under data/scenarios/ are schema smoke tests, NOT
fraud test sets (ADR-027: held-out scenarios live outside the repo; overlay
tooling is built against the schema + these fixtures only). Covered here:

- every actor kind (clinic/broker/doctor/credential/patients pool)
- country pins materializing address + IN_COUNTRY / OPERATES_FROM
- edges between refs and existing IDs (country codes are IDs)
- journeys: invented | recycled:<n> | pool:<ref>, doctor pin
- transfers with count, shells and attrition
- scenario-reserved ID ranges (no collision with base entities)
- ground-truth emission (scenario_<name>.csv) + manifest scenarios_applied
- byte-determinism with scenarios; base bytes unaffected by overlay use
"""
import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from generator.__main__ import main

REPO = Path(__file__).parent.parent
FIXTURE_SMOKE = REPO / "data" / "scenarios" / "fixture_smoke.yaml"
FIXTURE_RECYCLED = REPO / "data" / "scenarios" / "fixture_recycled.yaml"

SMALL_POPULATIONS = {"patients": 300, "doctors": 60, "clinics": 30, "brokers": 12,
                     "insurers": 6}


@pytest.fixture()
def small_config(tmp_path: Path) -> Path:
    base = yaml.safe_load((REPO / "generator" / "config.yaml").read_bytes())
    base["populations"] = SMALL_POPULATIONS
    p = tmp_path / "small.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    return p


def _read(out: Path, name: str) -> list[dict]:
    with open(out / "csv" / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _digest_tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


@pytest.fixture()
def overlay_out(tmp_path: Path, small_config: Path) -> Path:
    out = tmp_path / "overlay"
    assert main(["--seed", "42", "--out", str(out), "--config", str(small_config),
                 "--scenario", str(FIXTURE_SMOKE),
                 "--scenario", str(FIXTURE_RECYCLED)]) == 0
    return out


def test_scenario_ids_use_reserved_range_and_never_collide(overlay_out: Path):
    truth = list(csv.DictReader(open(
        overlay_out / "ground_truth" / "scenario_fixture_smoke.csv",
        encoding="utf-8", newline="")))
    created = [r["entity_id"] for r in truth]
    scn_ids = [e for e in created if not e.startswith(("CLI_0", "BRK_0", "DOC_0"))]
    assert scn_ids, "scenario created no reserved-range entities?"
    for e in scn_ids:
        prefix, num = e.split("_")
        assert int(num) >= (9000001 if prefix == "CLM" else 900001), e
    # base files never contain reserved-range IDs when no scenario made them
    base_patients = {r["id"] for r in _read(overlay_out, "patients.csv")}
    assert all(int(p.split("_")[1]) < 900001 or p in created or
               p in {r["entity_id"] for r in csv.DictReader(open(
                   overlay_out / "ground_truth" / "scenario_fixture_recycled.csv",
                   encoding="utf-8", newline=""))}
               for p in base_patients)


def test_all_actor_kinds_and_country_pins_materialize(overlay_out: Path):
    truth = {r["entity_id"] for r in csv.DictReader(open(
        overlay_out / "ground_truth" / "scenario_fixture_smoke.csv",
        encoding="utf-8", newline=""))}
    clinics = {r["id"]: r for r in _read(overlay_out, "clinics.csv")}
    brokers = {r["id"]: r for r in _read(overlay_out, "brokers.csv")}
    doctors = {r["id"]: r for r in _read(overlay_out, "doctors.csv")}
    creds = {r["id"]: r for r in _read(overlay_out, "credentials.csv")}
    scn_clinic = next(i for i in truth if i.startswith("CLI_9"))
    scn_broker = next(i for i in truth if i.startswith("BRK_9"))
    scn_doctor = next(i for i in truth if i.startswith("DOC_9"))
    scn_cred = next(i for i in truth if i.startswith("CRD_9"))
    assert clinics[scn_clinic]["bed_count"] == "0"
    assert clinics[scn_clinic]["accreditation_status"] == "none"
    assert doctors[scn_doctor]["specialty"] == "dental"
    assert creds[scn_cred]["license_no"] == "MC-TR88231"
    assert creds[scn_cred]["status"] == "revoked"
    # country pin TH: clinic address in TH, broker operates from a TH address
    located = {r["source_id"]: r["target_id"]
               for r in _read(overlay_out, "rel_located_at.csv")}
    operates = {r["source_id"]: r["target_id"]
                for r in _read(overlay_out, "rel_operates_from.csv")}
    in_country = {r["source_id"]: r["target_id"]
                  for r in _read(overlay_out, "rel_in_country.csv")}
    assert in_country[located[scn_clinic]] == "TH"
    assert in_country[operates[scn_broker]] == "TH"
    # ISSUED_IN edge to an existing country ID
    issued = {r["source_id"]: r["target_id"]
              for r in _read(overlay_out, "rel_issued_in.csv")}
    assert issued[scn_cred] == "TR"
    # HOLDS edge assigned the holder
    holds = {r["target_id"]: r["source_id"] for r in _read(overlay_out, "rel_holds.csv")}
    assert holds[scn_cred] == scn_doctor
    # OWNS_STAKE_IN between refs, with props
    stakes = {(r["source_id"], r["target_id"]): r["pct"]
              for r in _read(overlay_out, "rel_owns_stake_in.csv")}
    assert stakes[(scn_broker, scn_clinic)] == "40.0"
    # broker params recorded as emergent incentive ground truth
    params = {(r["actor_id"], r["param_name"]): r["value"]
              for r in csv.DictReader(open(
                  overlay_out / "ground_truth" / "actor_params.csv",
                  encoding="utf-8", newline=""))}
    assert params[(scn_broker, "steering_greed")] == "0.9"


def test_pool_reuses_same_patient_nodes_and_doctor_pin_holds(overlay_out: Path):
    truth = {r["entity_id"] for r in csv.DictReader(open(
        overlay_out / "ground_truth" / "scenario_fixture_smoke.csv",
        encoding="utf-8", newline=""))}
    scn_doctor = next(i for i in truth if i.startswith("DOC_9"))
    scn_clinic = next(i for i in truth if i.startswith("CLI_9"))
    for_patient = {r["source_id"]: r["target_id"]
                   for r in _read(overlay_out, "rel_for_patient.csv")}
    performed = {r["source_id"]: r["target_id"]
                 for r in _read(overlay_out, "rel_performed_by.csv")}
    at_clinic = {r["source_id"]: r["target_id"]
                 for r in _read(overlay_out, "rel_at_clinic.csv")}
    pinned_claims = [c for c, d in performed.items() if d == scn_doctor]
    assert pinned_claims, "doctor pin routed no claims"
    assert all(at_clinic[c] == scn_clinic for c in pinned_claims)
    # 24 pool journeys over 8 identities: each pool patient carries >1
    # journey's claims — SAME node reused, no clones
    pool_patients = sorted({for_patient[c] for c in pinned_claims})
    assert len(pool_patients) == 8
    patients = {r["id"]: r for r in _read(overlay_out, "patients.csv")}
    passports = [patients[p]["passport_no"] for p in pool_patients]
    assert len(set(passports)) == 8  # distinct identities, not clones


def test_recycled_journeys_clone_identities(overlay_out: Path):
    truth = {r["entity_id"] for r in csv.DictReader(open(
        overlay_out / "ground_truth" / "scenario_fixture_recycled.csv",
        encoding="utf-8", newline=""))}
    patients = {r["id"]: r for r in _read(overlay_out, "patients.csv")}
    scn_patients = [patients[i] for i in truth if i.startswith("PAT_9")]
    # 9 journeys over recycled:3 -> 3 sources + 6 clones (+3 invented at the
    # base clinic): clones share a passport with their source
    from collections import Counter
    shared = [pp for pp, n in Counter(p["passport_no"] for p in scn_patients).items()
              if n > 1]
    assert len(shared) == 3  # each recycled identity became a clone group


def test_transfers_with_count_shells_and_attrition(overlay_out: Path):
    truth = {r["entity_id"] for r in csv.DictReader(open(
        overlay_out / "ground_truth" / "scenario_fixture_smoke.csv",
        encoding="utf-8", newline=""))}
    owned = {r["source_id"] for r in _read(overlay_out, "rel_owned_by.csv")}
    scn_accounts = {i for i in truth if i.startswith("ACC_9")}
    shells = scn_accounts - owned
    assert len(shells) >= 2  # two shell hops in the fixture path
    transfers = _read(overlay_out, "rel_transferred.csv")
    starts = [t for t in transfers if t["amount_usd"] == "40000.00"]
    assert len(starts) == 2  # count: 2 -> two chains at the entry amount
    hop2 = [t for t in transfers if t["source_id"] in shells
            and t["amount_usd"] == "36800.00"]  # 40000 * (1 - 8%)
    assert len(hop2) == 2


def test_same_seed_same_scenarios_byte_identical(tmp_path: Path, small_config: Path):
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    argv = ["--seed", "42", "--config", str(small_config),
            "--scenario", str(FIXTURE_SMOKE), "--scenario", str(FIXTURE_RECYCLED)]
    assert main(argv + ["--out", str(out_a)]) == 0
    # flag order must not matter: the applied SET defines the bytes
    argv_swapped = ["--seed", "42", "--config", str(small_config),
                    "--scenario", str(FIXTURE_RECYCLED), "--scenario", str(FIXTURE_SMOKE)]
    assert main(argv_swapped + ["--out", str(out_b)]) == 0
    assert _digest_tree(out_a) == _digest_tree(out_b)


def test_overlay_leaves_base_generation_untouched(tmp_path: Path, small_config: Path):
    """Applying a scenario only APPENDS: every base row survives byte-for-byte
    (scenario passes draw from the RNG strictly after base generation)."""
    plain, overlaid = tmp_path / "plain", tmp_path / "overlaid"
    assert main(["--seed", "42", "--out", str(plain),
                 "--config", str(small_config)]) == 0
    assert main(["--seed", "42", "--out", str(overlaid),
                 "--config", str(small_config),
                 "--scenario", str(FIXTURE_SMOKE)]) == 0
    for f in sorted((plain / "csv").glob("*.csv")):
        base_rows = set(f.read_text(encoding="utf-8").splitlines())
        new_rows = set((overlaid / "csv" / f.name).read_text(encoding="utf-8").splitlines())
        assert base_rows <= new_rows, f.name


def test_manifest_records_applied_scenarios(overlay_out: Path):
    manifest = json.loads((overlay_out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenarios_applied"] == ["fixture_recycled", "fixture_smoke"]
    for name, count in manifest["counts"].items():
        lines = (overlay_out / "csv" / f"{name}.csv").read_text(
            encoding="utf-8").strip().splitlines()
        assert len(lines) - 1 == count, name

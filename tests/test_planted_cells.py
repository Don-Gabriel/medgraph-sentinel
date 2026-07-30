"""Planted-cell tests (DATA_GENERATION §4) + the typology-5 parallel
recycling fix. Small world keeps each generation in seconds."""
import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pytest
import yaml

from generator.__main__ import main

REPO = Path(__file__).parent.parent
SMALL_POPULATIONS = {"patients": 300, "doctors": 60, "clinics": 30, "brokers": 12,
                     "insurers": 6}


def _small_config(tmp_path: Path, honest: bool = False,
                  boost_recycling: bool = False) -> Path:
    base = yaml.safe_load((REPO / "generator" / "config.yaml").read_bytes())
    base["populations"] = SMALL_POPULATIONS
    if honest:  # every fraud gate zeroed AND planted cells zeroed
        base["fraud"]["overbilling"]["clinic_rate"] = 0.0
        base["fraud"]["steering"]["broker_rate"] = 0.0
        base["fraud"]["identity_recycling"]["broker_rate"] = 0.0
        base["fraud"]["identity_recycling"]["parallel_share"] = 0.0
        base["fraud"]["shell_layering"]["pair_rate"] = 0.0
        base["planted"]["ghost_clinics"]["cells"] = 0
        base["planted"]["credential_mills"]["cells"] = 0
    if boost_recycling:
        # 12 brokers x the default 2% rate would leave the small world with
        # no recyclers at all; the parallel-billing test needs some
        base["fraud"]["identity_recycling"].update(
            broker_rate=0.3, reuse_min=0.5, reuse_max=0.8, parallel_share=1.0)
    name = "honest.yaml" if honest else ("boosted.yaml" if boost_recycling
                                         else "small.yaml")
    p = tmp_path / name
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    return p


def _read(out: Path, name: str) -> list[dict]:
    with open(out / "csv" / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def default_out(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("planted")
    out = tmp / "default"
    assert main(["--seed", "42", "--out", str(out),
                 "--config", str(_small_config(tmp))]) == 0
    return out


def _planted(out: Path) -> list[dict]:
    with open(out / "ground_truth" / "planted.csv", encoding="utf-8",
              newline="") as fh:
        return list(csv.DictReader(fh))


def test_planted_cells_present_and_labeled(default_out: Path):
    rows = _planted(default_out)
    by_typ = defaultdict(set)
    for r in rows:
        by_typ[r["typology"]].add(r["cell_id"])
    assert len(by_typ["ghost_clinic"]) == 3
    assert len(by_typ["credential_laundering"]) == 3


def test_ghost_cell_structure(default_out: Path):
    rows = [r for r in _planted(default_out) if r["cell_id"] == "ghost_1"]
    ids = {r["entity_id"] for r in rows}
    clinic = next(i for i in ids if i.startswith("CLI_"))
    broker = next(i for i in ids if i.startswith("BRK_"))
    accounts = {i for i in ids if i.startswith("ACC_")}
    patients = {i for i in ids if i.startswith("PAT_")}
    claims = {i for i in ids if i.startswith("CLM_")}
    assert len(accounts) == 2 and patients and claims
    # paper clinic: zero beds
    crow = next(r for r in _read(default_out, "clinics.csv") if r["id"] == clinic)
    assert crow["bed_count"] == "0"
    # cell claims all land at the cell clinic; feeder arranges the bulk;
    # payouts concentrate on one hub account
    at_clinic = {r["source_id"]: r["target_id"]
                 for r in _read(default_out, "rel_at_clinic.csv")}
    assert all(at_clinic[c] == clinic for c in claims)
    arranged = {r["source_id"]: r["target_id"]
                for r in _read(default_out, "rel_arranged_by.csv")}
    feeder_share = sum(1 for c in claims if arranged.get(c) == broker) / len(claims)
    assert feeder_share > 0.8
    paid = {r["source_id"]: r["target_id"] for r in _read(default_out, "rel_paid_to.csv")}
    top_share = Counter(paid[c] for c in claims).most_common(1)[0][1] / len(claims)
    assert top_share > 0.8
    # invented one-journey patients: every cell patient is claims-exclusive
    # to the cell clinic
    for_patient = {r["source_id"]: r["target_id"]
                   for r in _read(default_out, "rel_for_patient.csv")}
    pats_claims = defaultdict(list)
    for c, p in for_patient.items():
        pats_claims[p].append(c)
    assert all(set(pats_claims[p]) <= claims for p in patients)


def test_credential_cells_share_licence_and_post_revocation_volume(default_out: Path):
    planted = _planted(default_out)
    creds = {r["id"]: r for r in _read(default_out, "credentials.csv")}
    claims_by_doctor = defaultdict(list)
    performed = _read(default_out, "rel_performed_by.csv")
    claim_dates = {r["id"]: r["procedure_date"] for r in _read(default_out, "claims.csv")}
    for r in performed:
        claims_by_doctor[r["target_id"]].append(r["source_id"])

    post_rev_found = False
    for cell in ("cred_1", "cred_2", "cred_3"):
        ids = {r["entity_id"] for r in planted if r["cell_id"] == cell}
        cell_creds = [creds[i] for i in ids if i.startswith("CRD_")]
        assert 3 <= len(cell_creds) <= 4
        # one licence number cloned across every identity in the cell
        assert len({c["license_no"] for c in cell_creds}) == 1
        # honest reality: number embeds its issuing country; all clones claim it
        licence = cell_creds[0]["license_no"]
        assert all(c["license_no"].startswith("MC-") for c in cell_creds)
        for c in cell_creds:
            if c["status"] == "revoked":
                post_rev_found = True
                doctor = next(h["source_id"] for h in _read(default_out, "rel_holds.csv")
                              if h["target_id"] == c["id"])
                rev = date.fromisoformat(c["revocation_date"])
                post = [cl for cl in claims_by_doctor[doctor]
                        if date.fromisoformat(claim_dates[cl]) > rev]
                # meaningfully above the honest post-revocation ceiling (29
                # claims at seed 42 full scale) so the volume ramp engages
                assert len(post) >= 30, (doctor, len(post))
    assert post_rev_found


def test_parallel_recycling_creates_impossible_same_day_pairs(tmp_path: Path):
    """The typology-5 fix: at least one recycled group must hold claims in
    two different treatment countries on the SAME day (whole-day travel
    table => genuinely impossible). Recycling gates are boosted because the
    default 2% broker rate rounds to zero recyclers in a 12-broker world."""
    default_out = tmp_path / "boosted"
    assert main(["--seed", "42", "--out", str(default_out),
                 "--config", str(_small_config(tmp_path, boost_recycling=True))]) == 0
    patients = _read(default_out, "patients.csv")
    by_passport = defaultdict(list)
    for p in patients:
        if p["passport_no"]:
            by_passport[p["passport_no"]].append(p["id"])
    located = {r["source_id"]: r["target_id"]
               for r in _read(default_out, "rel_located_at.csv")}
    in_country = {r["source_id"]: r["target_id"]
                  for r in _read(default_out, "rel_in_country.csv")}
    clinic_country = {c: in_country[a] for c, a in located.items()}
    at_clinic = {r["source_id"]: r["target_id"]
                 for r in _read(default_out, "rel_at_clinic.csv")}
    for_patient = defaultdict(list)
    for r in _read(default_out, "rel_for_patient.csv"):
        for_patient[r["target_id"]].append(r["source_id"])
    claim_dates = {r["id"]: r["procedure_date"] for r in _read(default_out, "claims.csv")}

    impossible = 0
    for pp, ids in by_passport.items():
        if len(ids) < 2:
            continue
        seen = defaultdict(set)  # day -> countries
        for pid in ids:
            for c in for_patient[pid]:
                seen[claim_dates[c]].add(clinic_country[at_clinic[c]])
        if any(len(countries) > 1 for countries in seen.values()):
            impossible += 1
    assert impossible >= 1


def test_honest_config_produces_no_planted_rows_or_clones(tmp_path: Path):
    out = tmp_path / "honest"
    assert main(["--seed", "42", "--out", str(out),
                 "--config", str(_small_config(tmp_path, honest=True))]) == 0
    assert _planted(out) == []
    params = list(csv.DictReader(open(out / "ground_truth" / "actor_params.csv",
                                      encoding="utf-8", newline="")))
    assert params == []  # every fraud gate zeroed
    # exactly the configured population: no clones, no invented cell patients
    patients = _read(out, "patients.csv")
    assert len(patients) == SMALL_POPULATIONS["patients"]

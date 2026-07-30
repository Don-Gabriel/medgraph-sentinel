"""PLANTED fraud cells (docs/DATA_GENERATION.md §4) — typologies 1 and 2.

These two typologies are structural enough that emergence is unreliable at
our scale, so they are planted with exact labels. Rules of the layer:

- Cells are built THROUGH THE SAME JOURNEY MODEL as honest claims
  (economy.emit_journey_claims), so amounts, dates, ancillary structure,
  statuses and narratives don't glow statistically.
- Everything runs strictly AFTER the honest + emergent passes, so planting
  is purely additive: base rows keep their bytes (the ADR-006 regression
  check is "old dataset == new dataset minus planted rows").
- Labels (cell membership) go to data/ground_truth/planted.csv
  (entity_id, cell_id, typology) — read by evaluation/ ONLY.
- Planted membership lists CREATED entities only. Honest entities a cell
  touches (e.g. the real clinics a cloned doctor identity practises at)
  are deliberately NOT labeled — an alert pointing only at those would be
  a false positive, and the label must not launder it into a hit.
- Config gates: planted.*.cells: 0 turns the layer off (honest runs).

Visible-but-not-cartoonish: feeder/payout concentration sits near but not
at 1.0, a few journeys use honest brokers, registration dates and volumes
stay inside honest ranges. The cells should be findable by structure, not
by being statistical outliers.
"""
from datetime import date, timedelta

import numpy as np

from .economy import (CARE_DAYS, CLINIC_SUFFIXES, JourneyContext, World,
                      date_in, device_hash, emit_journey_claims, pick)


def plant(cfg, rng: np.random.Generator, fake, w: World) -> list[dict]:
    """Plant all configured cells; returns planted.csv rows
    (entity_id, cell_id, typology)."""
    rows: list[dict] = []
    ctx = JourneyContext.build(cfg, w)
    n_base_brokers = cfg.populations.brokers  # honest-broker picks stay in base range
    for i in range(cfg.planted.ghost_clinics.cells):
        rows += _ghost_cell(cfg, rng, fake, w, ctx, i + 1, n_base_brokers)
    for i in range(cfg.planted.credential_mills.cells):
        rows += _credential_cell(cfg, rng, fake, w, ctx, i + 1, n_base_brokers)
    return rows


# ---------- typology 1: ghost clinic ----------

def _ghost_cell(cfg, rng, fake, w: World, ctx: JourneyContext, n: int,
                n_base_brokers: int) -> list[dict]:
    """Paper clinic + dedicated feeder broker + invented one-journey patients
    + concentrated payout account."""
    p = cfg.planted.ghost_clinics
    cell = f"ghost_{n}"
    treatment_codes = [c.code for c in cfg.countries.treatment]
    origin_codes = [c.code for c in cfg.countries.origin]
    origin_w = np.array([c.outbound_weight for c in cfg.countries.origin])
    origin_w = origin_w / origin_w.sum()
    members: list[str] = []

    country = pick(rng, treatment_codes)
    address_id = w.new_address(country)
    cid = w.seq["CLI"].take()
    # paper footprint: zero beds, young registration, weak accreditation
    registration = date_in(rng, cfg.window.start - timedelta(days=180),
                           cfg.window.start + timedelta(days=60))
    clinic = {
        "id": cid,
        "name": f"{fake.last_name()} {pick(rng, CLINIC_SUFFIXES)}",
        "bed_count": 0,
        "registration_date": registration.isoformat(),
        "accreditation_status": pick(rng, ["none", "provisional"],
                                     np.array([0.7, 0.3])),
        "country_code": country,
        "address_id": address_id,
        "account_ids": [w.new_account("clinic", cid), w.new_account("clinic", cid)],
        "size_weight": 0.0,  # never picked by honest journey routing (post-pass)
    }
    w.clinics.append(clinic)
    w.clinic_doctors[cid] = []
    hub_account, spare_account = clinic["account_ids"]
    members += [cid, hub_account, spare_account]

    # dedicated feeder broker, co-located with the clinic (address co-tenancy)
    bid = w.seq["BRK"].take()
    feeder = {
        "id": bid,
        "name": fake.name(),
        "agency_name": f"{fake.last_name()} Medical Travel",
        "address_id": address_id,
        "account_ids": [w.new_account("broker", bid)],
        "weight": 0.0,
        "country_code": country,
    }
    w.brokers.append(feeder)
    members.append(bid)

    # thin roster: 1-2 doctors, honest-looking active credentials
    doctors = []
    for _ in range(int(rng.integers(p.doctors_min, p.doctors_max + 1))):
        did = w.seq["DOC"].take()
        specialty = pick(rng, list(cfg.category_weights))
        doctor = {"id": did, "full_name": f"Dr. {fake.name()}",
                  "specialty": specialty, "clinic_ids": [cid]}
        w.doctors.append(doctor)
        w.clinic_doctors[cid].append(doctor)
        w.practises.append({"doctor_id": did, "clinic_id": cid,
                            "since": registration.isoformat()})
        issue = date_in(rng, cfg.window.start - timedelta(days=3650),
                        cfg.window.start - timedelta(days=365))
        crid = w.seq["CRD"].take()
        w.credentials.append({
            "id": crid,
            "license_no": f"MC-{country}{rng.integers(10000, 99999)}",
            "issuing_body": _council(w, country),
            "issue_date": issue.isoformat(),
            "status": "active", "revocation_date": "",
            "country_code": country, "doctor_id": did,
        })
        doctors.append(doctor)
        members += [did, crid]

    # invented one-journey patients billed through the normal journey model
    first_day = max(cfg.window.start, registration + timedelta(days=30))
    ins_p = np.array([i["weight"] for i in w.insurers]); ins_p = ins_p / ins_p.sum()
    for _ in range(int(rng.integers(p.patients_min, p.patients_max + 1))):
        home = pick(rng, origin_codes, origin_w)
        pid = w.seq["PAT"].take()
        dev_id = w.seq["DEV"].take()
        w.devices.append({"id": dev_id, "device_hash": device_hash(dev_id),
                          "device_type": pick(rng, ["mobile", "desktop", "tablet"],
                                              np.array([0.55, 0.30, 0.15]))})
        patient = {
            "id": pid, "full_name": fake.name(),
            "dob": date_in(rng, date(1950, 1, 1),
                           date(2005, 12, 31)).isoformat(),
            "gender": pick(rng, ["F", "M", "X"], np.array([0.49, 0.49, 0.02])),
            "passport_no": f"{home}{rng.integers(1000000, 9999999)}",
            "home_country": home, "device_ids": [dev_id],
        }
        w.patients.append(patient)
        members += [pid]

        doctor = pick(rng, doctors)
        category = doctor["specialty"]
        r = rng.random()
        if r < p.feeder_share:
            broker = feeder
        elif r < p.feeder_share + 0.04:  # a stray honest broker: FP noise
            broker = w.brokers[int(rng.integers(0, n_base_brokers))]
        else:
            broker = None
        commission = (round(float(rng.uniform(cfg.brokers.commission_min_pct,
                                              cfg.brokers.commission_max_pct)), 2)
                      if broker else None)
        account_id = (hub_account if rng.random() < p.payout_concentration
                      else spare_account)
        care_lo, care_hi = CARE_DAYS[category]
        claims = emit_journey_claims(
            cfg, rng, w, ctx, patient=patient, clinic=clinic, doctor=doctor,
            procedure=pick(rng, ctx.procs_by_cat[category]), category=category,
            insurer=pick(rng, w.insurers, ins_p), broker=broker,
            commission=commission, account_id=account_id,
            proc_date=date_in(rng, first_day, ctx.last_day),
            days_in_care=int(rng.integers(care_lo, care_hi + 1)),
            device_id=dev_id, over=None, steered=False)
        members += [c["id"] for c in claims]

    return [{"entity_id": e, "cell_id": cell, "typology": "ghost_clinic"}
            for e in members]


# ---------- typology 2: credential laundering ----------

def _credential_cell(cfg, rng, fake, w: World, ctx: JourneyContext, n: int,
                     n_base_brokers: int) -> list[dict]:
    """One licence number cloned across 3-4 doctor identities practising in
    different countries. The number keeps the honest format (it embeds its
    issuing country) and every clone claims the same issuing body/country —
    the tell is the same licence on several doctors, exactly the reality the
    honest data's format-collision guard allows for. Cell 1 additionally has
    a post-revocation biller: the original identity keeps billing well above
    the honest post-revocation ceiling after the licence is revoked."""
    p = cfg.planted.credential_mills
    cell = f"cred_{n}"
    treatment_codes = [c.code for c in cfg.countries.treatment]
    origin_codes = [c.code for c in cfg.countries.origin]
    origin_w = np.array([c.outbound_weight for c in cfg.countries.origin])
    origin_w = origin_w / origin_w.sum()
    ins_p = np.array([i["weight"] for i in w.insurers]); ins_p = ins_p / ins_p.sum()
    members: list[str] = []

    issuing = pick(rng, treatment_codes)
    license_no = f"MC-{issuing}{rng.integers(10000, 99999)}"
    issue = date_in(rng, date(2008, 1, 1),
                    date(2019, 12, 31))
    specialty = pick(rng, list(cfg.category_weights))
    post_revocation = n <= p.post_revocation_cells
    revocation = (date_in(rng, cfg.window.start + timedelta(days=90),
                          cfg.window.start + timedelta(days=150))
                  if post_revocation else None)

    n_ids = int(rng.integers(p.doctors_min, p.doctors_max + 1))
    # the original practises where the licence was issued; clones elsewhere
    other = [t for t in treatment_codes if t != issuing]
    id_countries = [issuing] + [other[int(i)] for i in
                                rng.choice(len(other), size=n_ids - 1, replace=False)]

    for j, country in enumerate(id_countries):
        did = w.seq["DOC"].take()
        doctor = {"id": did, "full_name": f"Dr. {fake.name()}",
                  "specialty": specialty, "clinic_ids": []}
        w.doctors.append(doctor)
        is_original = j == 0
        revoked_here = post_revocation and is_original
        crid = w.seq["CRD"].take()
        w.credentials.append({
            "id": crid,
            "license_no": license_no,             # the cloned number
            "issuing_body": _council(w, issuing),  # same body on every clone
            "issue_date": issue.isoformat(),       # cloned document, same date
            "status": "revoked" if revoked_here else "active",
            "revocation_date": revocation.isoformat() if revoked_here else "",
            "country_code": issuing,               # ISSUED_IN embeds the number's country
            "doctor_id": did,
        })
        members += [did, crid]

        # embed in a real, honest clinic of that country (nothing about the
        # clinic is fraudulent — it stays unlabeled)
        local = [c for c in w.clinics if c["country_code"] == country
                 and c["size_weight"] > 0]
        lw = np.array([c["size_weight"] for c in local]); lw = lw / lw.sum()
        clinic = pick(rng, local, lw)
        w.practises.append({"doctor_id": did, "clinic_id": clinic["id"],
                            "since": date_in(rng, issue, cfg.window.start).isoformat()})

        if revoked_here:
            k = int(rng.integers(p.post_rev_journeys_min, p.post_rev_journeys_max + 1))
            first_day = revocation + timedelta(days=21)  # clear of the 14-day grace
        else:
            k = int(rng.integers(p.journeys_min, p.journeys_max + 1))
            first_day = cfg.window.start
        for _ in range(k):
            home = pick(rng, origin_codes, origin_w)
            pid = w.seq["PAT"].take()
            dev_id = w.seq["DEV"].take()
            w.devices.append({"id": dev_id, "device_hash": device_hash(dev_id),
                              "device_type": pick(rng, ["mobile", "desktop", "tablet"],
                                                  np.array([0.55, 0.30, 0.15]))})
            patient = {
                "id": pid, "full_name": fake.name(),
                "dob": date_in(rng, date(1950, 1, 1),
                               date(2005, 12, 31)).isoformat(),
                "gender": pick(rng, ["F", "M", "X"], np.array([0.49, 0.49, 0.02])),
                "passport_no": f"{home}{rng.integers(1000000, 9999999)}",
                "home_country": home, "device_ids": [dev_id],
            }
            w.patients.append(patient)
            broker = (w.brokers[int(rng.integers(0, n_base_brokers))]
                      if rng.random() < cfg.brokers.arranged_share else None)
            commission = (round(float(rng.uniform(cfg.brokers.commission_min_pct,
                                                  cfg.brokers.commission_max_pct)), 2)
                          if broker else None)
            care_lo, care_hi = CARE_DAYS[specialty]
            claims = emit_journey_claims(
                cfg, rng, w, ctx, patient=patient, clinic=clinic, doctor=doctor,
                procedure=pick(rng, ctx.procs_by_cat[specialty]), category=specialty,
                insurer=pick(rng, w.insurers, ins_p), broker=broker,
                commission=commission,
                account_id=pick(rng, clinic["account_ids"]),
                proc_date=date_in(rng, first_day, ctx.last_day),
                days_in_care=int(rng.integers(care_lo, care_hi + 1)),
                device_id=dev_id, over=None, steered=False)
            members += [c["id"] for c in claims]

    return [{"entity_id": e, "cell_id": cell, "typology": "credential_laundering"}
            for e in members]


def _council(w: World, code: str) -> str:
    name = next(c["name"] for c in w.countries if c["code"] == code)
    return f"Medical Council of {name}"

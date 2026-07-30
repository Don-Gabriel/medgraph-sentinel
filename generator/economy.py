"""The honest economy: actors and journeys (docs/DATA_GENERATION.md §2).

Fraud incentive parameters (generator/fraud.py) plug into journey decisions
here — steering changes which clinic a broker picks, recycling changes which
identity files, overbilling changes how a clinic prices. Fraud is a
distortion of honest decisions, never a separate code path that stamps
labels (§3).
"""
import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from .ids import IdSeq
from .narrative import CODE_PREFIX, PROC_NAMES, build_narrative, simhash64, variant_name

# Real cities per treatment country (entities remain fictional — ADR-015).
CITIES = {
    "IN": ["Chennai", "Mumbai", "New Delhi", "Bengaluru"],
    "TH": ["Bangkok", "Phuket", "Chiang Mai"],
    "TR": ["Istanbul", "Antalya", "Ankara"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah"],
    "SG": ["Singapore"],
}
# Typical inpatient days per category: bounds for narrative + date spacing.
CARE_DAYS = {
    "cardiac": (4, 14), "oncology": (5, 14), "orthopaedic": (3, 10),
    "fertility": (1, 4), "cosmetic": (1, 5), "dental": (1, 3),
}
CLINIC_SUFFIXES = ["Medical Centre", "Speciality Hospital", "Care Clinic", "Institute", "Hospital"]
INSURER_SUFFIXES = ["Assurance", "Insurance Group", "Mutual Health", "Health Cover"]


@dataclass
class World:
    countries: list = field(default_factory=list)
    procedures: list = field(default_factory=list)
    insurers: list = field(default_factory=list)
    addresses: list = field(default_factory=list)
    accounts: list = field(default_factory=list)
    clinics: list = field(default_factory=list)
    doctors: list = field(default_factory=list)
    credentials: list = field(default_factory=list)
    brokers: list = field(default_factory=list)
    devices: list = field(default_factory=list)
    patients: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    transfers: list = field(default_factory=list)
    practises: list = field(default_factory=list)
    owns_stake: list = field(default_factory=list)
    used_device: dict = field(default_factory=dict)  # (patient_id, device_id) -> [min, max]
    # metadata only (no CSV output): recycled-clone events recorded by
    # build_journeys, consumed by fraud.parallel_recycling (typology-5 fix)
    recycled_clones: list = field(default_factory=list)
    # scenario-overlay generic edges: rel file stem -> extra rows (appended
    # by generator/scenario.py, written by writer.py)
    extra_rels: dict = field(default_factory=dict)

    def __post_init__(self):
        self.seq = {
            p: IdSeq(p)
            for p in ("PAT", "DOC", "CLI", "BRK", "CLM", "CRD", "ACC", "DEV", "ADR", "PRC", "INS")
        }
        # Scenario actors draw from a reserved ID range (INTERFACES §3) so
        # they can never collide with base entities: base populations stay
        # far below 900000 (claims below 9000000).
        self.scn_seq = {
            p: IdSeq(p, start=9000001 if p == "CLM" else 900001)
            for p in ("PAT", "DOC", "CLI", "BRK", "CLM", "CRD", "ACC", "DEV", "ADR", "PRC", "INS")
        }


# ---------- small deterministic helpers ----------

def zipf_weights(rng: np.random.Generator, n: int, a: float) -> np.ndarray:
    """Skewed size weights: few large actors, long tail; rank order shuffled."""
    ranks = rng.permutation(n) + 1
    w = 1.0 / ranks**a
    return w / w.sum()

def pick(rng, items, p=None):
    return items[int(rng.choice(len(items), p=p))]

def date_in(rng, start: date, end: date) -> date:
    return start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))

def money(x: float) -> float:
    return round(float(x), 2)

def device_hash(dev_id: str) -> str:
    return hashlib.md5(f"medgraph-device-{dev_id}".encode()).hexdigest()[:16]


# ---------- static populations ----------

def build_static(cfg, rng, fake, w: World) -> None:
    for c in cfg.countries.treatment:
        w.countries.append(
            {"code": c.code, "name": c.name, "role": "treatment",
             "cost_multiplier": c.cost_multiplier}
        )
    for c in cfg.countries.origin:
        w.countries.append(
            {"code": c.code, "name": c.name, "role": "origin", "cost_multiplier": 1.0}
        )
    cname = {c["code"]: c["name"] for c in w.countries}

    for cat, spec in cfg.procedure_categories.items():
        bases = PROC_NAMES[cat]
        for i in range(spec.count):
            w.procedures.append({
                "id": w.seq["PRC"].take(),
                "code": f"{CODE_PREFIX[cat]}-{i + 1:03d}",
                "category": cat,
                "name": variant_name(bases[i % len(bases)], i // len(bases)),
                "base_cost_usd": money(rng.lognormal(spec.cost_mu, spec.cost_sigma)),
            })

    origin_codes = [c.code for c in cfg.countries.origin]
    origin_w = np.array([c.outbound_weight for c in cfg.countries.origin])
    origin_w = origin_w / origin_w.sum()
    ins_weights = zipf_weights(rng, cfg.populations.insurers, 1.2)
    for i in range(cfg.populations.insurers):
        w.insurers.append({
            "id": w.seq["INS"].take(),
            "name": f"{fake.last_name()} {pick(rng, INSURER_SUFFIXES)}",
            "country_code": pick(rng, origin_codes, origin_w),
            "weight": float(ins_weights[i]),
        })

    treatment_codes = [c.code for c in cfg.countries.treatment]
    # A treatment country's clinic capacity follows its total corridor pull.
    pull = np.array([sum(row[t] for row in cfg.gravity.values()) for t in treatment_codes])
    pull = pull / pull.sum()

    def new_address(country_code: str) -> str:
        adr = {
            "id": w.seq["ADR"].take(),
            "street": fake.street_address(),
            "city": pick(rng, CITIES[country_code]) if country_code in CITIES else fake.city(),
            "postcode": fake.postcode(),
            "country_code": country_code,
        }
        w.addresses.append(adr)
        return adr["id"]

    def new_account(owner_kind: str | None, owner_id: str | None) -> str:
        acc = {
            "id": w.seq["ACC"].take(),
            "account_ref": f"MG{rng.integers(10**15, 10**16 - 1)}",
            "bank_name": f"{fake.last_name()} Bank",
            "opened_date": date_in(rng, date(2015, 1, 1), cfg.window.start).isoformat(),
            "owner_kind": owner_kind,
            "owner_id": owner_id,
        }
        w.accounts.append(acc)
        return acc["id"]

    w.new_address = new_address  # reused by journeys/fraud
    w.new_account = new_account

    shared_pool: dict[str, list[str]] = {t: [] for t in treatment_codes}
    clinic_sizes = zipf_weights(rng, cfg.populations.clinics, cfg.clinics.zipf_a)
    acc_status = list(cfg.clinics.accreditation.items())
    acc_p = np.array([v for _, v in acc_status]); acc_p = acc_p / acc_p.sum()
    for i in range(cfg.populations.clinics):
        country = pick(rng, treatment_codes, pull)
        if shared_pool[country] and rng.random() < cfg.clinics.shared_address_rate:
            address_id = pick(rng, shared_pool[country])
        else:
            address_id = new_address(country)
            shared_pool[country].append(address_id)
        cid = w.seq["CLI"].take()
        w.clinics.append({
            "id": cid,
            "name": f"{fake.last_name()} {pick(rng, CLINIC_SUFFIXES)}",
            "bed_count": 0 if rng.random() < cfg.clinics.bed_zero_rate
            else int(rng.lognormal(3.5, 0.8)) + 5,
            "registration_date": date_in(rng, date(2010, 1, 1), cfg.window.start).isoformat(),
            "accreditation_status": acc_status[int(rng.choice(len(acc_status), p=acc_p))][0],
            "country_code": country,
            "address_id": address_id,
            "account_ids": [
                new_account("clinic", cid)
                for _ in range(int(rng.integers(cfg.clinics.accounts_min,
                                                cfg.clinics.accounts_max + 1)))
            ],
            "size_weight": float(clinic_sizes[i]),
        })

    categories = list(cfg.category_weights)
    cat_p = np.array([cfg.category_weights[c] for c in categories]); cat_p = cat_p / cat_p.sum()
    clinic_w = np.array([c["size_weight"] for c in w.clinics]); clinic_w = clinic_w / clinic_w.sum()
    by_country_clinics: dict[str, list[dict]] = {}
    for c in w.clinics:
        by_country_clinics.setdefault(c["country_code"], []).append(c)
    w.by_country_clinics = by_country_clinics
    w.clinic_doctors = {c["id"]: [] for c in w.clinics}

    for _ in range(cfg.populations.doctors):
        did = w.seq["DOC"].take()
        specialty = pick(rng, categories, cat_p)
        primary = pick(rng, w.clinics, clinic_w)
        clinics = [primary]
        for _ in range(int(rng.integers(cfg.doctors.affiliations_min,
                                        cfg.doctors.affiliations_max + 1)) - 1):
            extra = pick(rng, by_country_clinics[primary["country_code"]])
            if extra["id"] not in [c["id"] for c in clinics]:
                clinics.append(extra)
        doctor = {"id": did, "full_name": f"Dr. {fake.name()}", "specialty": specialty,
                  "clinic_ids": [c["id"] for c in clinics]}
        w.doctors.append(doctor)
        for c in clinics:
            w.clinic_doctors[c["id"]].append(doctor)
            w.practises.append({
                "doctor_id": did, "clinic_id": c["id"],
                "since": date_in(rng, date(2012, 1, 1), cfg.window.start).isoformat(),
            })
        n_creds = int(rng.integers(cfg.doctors.credentials_min, cfg.doctors.credentials_max + 1))
        cred_countries = [primary["country_code"]]
        if n_creds > 1:
            cred_countries.append(pick(rng, treatment_codes))
        for cc in cred_countries[:n_creds]:
            issue = date_in(rng, date(2005, 1, 1), date(2024, 12, 31))
            revoked = rng.random() < cfg.doctors.revoked_rate
            w.credentials.append({
                "id": w.seq["CRD"].take(),
                "license_no": f"MC-{cc}{rng.integers(10000, 99999)}",
                "issuing_body": f"Medical Council of {cname[cc]}",
                "issue_date": issue.isoformat(),
                "status": "revoked" if revoked else "active",
                "revocation_date": (
                    date_in(rng, issue + timedelta(days=365), cfg.window.end).isoformat()
                    if revoked else ""
                ),
                "country_code": cc,
                "doctor_id": did,
            })

    broker_weights = zipf_weights(rng, cfg.populations.brokers, cfg.brokers.zipf_a)
    for i in range(cfg.populations.brokers):
        country = pick(rng, treatment_codes, pull)
        clinics_here = by_country_clinics.get(country, [])
        if clinics_here and rng.random() < cfg.brokers.colocate_with_clinic_rate:
            address_id = pick(rng, clinics_here)["address_id"]
        else:
            address_id = new_address(country)
        bid = w.seq["BRK"].take()
        w.brokers.append({
            "id": bid,
            "name": fake.name(),
            "agency_name": f"{fake.last_name()} Medical Travel",
            "address_id": address_id,
            "account_ids": [
                new_account("broker", bid)
                for _ in range(int(rng.integers(cfg.brokers.accounts_min,
                                                cfg.brokers.accounts_max + 1)))
            ],
            "weight": float(broker_weights[i]),
            "country_code": country,
        })

    # Honest declared stakes: some brokers legitimately invest in a local
    # clinic (hospital groups with in-house facilitation). This is the FP
    # noise that keeps OWNS_STAKE_IN from being a fraud label (ADR-023).
    for broker in w.brokers:
        if rng.random() < cfg.brokers.stake_rate:
            local = by_country_clinics.get(broker["country_code"], [])
            if not local:
                continue
            lw = np.array([c["size_weight"] for c in local]); lw = lw / lw.sum()
            clinic = pick(rng, local, lw)
            w.owns_stake.append({
                "broker_id": broker["id"],
                "clinic_id": clinic["id"],
                "pct": round(float(rng.uniform(cfg.brokers.stake_min_pct,
                                               cfg.brokers.stake_max_pct)), 1),
            })

    family_devices: dict[str, list[str]] = {}
    for _ in range(cfg.populations.patients):
        home = pick(rng, origin_codes, origin_w)
        pid = w.seq["PAT"].take()
        devices = []
        if family_devices.get(home) and rng.random() < cfg.patients.family_device_share:
            devices.append(pick(rng, family_devices[home]))
        n_devices = 1 + (1 if rng.random() < cfg.patients.second_device_rate else 0)
        while len(devices) < n_devices:
            dev_id = w.seq["DEV"].take()
            w.devices.append({
                "id": dev_id,
                "device_hash": device_hash(dev_id),
                "device_type": pick(rng, ["mobile", "desktop", "tablet"],
                                    np.array([0.55, 0.30, 0.15])),
            })
            devices.append(dev_id)
            family_devices.setdefault(home, []).append(dev_id)
        w.patients.append({
            "id": pid,
            "full_name": fake.name(),
            "dob": date_in(rng, date(1950, 1, 1), date(2005, 12, 31)).isoformat(),
            "gender": pick(rng, ["F", "M", "X"], np.array([0.49, 0.49, 0.02])),
            "passport_no": "" if rng.random() < cfg.patients.passport_null_rate
            else f"{home}{rng.integers(1000000, 9999999)}",
            "home_country": home,
            "device_ids": devices,
        })


# ---------- journeys -> claims ----------

@dataclass
class JourneyContext:
    """Derived lookup tables the claim emitter needs. Built once per pass
    (base journeys, planted cells, scenario overlays) — pure derivation from
    cfg + world, no RNG draws."""
    procs_by_cat: dict
    status_names: list
    status_p: np.ndarray
    cmult: dict
    last_day: date

    @classmethod
    def build(cls, cfg, w: "World") -> "JourneyContext":
        procs_by_cat: dict[str, list[dict]] = {}
        for p in w.procedures:
            procs_by_cat.setdefault(p["category"], []).append(p)
        status_names = list(cfg.claims.status_weights)
        status_p = np.array([cfg.claims.status_weights[s] for s in status_names])
        status_p = status_p / status_p.sum()
        cmult = {c["code"]: c["cost_multiplier"] for c in w.countries}
        # last treatment window day leaving room for submission lag + transfers
        last_day = cfg.window.end - timedelta(days=cfg.claims.submission_lag_max_days + 20)
        return cls(procs_by_cat, status_names, status_p, cmult, last_day)


def emit_journey_claims(cfg, rng, w: World, ctx: JourneyContext, *, patient: dict,
                        clinic: dict, doctor: dict, procedure: dict, category: str,
                        insurer: dict, broker: dict | None, commission,
                        account_id: str, proc_date: date, days_in_care: int,
                        device_id: str, over: dict | None, steered: bool,
                        claim_seq=None) -> list[dict]:
    """Emit one journey's 1-3 claims (main + ancillary) exactly as the base
    journey model does — planted cells and scenario overlays route through
    this same function so their claims don't glow statistically
    (DATA_GENERATION §4). Extracted verbatim from build_journeys; the RNG
    draw order in here is part of the byte-determinism contract (ADR-006).
    `claim_seq` overrides the ID source (scenario-reserved range)."""
    seq = claim_seq or w.seq["CLM"]
    emitted = []
    n_claims = int(rng.integers(cfg.claims.claims_per_journey_min,
                                cfg.claims.claims_per_journey_max + 1))
    main_amount = None
    for k in range(n_claims):
        if k == 0:
            amount = _price(rng, cfg, procedure["base_cost_usd"],
                            ctx.cmult[clinic["country_code"]])
            line_items = int(rng.integers(3, 13))
            claim_proc = procedure
            claim_date = proc_date
        else:
            claim_proc = pick(rng, ctx.procs_by_cat[category])
            amount = money(main_amount * rng.uniform(cfg.claims.ancillary_amount_min,
                                                     cfg.claims.ancillary_amount_max))
            line_items = int(rng.integers(1, 4))
            claim_date = proc_date + timedelta(days=int(rng.integers(0, 6)))
        if over and rng.random() < over["claim_share"]:
            amount = money(amount * over["factor"])
            line_items += int(rng.integers(1, 5))
        if k == 0:
            main_amount = amount
        submission = claim_date + timedelta(
            days=int(rng.integers(cfg.claims.submission_lag_min_days,
                                  cfg.claims.submission_lag_max_days + 1))
        )
        narrative = build_narrative(rng, claim_proc["name"], clinic["name"],
                                    days_in_care if k == 0 else int(rng.integers(0, 3)))
        claim = {
            "id": seq.take(),
            "amount_usd": amount,
            "procedure_date": claim_date.isoformat(),
            "submission_date": submission.isoformat(),
            "status": pick(rng, ctx.status_names, ctx.status_p),
            "line_item_count": line_items,
            "narrative_fingerprint": simhash64(narrative),
            "patient_id": patient["id"],
            "clinic_id": clinic["id"],
            "doctor_id": doctor["id"],
            "procedure_id": claim_proc["id"],
            "insurer_id": insurer["id"],
            "broker_id": broker["id"] if broker else "",
            "commission_pct": commission if broker else "",
            "account_id": account_id,
            "steered_by": broker["id"] if steered else "",
        }
        w.claims.append(claim)
        emitted.append(claim)
        _track_device(w, patient["id"], device_id, claim_date)
        if broker:
            w.transfers.append({
                "src": account_id,
                "dst": pick(rng, broker["account_ids"]),
                "amount_usd": money(amount * commission / 100.0),
                "date": (submission + timedelta(days=cfg.transfers.commission_lag_days)
                         ).isoformat(),
            })
    return emitted


def _doctor_for(rng, w: World, clinic: dict, category: str) -> dict:
    roster = w.clinic_doctors[clinic["id"]]
    matching = [d for d in roster if d["specialty"] == category]
    if matching:
        return pick(rng, matching)
    if roster:
        return pick(rng, roster)
    # tiny clinic with no roster: affiliate a doctor on the fly
    doctor = pick(rng, w.doctors)
    w.clinic_doctors[clinic["id"]].append(doctor)
    w.practises.append({"doctor_id": doctor["id"], "clinic_id": clinic["id"],
                        "since": "2024-01-01"})
    return doctor


def _price(rng, cfg, base_cost: float, multiplier: float) -> float:
    return money(base_cost * multiplier * rng.lognormal(0.0, cfg.claims.price_noise_sigma))


def _track_device(w: World, patient_id: str, device_id: str, d: date) -> None:
    key = (patient_id, device_id)
    if key not in w.used_device:
        w.used_device[key] = [d, d]
    else:
        lo, hi = w.used_device[key]
        w.used_device[key] = [min(lo, d), max(hi, d)]


def build_journeys(cfg, rng, fake, w: World, fraud_params) -> None:
    treatment_codes = [c.code for c in cfg.countries.treatment]
    categories = list(cfg.category_weights)
    cat_p = np.array([cfg.category_weights[c] for c in categories]); cat_p = cat_p / cat_p.sum()
    broker_p = np.array([b["weight"] for b in w.brokers]); broker_p = broker_p / broker_p.sum()
    ins_p = np.array([i["weight"] for i in w.insurers]); ins_p = ins_p / ins_p.sum()
    clinics_by_id = {c["id"]: c for c in w.clinics}
    ctx = JourneyContext.build(cfg, w)
    last_day = ctx.last_day
    recycle_pool: dict[str, list[tuple[str, str]]] = {}  # broker -> [(patient_id, insurer_id)]

    journeys = list(range(len(w.patients)))
    extra = int(len(w.patients) * cfg.patients.return_rate)
    journeys += [int(i) for i in rng.choice(len(w.patients), size=extra, replace=False)]

    for patient_idx in journeys:
        patient = w.patients[patient_idx]
        category = pick(rng, categories, cat_p)
        grav = cfg.gravity[patient["home_country"]]
        gp = np.array([grav[t] for t in treatment_codes]); gp = gp / gp.sum()
        country = pick(rng, treatment_codes, gp)

        broker = None
        if rng.random() < cfg.brokers.arranged_share:
            broker = pick(rng, w.brokers, broker_p)

        steer = fraud_params.steering.get(broker["id"]) if broker else None
        steered = bool(steer and rng.random() < steer["greed"])
        if steered:
            clinic = clinics_by_id[pick(rng, steer["partners"])]
        else:
            local = w.by_country_clinics[country]
            lw = np.array([c["size_weight"] for c in local]); lw = lw / lw.sum()
            clinic = pick(rng, local, lw)

        insurer_exclude = None
        recycler = fraud_params.recycling.get(broker["id"]) if broker else None
        if recycler and recycle_pool.get(broker["id"]) and rng.random() < recycler["reuse"]:
            src_pid, src_ins = pick(rng, recycle_pool[broker["id"]])
            src = next(p for p in w.patients if p["id"] == src_pid)
            clone_id = w.seq["PAT"].take()
            clone = {
                "id": clone_id,
                "full_name": fake.name(),  # new alias, same identity artifacts
                "dob": src["dob"],
                "gender": src["gender"],
                "passport_no": src["passport_no"],
                "home_country": src["home_country"],
                "device_ids": [pick(rng, src["device_ids"])],
            }
            w.patients.append(clone)
            # metadata for fraud.parallel_recycling (typology-5 fix): which
            # clone belongs to which broker. Recording only — no RNG draws.
            w.recycled_clones.append({"clone_id": clone_id, "source_id": src_pid,
                                      "broker_id": broker["id"]})
            patient = clone
            insurer_exclude = src_ins

        doctor = _doctor_for(rng, w, clinic, category)
        procedure = pick(rng, ctx.procs_by_cat[category])
        insurer = pick(rng, w.insurers, ins_p)
        if insurer_exclude is not None:
            while insurer["id"] == insurer_exclude:
                insurer = pick(rng, w.insurers, ins_p)

        over = fraud_params.overbilling.get(clinic["id"])
        care_lo, care_hi = CARE_DAYS[category]
        days_in_care = int(rng.integers(care_lo, care_hi + 1))
        proc_date = date_in(rng, cfg.window.start, last_day)
        device_id = pick(rng, patient["device_ids"])
        account_id = pick(rng, clinic["account_ids"])
        commission = (
            money(rng.uniform(cfg.brokers.commission_min_pct, cfg.brokers.commission_max_pct))
            if broker else None
        )

        emit_journey_claims(cfg, rng, w, ctx, patient=patient, clinic=clinic,
                            doctor=doctor, procedure=procedure, category=category,
                            insurer=insurer, broker=broker, commission=commission,
                            account_id=account_id, proc_date=proc_date,
                            days_in_care=days_in_care, device_id=device_id,
                            over=over, steered=steered)
        if broker:
            recycle_pool.setdefault(broker["id"], []).append((patient["id"], insurer["id"]))

    _emit_dormant_device_edges(cfg, rng, w)


def _emit_dormant_device_edges(cfg, rng, w: World) -> None:
    """Every owned device gets a USED_DEVICE edge (fix — ADR-022).

    Journeys only track the device actually used for a claim, which left
    second devices as orphan nodes and erased the family-sharing signal from
    the edge table. Devices not used on a journey get a plausible dormant
    window: portal registration/browsing in the weeks before the patient's
    first treatment.
    """
    first_claim: dict[str, date] = {}
    for (pid, _dev), (lo, _hi) in w.used_device.items():
        if pid not in first_claim or lo < first_claim[pid]:
            first_claim[pid] = lo
    for patient in w.patients:
        ref = first_claim.get(patient["id"], cfg.window.start)
        for dev in patient["device_ids"]:
            if (patient["id"], dev) in w.used_device:
                continue
            start = ref - timedelta(days=int(rng.integers(14, 91)))
            end = min(start + timedelta(days=int(rng.integers(1, 40))), ref)
            w.used_device[(patient["id"], dev)] = [start, end]

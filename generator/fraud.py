"""EMERGENT fraud layer (docs/DATA_GENERATION.md §3).

Assigns incentive *parameters* to a small fraction of actors before journeys
run; the economy consults them during normal decision-making. Nothing here
stamps a fraud label on data — ground truth is the parameter record itself,
written to data/ground_truth/ and read by evaluation ONLY.

Planted cells (§4) live in generator/plant.py; scenario overlays (§5 tooling,
INTERFACES §3) in generator/scenario.py. Both run strictly AFTER the emergent
passes here so the honest+emergent base keeps its bytes (ADR-006).
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from .economy import World, money, pick


@dataclass
class FraudParams:
    overbilling: dict = field(default_factory=dict)   # clinic_id -> {factor, claim_share}
    steering: dict = field(default_factory=dict)      # broker_id -> {greed, partners, side_pct, layered, ...}
    recycling: dict = field(default_factory=dict)     # broker_id -> {reuse}
    ground_truth: list = field(default_factory=list)  # rows for actor_params.csv


def assign(cfg, rng: np.random.Generator, w: World) -> FraudParams:
    fp = FraudParams()
    f = cfg.fraud

    for clinic in w.clinics:
        if rng.random() < f.overbilling.clinic_rate:
            params = {
                "factor": round(float(rng.uniform(f.overbilling.factor_min,
                                                  f.overbilling.factor_max)), 3),
                "claim_share": round(float(rng.uniform(f.overbilling.claim_share_min,
                                                       f.overbilling.claim_share_max)), 3),
            }
            fp.overbilling[clinic["id"]] = params
            for k, v in params.items():
                fp.ground_truth.append(
                    {"actor_id": clinic["id"], "param_name": f"overbilling_{k}", "value": v}
                )

    clinic_ids = [c["id"] for c in w.clinics]
    stake_pairs = {(s["broker_id"], s["clinic_id"]) for s in w.owns_stake}
    # Overbilling clinics are likelier kickback partners — parameter
    # interaction is what makes rings *emerge* rather than being placed.
    partner_w = np.array(
        [c["size_weight"] * (f.steering.partner_overbilling_bias
                             if c["id"] in fp.overbilling else 1.0)
         for c in w.clinics]
    )
    partner_w = partner_w / partner_w.sum()

    for broker in w.brokers:
        if rng.random() < f.steering.broker_rate:
            n = int(rng.integers(f.steering.partners_min, f.steering.partners_max + 1))
            partners = list(dict.fromkeys(
                clinic_ids[int(i)] for i in rng.choice(len(clinic_ids), size=n, p=partner_w)
            ))
            params = {
                "greed": round(float(rng.uniform(f.steering.greed_min, f.steering.greed_max)), 3),
                "partners": partners,
                "side_pct": round(float(rng.uniform(f.steering.side_commission_min_pct,
                                                    f.steering.side_commission_max_pct)), 2),
                "layered": bool(rng.random() < f.shell_layering.pair_rate),
                "shells": int(rng.integers(f.shell_layering.shells_min,
                                           f.shell_layering.shells_max + 1)),
                "attrition_pct": round(float(rng.uniform(f.shell_layering.attrition_min_pct,
                                                         f.shell_layering.attrition_max_pct)), 2),
            }
            fp.steering[broker["id"]] = params
            fp.ground_truth.append({"actor_id": broker["id"], "param_name": "steering_greed",
                                    "value": params["greed"]})
            fp.ground_truth.append({"actor_id": broker["id"], "param_name": "steering_partners",
                                    "value": "|".join(partners)})
            fp.ground_truth.append({"actor_id": broker["id"], "param_name": "side_commission_pct",
                                    "value": params["side_pct"]})
            if params["layered"]:
                fp.ground_truth.append({"actor_id": broker["id"],
                                        "param_name": "shell_layering", "value": params["shells"]})
            # Hidden equity in partner clinics closes the kickback loop
            # (typology 3's ownership leg). Honest declared stakes generated
            # in economy.build_static keep the edge from being a label.
            for clinic_id in partners:
                if rng.random() >= f.steering.stake_prob:
                    continue
                if (broker["id"], clinic_id) in stake_pairs:
                    continue  # already a declared holder; no second edge
                pct = round(float(rng.uniform(f.steering.stake_min_pct,
                                              f.steering.stake_max_pct)), 1)
                w.owns_stake.append({"broker_id": broker["id"], "clinic_id": clinic_id,
                                     "pct": pct})
                stake_pairs.add((broker["id"], clinic_id))
                fp.ground_truth.append({"actor_id": broker["id"], "param_name": "hidden_stake",
                                        "value": f"{clinic_id}:{pct}"})
        if rng.random() < f.identity_recycling.broker_rate:
            reuse = round(float(rng.uniform(f.identity_recycling.reuse_min,
                                            f.identity_recycling.reuse_max)), 3)
            fp.recycling[broker["id"]] = {"reuse": reuse}
            fp.ground_truth.append({"actor_id": broker["id"],
                                    "param_name": "identity_recycling", "value": reuse})
    return fp


def side_payments(cfg, rng: np.random.Generator, w: World, fp: FraudParams,
                  claims: list | None = None) -> None:
    """Materialize kickbacks for steered claims: direct or shell-layered
    transfers, with a fraction cycling back to the clinic (typology 6's
    emergent substrate). `claims` restricts the pass to a subset (scenario
    overlays run it over their own claims only); default is the whole world."""
    f = cfg.fraud.shell_layering
    brokers_by_id = {b["id"]: b for b in w.brokers}
    clinics_by_id = {c["id"]: c for c in w.clinics}

    for claim in (claims if claims is not None else w.claims):
        broker_id = claim["steered_by"]
        if not broker_id:
            continue
        params = fp.steering[broker_id]
        clinic = clinics_by_id[claim["clinic_id"]]
        broker = brokers_by_id[broker_id]
        src = claim["account_id"]
        dst = pick(rng, broker["account_ids"])
        amount = money(claim["amount_usd"] * params["side_pct"] / 100.0)
        if amount < 1:
            continue
        pay_date = date.fromisoformat(claim["submission_date"]) + timedelta(days=3)

        if not params["layered"]:
            w.transfers.append({"src": src, "dst": dst, "amount_usd": amount,
                                "date": pay_date.isoformat()})
            continue

        hop_from = src
        remaining = amount
        for _ in range(params["shells"]):
            shell = w.new_account(None, None)  # no OWNED_BY edge: a shell, by definition
            w.transfers.append({"src": hop_from, "dst": shell, "amount_usd": money(remaining),
                                "date": pay_date.isoformat()})
            remaining = remaining * (1 - params["attrition_pct"] / 100.0)
            pay_date += timedelta(days=int(rng.integers(2, 9)))
            hop_from = shell
        w.transfers.append({"src": hop_from, "dst": dst, "amount_usd": money(remaining),
                            "date": pay_date.isoformat()})

        if rng.random() < f.recycle_prob:
            back = money(remaining * float(rng.uniform(0.3, 0.6)))
            if back >= 1:
                shell = w.new_account(None, None)
                d1 = pay_date + timedelta(days=int(rng.integers(3, 12)))
                d2 = d1 + timedelta(days=int(rng.integers(2, 9)))
                w.transfers.append({"src": dst, "dst": shell, "amount_usd": back,
                                    "date": d1.isoformat()})
                w.transfers.append({"src": shell, "dst": pick(rng, clinic["account_ids"]),
                                    "amount_usd": money(back * 0.95), "date": d2.isoformat()})


def parallel_recycling(cfg, rng: np.random.Generator, fake, w: World,
                       fp: FraudParams) -> None:
    """Typology-5 fix (2026-07-31 session): a deterministic fraction of
    recycled-clone events also get a PARALLEL-billed journey — a further
    clone of the same identity treated the SAME DAY in a DIFFERENT treatment
    country. Rationale: colluding clinics bill one recruited identity
    simultaneously in two corridors; sequential reuse alone never violates
    the whole-day travel table (measured: tightest cross-country gap 6 days
    at seed 42), so without this the impossible-travel core is untestable.

    Runs strictly AFTER build_journeys + side_payments so it is purely
    additive: base rows keep their bytes; this pass only appends new
    patients/devices/claims/transfers. Claims go through the same journey
    model (economy.emit_journey_claims). No labels are written — ground
    truth stays derived (actor_params identity_recycling rows + passport
    sharing + claim dates), exactly like sequential recycling.
    """
    from .economy import (CARE_DAYS, JourneyContext, _doctor_for, date_in,
                          emit_journey_claims)

    share = cfg.fraud.identity_recycling.parallel_share
    if share <= 0 or not w.recycled_clones:
        return
    ctx = JourneyContext.build(cfg, w)
    treatment_codes = [c.code for c in cfg.countries.treatment]
    clinics_by_country = {}
    for c in w.clinics:
        clinics_by_country.setdefault(c["country_code"], []).append(c)
    brokers_by_id = {b["id"]: b for b in w.brokers}
    patients_by_id = {p["id"]: p for p in w.patients}
    claims_by_patient: dict[str, list[dict]] = {}
    for c in w.claims:
        claims_by_patient.setdefault(c["patient_id"], []).append(c)
    categories = list(cfg.category_weights)
    cat_p = np.array([cfg.category_weights[c] for c in categories])
    cat_p = cat_p / cat_p.sum()
    ins_p = np.array([i["weight"] for i in w.insurers])
    ins_p = ins_p / ins_p.sum()

    for event in list(w.recycled_clones):  # snapshot: we append patients below
        if rng.random() >= share:
            continue
        anchor_claims = claims_by_patient.get(event["clone_id"])
        if not anchor_claims:
            continue  # clone journey emitted nothing (cannot happen today)
        anchor = anchor_claims[0]  # the journey's main claim
        anchor_clinic = next(c for c in w.clinics if c["id"] == anchor["clinic_id"])
        other_codes = [t for t in treatment_codes
                       if t != anchor_clinic["country_code"] and clinics_by_country.get(t)]
        if not other_codes:
            continue
        country = pick(rng, other_codes)
        local = clinics_by_country[country]
        lw = np.array([c["size_weight"] for c in local]); lw = lw / lw.sum()
        clinic = pick(rng, local, lw)

        src = patients_by_id[event["clone_id"]]
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

        category = pick(rng, categories, cat_p)
        doctor = _doctor_for(rng, w, clinic, category)
        procedure = pick(rng, ctx.procs_by_cat[category])
        insurer = pick(rng, w.insurers, ins_p)
        while insurer["id"] == anchor["insurer_id"]:  # parallel bill hits another insurer
            insurer = pick(rng, w.insurers, ins_p)
        broker = brokers_by_id[event["broker_id"]]
        commission = money(rng.uniform(cfg.brokers.commission_min_pct,
                                       cfg.brokers.commission_max_pct))
        care_lo, care_hi = CARE_DAYS[category]
        days_in_care = int(rng.integers(care_lo, care_hi + 1))
        proc_date = date.fromisoformat(anchor["procedure_date"])  # SAME DAY - the core
        emit_journey_claims(cfg, rng, w, ctx, patient=clone, clinic=clinic,
                            doctor=doctor, procedure=procedure, category=category,
                            insurer=insurer, broker=broker, commission=commission,
                            account_id=pick(rng, clinic["account_ids"]),
                            proc_date=proc_date, days_in_care=days_in_care,
                            device_id=clone["device_ids"][0],
                            over=fp.overbilling.get(clinic["id"]), steered=False)

"""EMERGENT fraud layer (docs/DATA_GENERATION.md §3).

Assigns incentive *parameters* to a small fraction of actors before journeys
run; the economy consults them during normal decision-making. Nothing here
stamps a fraud label on data — ground truth is the parameter record itself,
written to data/ground_truth/ and read by evaluation ONLY.

Planted cells (§4) and held-out scenario overlays (§5) are NOT implemented
yet: planted is an M3 item; held-out tooling waits on the OQ #12 attestation.
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
        if rng.random() < f.identity_recycling.broker_rate:
            reuse = round(float(rng.uniform(f.identity_recycling.reuse_min,
                                            f.identity_recycling.reuse_max)), 3)
            fp.recycling[broker["id"]] = {"reuse": reuse}
            fp.ground_truth.append({"actor_id": broker["id"],
                                    "param_name": "identity_recycling", "value": reuse})
    return fp


def side_payments(cfg, rng: np.random.Generator, w: World, fp: FraudParams) -> None:
    """Materialize kickbacks for steered claims: direct or shell-layered
    transfers, with a fraction cycling back to the clinic (typology 6's
    emergent substrate)."""
    f = cfg.fraud.shell_layering
    brokers_by_id = {b["id"]: b for b in w.brokers}
    clinics_by_id = {c["id"]: c for c in w.clinics}

    for claim in w.claims:
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

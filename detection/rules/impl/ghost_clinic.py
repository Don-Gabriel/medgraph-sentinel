"""Typology 1 — ghost clinic (DETECTION_SPEC §1).

A clinic that exists on paper: high claim volume against no physical
footprint, one feeder broker, one payout account, a skeleton doctor roster,
patients who appear once and vanish. Every feature alone has an honest
explanation (that is the FP-mode list in the spec), so the score is a
weighted sum and a "strong hits" count — fewer than min_strong_features
strong features caps the score below medium, mechanically.

Louvain community membership is attached as ring *context* only (the ghost
cell clusters with its feeder broker and hub account); it gates nothing.
"""
from datetime import date

from .common import community_sizes, louvain_communities, scale

# Feature extraction is one aggregate pass per evidence family; candidates
# are gated by min_claims first so the follow-up queries stay tiny.
Q_BASE = """
MATCH (cl:Clinic)<-[:AT_CLINIC]-(c:Claim)
WITH cl, count(c) AS claims
WHERE claims >= $min_claims
RETURN cl.id AS clinic_id, cl.name AS name, cl.bed_count AS beds,
       toString(cl.registration_date) AS registered, claims
"""
Q_TOP_BROKER = """
MATCH (cl:Clinic)<-[:AT_CLINIC]-(c:Claim)-[:ARRANGED_BY]->(b:Broker)
WHERE cl.id IN $ids
WITH cl, b, count(c) AS n
ORDER BY n DESC, b.id
WITH cl, collect({broker: b.id, n: n})[0] AS top
RETURN cl.id AS clinic_id, top.broker AS top_broker, top.n AS top_broker_claims
"""
Q_TOP_ACCOUNT = """
MATCH (cl:Clinic)<-[:AT_CLINIC]-(c:Claim)-[:PAID_TO]->(a:PaymentAccount)
WHERE cl.id IN $ids
WITH cl, a, count(c) AS n
ORDER BY n DESC, a.id
WITH cl, collect({acc: a.id, n: n}) AS accs
RETURN cl.id AS clinic_id, accs[0].acc AS top_account,
       accs[0].n AS top_account_claims, size(accs) AS n_accounts
"""
Q_DOCTORS = """
MATCH (cl:Clinic)<-[:AT_CLINIC]-(c:Claim)-[:PERFORMED_BY]->(d:Doctor)
WHERE cl.id IN $ids
RETURN cl.id AS clinic_id, count(DISTINCT d) AS n_doctors
"""
Q_ADDRESS = """
MATCH (cl:Clinic)-[:LOCATED_AT]->(adr:Address)
WHERE cl.id IN $ids
OPTIONAL MATCH (other:Clinic)-[:LOCATED_AT]->(adr) WHERE other <> cl
WITH cl, adr, count(DISTINCT other) AS other_clinics
OPTIONAL MATCH (bk:Broker)-[:OPERATES_FROM]->(adr)
RETURN cl.id AS clinic_id, adr.id AS address_id, other_clinics,
       count(DISTINCT bk) AS brokers_at_address
"""
# "One-journey patients": all of the patient's claims are at this clinic and
# fit one journey's date span (a journey emits 1-3 claims within ~5 days).
Q_SINGLE_VISIT = """
MATCH (cl:Clinic)<-[:AT_CLINIC]-(c:Claim)-[:FOR_PATIENT]->(p:Patient)
WHERE cl.id IN $ids
WITH cl, p, count(c) AS here,
     min(c.procedure_date) AS lo, max(c.procedure_date) AS hi
MATCH (p)<-[:FOR_PATIENT]-(any_claim:Claim)
WITH cl, p, here, lo, hi, count(any_claim) AS total
WITH cl, (total = here AND duration.inDays(lo, hi).days <= 7) AS oneoff
RETURN cl.id AS clinic_id, count(*) AS patients,
       sum(CASE WHEN oneoff THEN 1 ELSE 0 END) AS oneoff_patients
"""
# "now" for registration age = newest procedure date in the graph, so the
# feature is a pure function of the data (no wall clock — determinism).
Q_DATA_NOW = "MATCH (c:Claim) RETURN toString(max(c.procedure_date)) AS now"
Q_CLINIC_CLAIMS = """
MATCH (cl:Clinic {id: $id})<-[:AT_CLINIC]-(c:Claim)
RETURN c.id AS id ORDER BY c.id
"""


def run(session, params: dict) -> list[dict]:
    base = {r["clinic_id"]: dict(r) for r in
            session.run(Q_BASE, min_claims=params["min_claims"])}
    if not base:
        return []
    ids = sorted(base)
    for q in (Q_TOP_BROKER, Q_TOP_ACCOUNT, Q_DOCTORS, Q_ADDRESS, Q_SINGLE_VISIT):
        for r in session.run(q, ids=ids):
            base[r["clinic_id"]].update(dict(r))
    data_now = date.fromisoformat(session.run(Q_DATA_NOW).single()["now"])
    communities = louvain_communities(session)
    sizes = community_sizes(communities)
    w = params["weights"]

    drafts = []
    for cid in ids:
        row = base[cid]
        claims = row["claims"]
        age_years = (data_now - date.fromisoformat(row["registered"])).days / 365.0
        top_broker_share = row.get("top_broker_claims", 0) / claims
        top_account_share = row.get("top_account_claims", 0) / claims
        claims_per_doctor = claims / max(row.get("n_doctors", 1), 1)
        oneoff_share = row.get("oneoff_patients", 0) / max(row.get("patients", 1), 1)
        address_entities = row.get("other_clinics", 0) + row.get("brokers_at_address", 0)

        # Volume against footprint, discounted by registration history: an
        # established bed-0 day clinic is normal, a young one billing hard is not.
        f_young = scale(params["young_years"] - age_years, 0.0, params["young_years"])
        f_volume = scale(claims / max(row["beds"], 1), 0.0, params["claims_per_bed_ref"])
        features = {
            "footprint": f_volume * (0.4 + 0.6 * f_young),
            "inflow": scale(top_broker_share,
                            0.7 * params["inflow_share"], params["inflow_share"]),
            "payout": scale(top_account_share,
                            0.85 * params["payout_share"], params["payout_share"]),
            "doctors": scale(claims_per_doctor,
                             0.5 * params["claims_per_doctor_ref"],
                             params["claims_per_doctor_ref"]),
            "address": scale(address_entities, 0.0, params["address_entities_ref"]),
            "single_visit": scale(oneoff_share, params["single_visit_baseline"], 1.0),
        }
        score = 100.0 * sum(w[k] * features[k] for k in w)
        strong = sorted(k for k, v in features.items() if v >= params["strong_cut"])
        if len(strong) < params["min_strong_features"]:
            # FP-mode mitigation (spec §1): one strong feature alone — new day
            # clinic, single corporate account, shared registered office —
            # must stay below the medium band.
            score = min(score, 49.9)
        if score < params["emit_min_score"]:
            continue

        implicated = [{"id": cid, "role": "ghost_clinic"}]
        if row.get("top_broker") and top_broker_share >= 0.5 * params["inflow_share"]:
            implicated.append({"id": row["top_broker"], "role": "feeder_broker"})
        if row.get("top_account") and top_account_share >= 0.7 * params["payout_share"]:
            implicated.append({"id": row["top_account"], "role": "hub_account"})
        if address_entities > 0:
            implicated.append({"id": row["address_id"], "role": "shared_address"})
        implicated += [{"id": r["id"], "role": "suspect_claim"}
                       for r in session.run(Q_CLINIC_CLAIMS, id=cid)]

        community = communities.get(cid)
        drafts.append({
            "anchor_id": cid,
            "score": score,
            "summary_params": {
                "clinic_name": row["name"],
                "claim_count": claims,
                "bed_count": row["beds"],
                "registration_age_years": round(age_years, 1),
                "inflow_share": round(top_broker_share, 3),
                "payout_share": round(top_account_share, 3),
                "distinct_doctors": row.get("n_doctors", 0),
                "claims_per_doctor": round(claims_per_doctor, 1),
                "one_journey_patient_share": round(oneoff_share, 3),
                "address_cotenants": address_entities,
                "features": {k: round(v, 3) for k, v in features.items()},
                "strong_features": strong,
                "community_id": community,
                "community_size": sizes.get(community, 0),
            },
            "implicated": implicated,
        })
    return drafts

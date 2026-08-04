"""Typology 4 — Template cloning (DETECTION_SPEC §4, revived per ADR-037).

A claim mill perfects one claim package and resubmits it across unrelated
patients, sometimes across insurers, names swapped. Approach exactly as
specified: candidate blocking in Cypher (same procedure + line_item_count),
then pairwise SimHash Hamming distance in Python; connected components of
mutually-similar claims with >= min_cluster members and a tight amount
band become one alert implicating the whole cluster.

FP guard (spec §4): legitimately standardized packages — LASIK, implant
packages, health checks — produce near-identical narratives *within one
clinic and one insurer*. Cross-insurer spread and shared submission
devices are what raise the score; without either the alert caps below
the medium band.
"""
from .common import scale

# One row per candidate block: every claim of one (procedure,
# line_item_count) pair, with the cluster evidence attached. Blocks
# smaller than min_cluster can never form a cluster and are skipped
# server-side.
Q_BLOCKS = """\
MATCH (c:Claim)-[:FOR_PROCEDURE]->(proc:Procedure)
MATCH (c)-[:FOR_PATIENT]->(pat:Patient)
MATCH (c)-[:AT_CLINIC]->(cl:Clinic)
MATCH (c)-[:BILLED_TO]->(ins:Insurer)
OPTIONAL MATCH (c)-[:ARRANGED_BY]->(b:Broker)
WITH proc, c.line_item_count AS line_items,
     collect({id: c.id, fp: c.narrative_fingerprint,
              amount: c.amount_usd, patient: pat.id, clinic: cl.id,
              clinic_name: cl.name, insurer: ins.id, broker: b.id}) AS claims
WHERE size(claims) >= $min_cluster
RETURN proc.id AS proc_id, proc.name AS proc_name, line_items, claims
ORDER BY proc_id, line_items
"""

# Devices used by >= 2 distinct patients of one cluster: the mill's
# office machines. Patient-owned devices never overlap across invented
# identities, so any hit is signal.
Q_SHARED_DEVICES = """\
MATCH (p:Patient)-[:USED_DEVICE]->(d:Device)
WHERE p.id IN $ids
WITH d, collect(DISTINCT p.id) AS users
WHERE size(users) >= 2
RETURN d.id AS id, size(users) AS user_count
ORDER BY user_count DESC, id
"""


def _hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _clusters(claims: list[dict], max_hamming: int) -> list[list[dict]]:
    """Connected components under 'Hamming(fp) <= max_hamming' — union-find
    over one block (blocks are small; honest blocks average ~40 claims)."""
    parent = list(range(len(claims)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            if _hamming(claims[i]["fp"], claims[j]["fp"]) <= max_hamming:
                parent[find(i)] = find(j)
    groups: dict[int, list[dict]] = {}
    for i, claim in enumerate(claims):
        groups.setdefault(find(i), []).append(claim)
    return [g for g in groups.values() if len(g) > 1]


def run(session, params: dict) -> list[dict]:
    w = params["weights"]
    drafts = []
    for block in session.run(Q_BLOCKS, min_cluster=params["min_cluster"]):
        for cluster in _clusters(list(block["claims"]), params["max_hamming"]):
            if len(cluster) < params["min_cluster"]:
                continue
            patients = sorted({c["patient"] for c in cluster})
            if len(patients) < params["min_distinct_patients"]:
                continue
            amounts = sorted(float(c["amount"]) for c in cluster)
            band = amounts[-1] / amounts[0] - 1.0 if amounts[0] else 99.0
            if band > params["amount_band_max"]:
                continue  # similar text but free-floating prices: not a package
            insurers = sorted({c["insurer"] for c in cluster})
            clinics = sorted({c["clinic"] for c in cluster})
            brokers = sorted({c["broker"] for c in cluster if c["broker"]})
            shared = [dict(r) for r in session.run(Q_SHARED_DEVICES, ids=patients)]

            features = {
                "cluster": scale(len(cluster), params["min_cluster"],
                                 params["cluster_ref"]),
                "insurers": scale(len(insurers), 1, params["insurers_ref"]),
                "devices": scale(len(shared), 0, 1),
                "patients": scale(len(patients), 1, params["patients_ref"]),
            }
            score = 100.0 * sum(w[k] * features[k] for k in w)
            if len(insurers) == 1 and not shared:
                # spec §4 FP mode: a same-clinic standardized package with no
                # cross-insurer spread and no shared devices stays below medium.
                score = min(score, 49.9)
            if score < params["emit_min_score"]:
                continue

            anchor = max(clinics, key=lambda cid: sum(
                1 for c in cluster if c["clinic"] == cid))
            clinic_name = next(c["clinic_name"] for c in cluster
                               if c["clinic"] == anchor)
            implicated = [{"id": anchor, "role": "mill_clinic"}]
            implicated += [{"id": b, "role": "feeder_broker"} for b in brokers]
            implicated += [{"id": d["id"], "role": "shared_device"}
                           for d in shared]
            implicated += [{"id": p, "role": "package_patient"}
                           for p in patients]
            implicated += [{"id": c["id"], "role": "cloned_claim"}
                           for c in sorted(cluster, key=lambda c: c["id"])]

            drafts.append({
                "anchor_id": anchor,
                "score": score,
                "summary_params": {
                    "clinic_name": clinic_name,
                    "procedure_name": block["proc_name"],
                    "line_item_count": block["line_items"],
                    "cluster_size": len(cluster),
                    "distinct_patients": len(patients),
                    "distinct_insurers": len(insurers),
                    "distinct_clinics": len(clinics),
                    "shared_devices": len(shared),
                    "amount_band_pct": round(band * 100, 1),
                    "amount_min_usd": amounts[0],
                    "amount_max_usd": amounts[-1],
                    "max_hamming": params["max_hamming"],
                    "features": {k: round(v, 3) for k, v in features.items()},
                },
                "implicated": implicated,
            })
    return drafts

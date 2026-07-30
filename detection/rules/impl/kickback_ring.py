"""Typology 3 — kickback ring (DETECTION_SPEC §3, amended by ADR-028).

Steering is a *concentration* pattern (measured, not assumed:
detection/benchmarks/typology3_centrality.md), so candidates are
broker-clinic pairs gated by referral concentration:

- broker side: the share of the broker's referrals landing at this clinic
  (for the broker's top clinic this IS the benchmarked top-clinic share);
- clinic side: the share of the clinic's total claims arranged by this
  broker. Both directions matter — a big broker dominating a tiny clinic
  is normal one way, suspicious both ways.

Shared infrastructure completes the score and is the only route to
low-volume steering brokers (8 of 13 emergent steerers sit at or below the
median referral volume): hidden stakes, clinic->broker money above the
declared commissions, transfers hopping through shell accounts (no
OWNED_BY), shared addresses, co-owned accounts. Louvain community is ring
*context* — a small bonus, never a gate. No PageRank, no betweenness.
"""
from .common import community_sizes, louvain_communities, scale

# The expected commission per pair is computable exactly: commission_pct
# rides on each ARRANGED_BY edge, so any clinic->broker money beyond
# sum(amount * pct) is unexplained by the declared relationship.
Q_PAIRS = """
MATCH (c:Claim)-[ab:ARRANGED_BY]->(b:Broker)
MATCH (c)-[:AT_CLINIC]->(cl:Clinic)
WITH b, cl, count(c) AS pair_claims, sum(c.amount_usd) AS pair_amount,
     sum(c.amount_usd * ab.commission_pct / 100.0) AS expected_commission
RETURN b.id AS broker, cl.id AS clinic, pair_claims,
       pair_amount, expected_commission
"""
Q_BROKER_TOTALS = """
MATCH (c:Claim)-[:ARRANGED_BY]->(b:Broker)
RETURN b.id AS broker, count(c) AS total
"""
Q_CLINIC_TOTALS = """
MATCH (cl:Clinic)
OPTIONAL MATCH (cl)<-[:AT_CLINIC]-(c:Claim)
RETURN cl.id AS clinic, cl.name AS name,
       cl.accreditation_status AS accreditation, count(c) AS total
"""
Q_STAKES = """
UNWIND $pairs AS pr
MATCH (b:Broker {id: pr.broker})-[s:OWNS_STAKE_IN]->(cl:Clinic {id: pr.clinic})
RETURN pr.broker AS broker, pr.clinic AS clinic, s.pct AS stake_pct
"""
Q_SHARED_ADDRESS = """
UNWIND $pairs AS pr
MATCH (b:Broker {id: pr.broker})-[:OPERATES_FROM]->(a:Address)
      <-[:LOCATED_AT]-(cl:Clinic {id: pr.clinic})
RETURN pr.broker AS broker, pr.clinic AS clinic, a.id AS address_id
"""
Q_COMMON_ACCOUNTS = """
UNWIND $pairs AS pr
MATCH (acc:PaymentAccount)-[:OWNED_BY]->(:Broker {id: pr.broker})
MATCH (acc)-[:OWNED_BY]->(:Clinic {id: pr.clinic})
RETURN pr.broker AS broker, pr.clinic AS clinic, collect(acc.id) AS accounts
"""
Q_DIRECT_TRANSFERS = """
UNWIND $pairs AS pr
MATCH (ca:PaymentAccount)-[:OWNED_BY]->(:Clinic {id: pr.clinic})
MATCH (ba:PaymentAccount)-[:OWNED_BY]->(:Broker {id: pr.broker})
MATCH (ca)-[t:TRANSFERRED]->(ba)
RETURN pr.broker AS broker, pr.clinic AS clinic,
       sum(t.amount_usd) AS to_broker, count(t) AS n_transfers,
       collect(DISTINCT ca.id) + collect(DISTINCT ba.id) AS accounts
"""
# Shell hop = an intermediate account with NO OWNED_BY edge (DATA_MODEL:
# that absence is data). Length 2..4 covers the generator's 1-3 shell hops.
Q_SHELL_PATHS = """
UNWIND $pairs AS pr
MATCH (ca:PaymentAccount)-[:OWNED_BY]->(:Clinic {id: pr.clinic})
MATCH (ba:PaymentAccount)-[:OWNED_BY]->(:Broker {id: pr.broker})
MATCH p = (ca)-[:TRANSFERRED*2..4]->(ba)
WHERE all(mid IN nodes(p)[1..-1] WHERE NOT (mid)-[:OWNED_BY]->())
WITH pr, p, [mid IN nodes(p)[1..-1] | mid.id] AS shells,
     relationships(p)[0].amount_usd AS entry_amount
RETURN pr.broker AS broker, pr.clinic AS clinic, count(p) AS shell_paths,
       sum(entry_amount) AS shell_amount, collect(shells) AS shell_hops
"""
Q_PAIR_CLAIMS = """
MATCH (c:Claim)-[:ARRANGED_BY]->(:Broker {id: $broker})
MATCH (c)-[:AT_CLINIC]->(:Clinic {id: $clinic})
RETURN c.id AS id ORDER BY c.id
"""


def run(session, params: dict) -> list[dict]:
    pairs = [dict(r) for r in session.run(Q_PAIRS)]
    broker_total = {r["broker"]: r["total"] for r in session.run(Q_BROKER_TOTALS)}
    clinic_info = {r["clinic"]: dict(r) for r in session.run(Q_CLINIC_TOTALS)}

    candidates = []
    for p in pairs:
        p["broker_share"] = p["pair_claims"] / broker_total[p["broker"]]
        p["clinic_share"] = p["pair_claims"] / max(clinic_info[p["clinic"]]["total"], 1)
        if (p["pair_claims"] >= params["min_pair_claims"]
                and p["broker_share"] >= params["broker_share_gate"]):
            candidates.append(p)
    if not candidates:
        return []

    keys = [{"broker": p["broker"], "clinic": p["clinic"]} for p in candidates]
    def by_pair(query):
        return {(r["broker"], r["clinic"]): dict(r)
                for r in session.run(query, pairs=keys)}
    stakes = by_pair(Q_STAKES)
    addresses = by_pair(Q_SHARED_ADDRESS)
    common_accounts = by_pair(Q_COMMON_ACCOUNTS)
    transfers = by_pair(Q_DIRECT_TRANSFERS)
    shells = by_pair(Q_SHELL_PATHS)
    communities = louvain_communities(session)
    sizes = community_sizes(communities)

    drafts = []
    for p in sorted(candidates, key=lambda x: (x["broker"], x["clinic"])):
        key = (p["broker"], p["clinic"])
        # --- concentration: both directions, discounted for tiny volume ---
        broker_side = scale(p["broker_share"],
                            params["broker_share_gate"], params["broker_share_ref"])
        clinic_side = scale(p["clinic_share"],
                            params["clinic_share_lo"], params["clinic_share_ref"])
        volume = scale(p["pair_claims"], params["min_pair_claims"],
                       params["volume_ref"])
        conc_pts = (params["concentration_max"]
                    * (0.5 * broker_side + 0.5 * clinic_side)
                    * (0.5 + 0.5 * volume))

        # --- shared infrastructure ---
        infra_pts = 0.0
        evidence = {}
        stake = stakes.get(key)
        accreditation = clinic_info[p["clinic"]]["accreditation"]
        if stake:
            soften = params["stake_softening"].get(accreditation, 1.0)
            infra_pts += (params["stake_max"]
                          * scale(stake["stake_pct"], 0.0, params["stake_ref_pct"])
                          * soften)
            evidence["stake_pct"] = stake["stake_pct"]
            evidence["stake_softening"] = soften
        tr = transfers.get(key)
        excess_ratio = 0.0
        if tr:
            excess = tr["to_broker"] - p["expected_commission"]
            excess_ratio = excess / max(p["pair_amount"], 1.0)
            infra_pts += params["excess_max"] * scale(
                excess_ratio, params["excess_lo"], params["excess_ref"])
            evidence["transfers_to_broker_usd"] = round(tr["to_broker"], 2)
            evidence["expected_commission_usd"] = round(p["expected_commission"], 2)
            evidence["excess_transfer_ratio"] = round(excess_ratio, 4)
        sh = shells.get(key)
        if sh and sh["shell_paths"] > 0:
            infra_pts += params["shell_max"] * scale(
                sh["shell_paths"], 0.0, params["shell_paths_ref"])
            evidence["shell_paths"] = sh["shell_paths"]
            evidence["shell_amount_usd"] = round(sh["shell_amount"], 2)
        if key in addresses:
            infra_pts += params["shared_address_pts"]
            evidence["shared_address"] = addresses[key]["address_id"]
        if key in common_accounts:
            infra_pts += params["common_account_pts"]
            evidence["common_accounts"] = sorted(common_accounts[key]["accounts"])
        infra_pts = min(infra_pts, params["infrastructure_max"])

        # --- ring context (never a gate — ADR-028) ---
        b_comm, c_comm = communities.get(p["broker"]), communities.get(p["clinic"])
        same_small_community = (b_comm is not None and b_comm == c_comm
                                and sizes[b_comm] <= params["community_size_max"])
        score = conc_pts + infra_pts + (
            params["community_bonus"] if same_small_community else 0.0)
        if score < params["emit_min_score"]:
            continue

        implicated = [{"id": p["broker"], "role": "kickback_broker"},
                      {"id": p["clinic"], "role": "partner_clinic"}]
        if key in addresses:
            implicated.append({"id": addresses[key]["address_id"],
                               "role": "shared_address"})
        for acc in sorted(set(common_accounts.get(key, {}).get("accounts", []))):
            implicated.append({"id": acc, "role": "shared_account"})
        for acc in sorted(set(transfers.get(key, {}).get("accounts", []))):
            implicated.append({"id": acc, "role": "ring_account"})
        if sh:
            shell_ids = sorted({s for hop in sh["shell_hops"] for s in hop})
            implicated += [{"id": s, "role": "shell_account"} for s in shell_ids]
        seen = set()
        implicated = [e for e in implicated
                      if not (e["id"] in seen or seen.add(e["id"]))]
        implicated += [{"id": r["id"], "role": "steered_claim"}
                       for r in session.run(Q_PAIR_CLAIMS,
                                            broker=p["broker"], clinic=p["clinic"])]

        drafts.append({
            "anchor_id": f"{p['broker']}:{p['clinic']}",
            "score": score,
            "summary_params": {
                "broker_id": p["broker"],
                "clinic_id": p["clinic"],
                "clinic_name": clinic_info[p["clinic"]]["name"],
                "pair_claims": p["pair_claims"],
                "pair_amount_usd": round(p["pair_amount"], 2),
                "broker_share": round(p["broker_share"], 3),
                "clinic_share": round(p["clinic_share"], 3),
                "accreditation_status": accreditation,
                "concentration_points": round(conc_pts, 1),
                "infrastructure_points": round(infra_pts, 1),
                "same_small_community": same_small_community,
                "community_id": b_comm,
                **evidence,
            },
            "implicated": implicated,
        })
    return drafts

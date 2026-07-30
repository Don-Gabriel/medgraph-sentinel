# Typology 3 (kickback ring) — centrality benchmark

**Question:** does typology 3 need betweenness centrality at all, or do
PageRank / (weighted) degree on the right projection identify steering
brokers as well or better — and what does betweenness cost at each scale?

- Date: 2026-07-30. GDS **2.13.11** (verified live via `gds.version()`),
  Neo4j 5.26 Community, floor memory profile (2G heap / 1G pagecache),
  container `replan-single-implementer-7dfbb0-neo4j-1`.
- Every GDS call below was verified against the live install with
  `CALL gds.list("<name>")` before use (procedure signatures), and the
  config keys `samplingSize` / `samplingSeed` / `relationshipWeightProperty`
  / `undirectedRelationshipTypes` were verified by live acceptance on
  2.13.11 (an invalid key raises an error; none did).
- All numbers are **measured**, not estimated. `computeMillis` /
  `preProcessingMillis` come from GDS `*.stats` modes; "wall" is measured
  end-to-end around `docker exec` + `cypher-shell` (which adds a constant
  ~2.2–2.4 s of client startup overhead — visible in every fast query).
- **Ground-truth use:** this is an offline *evaluation* artifact. The
  steering-broker set was read from `data/ground_truth/actor_params.csv`
  (`param_name = steering_greed`, value > 0) to score rankings only. No
  detection code reads ground truth (INTERFACES §2 / hard rule 5 intact);
  thresholds are still calibrated on the honest economy only.

Ground truth: **K = 13** steering brokers out of 250
(`BRK_000017, 000029, 000034, 000054, 000063, 000067, 000100, 000125,
000142, 000153, 000188, 000238, 000250`).

## 1. Projections

### 1a. Large claim-participation projection (ADR-026 baseline style)

Reconstructed to ADR-026's exact counts (34,078 nodes / 189,972 rels):
nodes = Claim + Patient + Clinic + Broker + PaymentAccount
(21,622 + 10,008 + 600 + 250 + 1,598), rels = FOR_PATIENT + AT_CLINIC +
ARRANGED_BY + PAID_TO + TRANSFERRED (94,986, reported doubled by GDS
under UNDIRECTED orientation).

```cypher
CALL gds.graph.project(
  'bench_claimpart',
  ['Claim','Patient','Clinic','Broker','PaymentAccount'],
  {
    FOR_PATIENT: {orientation: 'UNDIRECTED'},
    AT_CLINIC:   {orientation: 'UNDIRECTED'},
    ARRANGED_BY: {orientation: 'UNDIRECTED'},
    PAID_TO:     {orientation: 'UNDIRECTED'},
    TRANSFERRED: {orientation: 'UNDIRECTED'}
  }
)
```

Result: 34,078 nodes / 189,972 rels — **exact match to ADR-026**.
projectMillis 366 (wall 2.8 s).

### 1b. Purpose-built referral projection (weighted BROKER–CLINIC)

Claims collapsed into weighted broker→clinic edges
(weight = number of claims that broker arranged at that clinic), made
undirected at projection time. Uses the GDS 2.13 Cypher-aggregation
projection (`gds.graph.project` *function* form, verified via `gds.list`).

```cypher
MATCH (c:Claim)-[:ARRANGED_BY]->(b:Broker)
MATCH (c)-[:AT_CLINIC]->(cl:Clinic)
WITH b, cl, count(c) AS w
WITH gds.graph.project(
  'bench_referral',
  b, cl,
  {
    sourceNodeLabels: ['Broker'],
    targetNodeLabels: ['Clinic'],
    relationshipProperties: {weight: w}
  },
  {undirectedRelationshipTypes: ['*']}
) AS g
RETURN g.nodeCount, g.relationshipCount
```

Result: **652 nodes** (234 brokers with ≥1 arranged claim + 418 clinics)
/ **5,008 rels** (2,504 distinct broker–clinic pairs, doubled).
projectMillis 779 (wall 3.7 s). 16 of 250 brokers arranged zero claims
and appear in no volume-based ranking.

## 2. Measured timings

| run | graph | computeMillis | preProc | wall (incl. shell) |
|---|---|---:|---:|---:|
| betweenness exact, `stats` | large (34,078 n) | **131,589** | 1 | 133.8 s |
| betweenness exact, `stream` (all nodes) | large | — | — | 132.0 s |
| betweenness `samplingSize: 512, samplingSeed: 42`, `stats` | large | **1,789** | 2 | 4.3 s |
| betweenness `samplingSize: 2048, samplingSeed: 42`, `stats` | large | **7,092** | 0 | 9.3 s |
| betweenness exact, `stats` | referral (652 n) | **73** | 0 | 2.3 s |
| PageRank unweighted, `stats` (20 iters, didConverge=false) | referral | **106** | 0 | 2.4 s |
| PageRank `relationshipWeightProperty:'weight'`, `stats` (20 iters, didConverge=false) | referral | **85** | 1 | 2.4 s |
| degree `relationshipWeightProperty:'weight'`, `stats` | referral | **2** | 0 | 2.3 s |
| naive referral claim count (plain Cypher) | store | — | — | 2.4 s |
| top-clinic share, min 20 referrals (plain Cypher) | store | — | — | 2.4 s |

ADR-026 measured 122.5 s for the same exact-betweenness baseline; today's
131.6 s is the same machine class under container load — same order,
baseline confirmed.

## 3. Discrimination vs ground truth (K = 13, universe = all 250 brokers)

Ranking convention: score descending; brokers with no score (not in the
projection, or excluded by a volume floor) share rank `(#scored + 1)` —
so median ranks of floor-filtered features are floor-dependent; compare
hits@13 first. P@13 = R@13 because K = |true set| = 13.

| measure | hits@13 | P@13 | R@13 | median rank of true 13 |
|---|---:|---:|---:|---:|
| referral betweenness (exact, undirected) | 1 | 0.077 | 0.077 | 131 |
| referral PageRank (unweighted) | 1 | 0.077 | 0.077 | 129 |
| referral PageRank (weighted) | 2 | 0.154 | 0.154 | 86 |
| referral weighted degree | 2 | 0.154 | 0.154 | 117 |
| referral unweighted degree (distinct clinics) | 1 | 0.077 | 0.077 | 114 |
| naive referral claim count (no GDS) | 2 | 0.154 | 0.154 | 117 |
| **top-clinic share, ≥20 referrals (no GDS)** | **5** | **0.385** | **0.385** | 66 |
| top-clinic share, ≥10 referrals (sensitivity) | 5 | 0.385 | 0.385 | 117 |

Verified identity: **weighted degree on the referral projection equals the
naive claim count for every broker** (0 mismatches across 234 brokers) —
it is the same feature with GDS overhead attached.

### Why the recall ceiling sits at ~5/13

Measured steering-broker referral volumes: 2, 2, 6, 8, 9, 9, 9, 10, 36,
106, 127, 391, 1,781. **8 of 13 steering brokers have ≤10 referrals**,
while the *median* broker in the economy has 9 — those eight are
statistically invisible to every referral-volume or referral-topology
signal. For the 5 steering brokers with ≥20 referrals, top-clinic share
ranked them **1, 2, 3, 4, 7** out of 65 qualifying brokers (their shares:
0.31–0.84 of all referrals into one clinic) — near-perfect. The invisible
eight are exactly the case the spec's *shared-infrastructure* signature
(`OWNS_STAKE_IN`, common `OWNED_BY`, `TRANSFERRED`, shared addresses)
exists for; no centrality measure recovers them from referral structure.

## 4. Sampled vs exact betweenness (large projection, seed 42)

| samplingSize | computeMillis | % of exact cost | Spearman ρ vs exact (34,078 nodes) | top-50 overlap |
|---:|---:|---:|---:|---:|
| 512 | 1,789 | 1.4% | 0.8941 | 40/50 (80%) |
| 2048 | 7,092 | 5.4% | 0.9457 | 47/50 (94%) |
| exact | 131,589 | 100% | 1.0 | 50/50 |

## 5. Recommendation

Typology 3 should **not** use betweenness centrality. It is the *worst*
discriminator tested (1/13 at K, median rank 131) while being the most
expensive: 131.6 s exact on the full claim-participation graph — and even
on the 652-node referral projection, where it costs only 73 ms, it still
finds nothing PageRank/degree don't, because steering is a
**concentration** pattern, not a bridging pattern. PageRank earns nothing
either: its weighted variant (2/13) merely tracks volume, and weighted
degree is *provably identical* to a one-line Cypher claim count. The best
volume-side signal is the one-line **top-clinic-share** Cypher feature
(5/13 at K; ranks 1–7 for every steering broker with enough volume to be
visible), which costs no GDS at all — the rule should combine it with the
spec's mutual-concentration test and the shared-infrastructure signature,
which is the only route to the eight low-volume steering brokers. Keep
Louvain for ring context (2.4 s, ADR-026). If Day-2 ever demands
betweenness on the full graph anyway, use
`samplingSize: 2048` — ρ = 0.946 / 94% top-50 agreement at 5.4% of the
exact cost (7.1 s vs 131.6 s).

*Benchmark artifacts (raw score CSVs, metrics script) lived in the session
scratchpad; in-memory graphs `bench_claimpart` and `bench_referral` were
dropped after the run (`gds.graph.list()` → 0 remaining).*

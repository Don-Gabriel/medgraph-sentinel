# detection/

> ⛔ **Held-out discipline (ADR-027):** everything in this directory
> postdates the held-out hash commit in docs/HELDOUT_COMMITMENT.md
> (2026-07-30) — that ordering is the circularity defense. Sessions
> working here must never open the off-repo held-out scenario files
> before the one-shot evaluation.

The rule registry and batch runner (INTERFACES §5, ADR-008). Each typology
is a registry entry: `rules/<key>.yaml` (metadata, tunable params, severity
bands) plus a Python module or parameterized Cypher file. Nothing here may
read `data/ground_truth/` — only `evaluation/` does.

## Shipping rules (ADR-024 scope: typologies 1, 2, 3, 5)

| rule key | typology | implementation | core signals |
|---|---|---|---|
| `ghost_clinic` | 1 | python | volume vs footprint/age, single-broker inflow, payout concentration, thin doctor roster, address co-tenancy, one-journey patients; Louvain ring context. Fewer than 2 strong features ⇒ capped below `medium` (FP modes). |
| `credential_laundering` | 2 | python | (a) shared licence number (same-body/-country guard), (b) post-revocation billing (grace window, no-other-active-credential guard, volume-tiered severity), (c) jurisdiction shopping |
| `kickback_ring` | 3 | python | mutual broker↔clinic referral concentration gate + shared infrastructure (stakes softened by accreditation, clinic→broker money beyond declared commissions, shell-hop paths, shared addresses, co-owned accounts); Louvain context. **No centrality (ADR-028).** |
| `impossible_travel` | 5 | python | per passport-identity group, consecutive claims in different treatment countries vs the minimum-travel-days table (`generator/config.yaml: travel_time_days`, mirrored in the rule YAML, sync-tested) |

## Running

```bash
python -m detection.run                          # all rules, write alerts
python -m detection.run --rules kickback_ring    # subset
python -m detection.run --dry-run                # compute + summarize, write nothing
python -m detection.run --created-at 2026-08-07T00:00:00+00:00   # build phase
python -m detection.export                       # graph -> committed alert CSVs
```

Env: `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` (INTERFACES §1); export
also uses `DATA_DIR`. The demo build (ADR-018/029) pins `--created-at` so
re-exporting the unchanged graph is byte-identical (verified: export →
load-from-CSV → re-export produced identical bytes).

Runs are idempotent per rule+version; alert IDs are assigned by sorting
(rule key, score desc, anchor id) — a full run numbers from `ALT_000001`,
a `--rules` subset continues after the highest surviving ID.

## Calibration (DATA_GENERATION §6 — honest economy only)

Thresholds were tuned 2026-07-30 against a seed-42 generation with every
`fraud:` gate set to 0.0 (never against fraud labels). Honest-economy alert
counts at the committed thresholds — these are the documented FP rates:

| rule | low | medium | high |
|---|---|---|---|
| ghost_clinic | 5 | 0 | 0 |
| credential_laundering | 62 | 0 | 0 |
| kickback_ring | 0 | 0 | 0 |
| impossible_travel | 6 | 0 | 0 |

Calibration findings that shaped the rules (measured, seed 42):

- The honest economy keeps revoked doctors on clinic rosters: 27 honest
  doctors bill post-revocation (1–29 claims, revocation-to-claim gaps from
  18 days). Existence, recency and moderate volume are therefore honest
  noise; the spec's "starts at high" is implemented as a volume ramp that
  reaches `high` only beyond the honest ceiling (≥ ~42 post-revocation
  claims). Flagged in OPEN_QUESTIONS for the generator owner.
- Honest licence-number collisions exist (9 two-holder, same-country
  groups) — two holders stay `low`; three holders or cross-country reuse
  (impossible honestly: numbers embed the issuing country) escalate.
- 26 honest doctors hold an unused-jurisdiction credential with claims in
  exactly 2 other countries (cross-country rosters are legal here); 3+
  claim countries never happens honestly and escalates.
- 6 honest same-day cross-country date artifacts (return patients; we
  store dates, not times) — a single-identity single pair stays `low`;
  cross-insurer only escalates alongside identity multiplexing.

## Determinism boundary (measured)

GDS Louvain runs single-threaded (`readConcurrency`/`concurrency` 1) with
community labels canonicalized to the smallest member id. Within one loaded
store, detection → export is byte-stable (verified twice). Across a
wipe-and-reload, Neo4j reassigns internal ids from its freelist in a
different order and Louvain's tie-breaking follows store order: the two
community *context* fields (`community_id`, `community_size`) can drift on
a few borderline nodes while **scores, severities, alert IDs, edges and
alert sets stay byte-identical** (verified across two independent
load→detect→export cycles). The committed demo artifacts are produced by
exactly one detection run (ADR-018 one-way chain), so this boundary never
touches them; it matters only if a Day-2 re-run compares summaries across
reloads. Kickback's `community_bonus` (4 pts) is the only score term
reading Louvain; no shipped alert sits within 4 points of a band edge.

Contracts: [docs/INTERFACES.md](../docs/INTERFACES.md) §5,
[docs/DETECTION_SPEC.md](../docs/DETECTION_SPEC.md) (freezes Aug 6).
Benchmark evidence for the no-centrality decision:
[benchmarks/typology3_centrality.md](benchmarks/typology3_centrality.md).

# generator/

The synthetic medical-tourism economy. Design:
[docs/DATA_GENERATION.md](../docs/DATA_GENERATION.md); output contract:
[docs/INTERFACES.md](../docs/INTERFACES.md) §2–3.

```
python -m generator --seed 42 --out data/ [--scenario file.yaml ...]
```

- `config.yaml` — every tunable distribution (the M2 tuning surface and the
  Day-2 scale knobs). `config.py` validates it and hashes it for the
  manifest.
- `economy.py` — honest actors + journeys. Fraud parameters distort honest
  decisions inline (steering, recycling, overbilling) — fraud is never a
  separate labeled code path. `emit_journey_claims` is the single claim
  emitter every layer routes through.
- `fraud.py` — emergent parameter assignment + kickback/shell/recycle
  transfers + `parallel_recycling` (the typology-5 fix: a configured share
  of recycled-clone events also books a parallel journey — same identity,
  same day, different treatment country — because colluding clinics bill a
  recruited identity simultaneously; sequential reuse alone never violates
  the whole-day travel table). Ground truth = the parameter record, written
  to `data/ground_truth/` (evaluation-only — INTERFACES §2).
- `plant.py` — PLANTED cells (DATA_GENERATION §4): 3 ghost-clinic cells
  (paper clinic + dedicated feeder broker + invented one-journey patients +
  concentrated payout account) and 3 credential-laundering cells (one
  licence number cloned across 3–4 doctor identities practising in
  different countries; cell 1's original keeps billing after revocation at
  a volume above the honest ceiling). Labels →
  `data/ground_truth/planted.csv`; CREATED entities only — honest entities
  a cell touches stay unlabeled so they can't launder a false positive.
  `planted.*.cells: 0` switches the layer off (honest calibration runs).
- `scenario.py` — `--scenario` overlays implementing the full INTERFACES §3
  schema (all five actor kinds, country pins, edges between refs/existing
  IDs, doctor-pinned journeys, invented/recycled/pool patients, transfers
  with count/shells/attrition). Scenario actors draw IDs from a reserved
  range (`PAT_900001+`, `CLM_9000001+`) so they never collide with base
  entities; ground truth → `data/ground_truth/scenario_<name>.csv`.
- `narrative.py` — templated claim narratives + 64-bit SimHash fingerprint
  (OQ #3: SimHash-first).
- `writer.py` — deterministic CSVs + manifest (sorted rows, 2dp money, no
  timestamps — ADR-006).

**Pass order** (byte-determinism, ADR-006): honest economy → emergent fraud
→ parallel-recycling additions → planted cells → scenario overlays (sorted
by scenario name), all drawing from one numpy Generator. Every later pass
draws strictly after the earlier ones, so disabling a later layer never
changes an earlier layer's bytes; the same seed + config + scenario set is
byte-identical regardless of `--scenario` flag order.

**Fixture scenarios** (`data/scenarios/fixture_*.yaml`) are SCHEMA SMOKE
TESTS, not fraud test sets — held-out scenarios live outside the repo
(ADR-027) and overlay tooling is developed against the schema + fixtures
only. `tests/test_scenario_overlay.py` applies them to a small generation.

**Overlay schema decisions** (ambiguities in INTERFACES §3 resolved here,
flagged for the owner):

- `recycled:<n>`: n source identities; journeys cycle through them; each
  use after a source's first creates a CLONE node (same passport/dob/
  device, new alias) — mirroring emergent recycling. `pool:<ref>` reuses
  the SAME Patient nodes (per the schema comment).
- transfer `path` entries: `<ref>.account` / `<existing id>.account` (first
  account, created if absent), raw `ACC_…` ids, or `shell` (one new unowned
  account per position, shared by all `count` transfers of the entry).
  `amount_usd` is the per-transfer first-hop amount; `attrition_pct`
  applies per hop.
- edges whose data lives on node records (HOLDS, ISSUED_IN, RESIDES_IN,
  OWNED_BY on scenario rows, USED_DEVICE, PRACTISES_AT, OWNS_STAKE_IN,
  TRANSFERRED) update those records; all other DATA_MODEL types become raw
  rows in the matching `rel_*.csv`.
- an optional top-level `typology:` key labels the ground-truth rows
  (empty string when absent).
- credential actors without `props.country` derive ISSUED_IN from the
  country embedded in an `MC-XX…` licence number; otherwise it must be
  given explicitly.
- broker `params` are appended to `actor_params.csv` (they ARE emergent
  incentive parameters — evaluation derives kickback/recycling truth from
  that file); `steering_greed` additionally marks that broker's scenario
  journeys as steered and materializes side payments over those claims.

**Known v1 simplifications** (M2 tuning items, tracked in STATUS): Faker
names/streets are en-US regardless of country; category choice is
age-independent; no duplicate-name-spelling noise yet; "family" device
sharing is approximated by same-country device pooling rather than real
family units. Distribution realism
is tuned to DATA_GENERATION §2 at M2, judged by the M2 exit test.

# Synthetic Data Generation

How the synthetic medical-tourism economy is simulated. The generator is the
foundation of the project's credibility: a sharp judge will ask *"didn't you
just find what you planted?"* — this document is the answer.

## 1. Design principles

1. **Simulation first, fraud second.** The generator simulates an *economy*
   of actors making decisions under incentives — not a dataset with fraud
   rows. Most actors are honest; the honest economy must look right before
   any fraud exists.
2. **Determinism.** One RNG seed (`GENERATOR_SEED`, default `42`) drives
   everything via a single `numpy.random.Generator`. Same seed + same config
   ⇒ byte-identical CSVs. The manifest carries the seed and a config hash;
   no timestamps in generated files (ADR-006).
3. **Three fraud layers, kept separate:** EMERGENT (behavioural), PLANTED
   (templated, labeled), HELD-OUT (sealed, post-freeze). Defined in §3–5.
4. **Scale:** ~50k nodes, committed CSVs < 50 MB. If size busts the budget,
   reduce claim count — never Git LFS (owner decision, Q7).

## 2. The honest economy

**Geography.** Treatment countries: India, Thailand, Turkey, UAE, Singapore —
real corridors, each with a `cost_multiplier` (e.g. IN cheap, SG premium).
Origin countries: ~10 (US, GB, DE, AU, NG, BD, PK, RU, SA, KE) with outbound
patient volumes weighted by plausible corridor gravity (origin region ×
category × price advantage). All *entities* are fictional (Q5).

**Actors and distributions** (all parameters live in `generator/config.yaml`,
build phase; values below are starting points, tuned to look right):

| population | count (approx) | shape |
|---|---|---|
| Patients | 12,000 | one treatment journey each; ~8% return patients |
| Doctors | 1,800 | 1–3 clinic affiliations; specialty fixed |
| Credentials | ~2,000 | 1–2 per doctor; ~3% revoked in the honest world (retirements, discipline) |
| Clinics | 600 | size ~ Zipf: few large hospitals, long tail of day clinics |
| Brokers | 250 | referral share ~ Zipf; commission 5–15% |
| Claims | 25,000 | the hub population; volume per clinic ∝ size × quality |
| PaymentAccounts | 1,500 | clinics 1–3 each, brokers 1–2, plus shells (fraud layers only) |
| Devices | 6,000 | patients 1–2 each; honest sharing exists (family devices) |
| Addresses | 1,200 | clinics + brokers; some honest co-location |
| Procedures | ~120 | catalog across 6 categories; base costs lognormal within category |
| Insurers | 20 | market share ~ Zipf |
| Countries | ~15 | 5 treatment + ~10 origin |

**Journey model.** A patient picks a category (age/origin-weighted), then a
corridor (gravity), then a clinic (size/quality-weighted within corridor),
gets a doctor of that specialty at that clinic, a procedure from the
category, a price = `base_cost × country_multiplier × lognormal noise`, dates
(procedure, then submission +2–30 days), a payout account of the clinic, and
~65% of journeys an arranging broker. Claim narratives are assembled from
templated fragments; the fingerprint is computed from the assembled text, so
honest narratives are similar-but-not-identical.

**Honest noise is mandatory.** Duplicate name spellings, shared family
devices, clinics sharing registered offices, brokers with genuine exclusive
partnerships — the honest world must contain *weak* versions of every fraud
signal, or detection is trivially easy and the judges will see it.

## 3. EMERGENT fraud (behavioural)

No entity is labeled "fraudulent." Instead, a small fraction of actors get
*incentive parameters* drawn at generation time, and fraud **emerges from
their local decision rules interacting**:

- `overbilling_propensity` (clinics, ~5% get >0): inflates amounts and
  line-item counts by a drawn factor on a drawn fraction of claims.
- `steering_greed` (brokers, ~6% get >0): routing probability skews toward
  clinics that pay a side commission; the side payments materialize as
  `TRANSFERRED` clinic-account → broker-account flows. When a greedy broker
  meets a paying clinic, a kickback ring *emerges* — we never place a ring.
- `identity_recycling` (brokers, ~2%): reuses patient identities (passport,
  device) across insurers when recruiting — impossible-travel and
  identity-sharing patterns emerge from reuse frequency, not from a script.
- `shell_layering` (clinic-broker pairs with active side payments, small
  fraction): side payments route through 1–3 shell accounts instead of going
  direct, with attrition — circular structures emerge when recycled money
  returns as fake claim payouts.

Because these are *parameters*, the ground truth for evaluation is **derived,
not planted**: `data/ground_truth/actor_params.csv` records which actors got
which parameters, and an evaluation script derives which claims/entities were
actually affected. Detection code never reads this directory (enforced by
review; the API and detection layers have no code path to it).

## 4. PLANTED fraud (templated)

Two typologies are structural enough that emergence is unreliable at our
scale, so they are explicitly planted with exact labels:

- **Ghost clinic cells** (2–3): clinic with no real activity + dedicated
  feeder broker + invented patients + single payout account.
- **Credential laundering cells** (2–3): one licence number cloned across
  3–4 doctor identities in different countries; one post-revocation biller.

Planted cells are generated *through the same journey model* (they emit
normal-looking claims), so they don't glow statistically. Labels go to
`data/ground_truth/planted.csv`.

**Honesty rule for the pitch:** we say plainly which typologies were planted
vs. emergent. Precision/recall is reported per layer.

## 5. HELD-OUT scenarios (the circularity defense)

Time-boxed abstention protocol (owner decision, Q4):

1. On DETECTION_SPEC freeze day (planned 2026-08-06), the freeze is its own
   commit, recorded in DECISIONS.md.
2. From freeze until evaluation, **Pavithra R** abstains from all detection
   query work (she works frontend/demo only) and authors held-out fraud
   scenarios **outside this repo** as scenario overlay files (schema in
   INTERFACES.md §3).
3. She commits only `SHA-256(scenario file)` to `docs/HELDOUT_COMMITMENT.md`,
   with the date.
4. Evaluation (planned 2026-08-09): regenerate the dataset with her overlays
   applied (same base seed), run the frozen detection rules once, record
   results. Then the full scenario files are committed, once.
5. Results — including misses — are reported in PITCH.md and DECISIONS.md.

**What this protocol proves:** the scenarios existed before evaluation (hash
+ git dates), the detection queries were frozen before the scenarios were
written, and neither was tuned against the other afterward. Git history is
the evidence; we can walk a judge through the commits.

**What it does NOT prove — do not overclaim:**
- It does not prove detection generalizes to *real-world* fraud. Everything
  here is synthetic, and the author of the scenarios read DETECTION_SPEC.
  The held-out test measures robustness to *unseen parameterizations and
  structures of known typologies*, not discovery of novel typologies.
- It does not prove the generator is realistic. That defense is separate:
  honest-noise design (§2) and distribution sanity checks.
- Pavithra is one person on the same team, not an independent red team. It is
  a good-faith firewall under hackathon constraints, and we say exactly that.

## 6. Threshold discipline

Rule thresholds and scoring weights are calibrated against the **honest
economy** (false-positive rates on actors with no fraud parameters), not
against planted or emergent fraud labels. This keeps "we tuned until we found
what we hid" off the table.

## 7. Interfaces

Generator CLI, CSV schemas, manifest format, and the scenario overlay schema
are contracts — defined once in [INTERFACES.md](INTERFACES.md) §2–3.

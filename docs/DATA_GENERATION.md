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

**Actors and distributions** (all parameters live in `generator/config.yaml`;
counts below are the seed-42 v1 output — corrected 2026-07-29 after the
first full run exposed arithmetic inconsistencies in the original draft
table, which could not simultaneously satisfy its own per-actor rules):

| population | count (seed 42) | shape |
|---|---|---|
| Patients | ~10,000 (+ a handful of recycled-identity clones from the fraud layer) | one journey each; ~8% return patients |
| Doctors | 1,500 | 1–3 clinic affiliations; specialty fixed |
| Credentials | ~2,230 | 1–2 per doctor; ~3% revoked in the honest world (retirements, discipline) |
| Clinics | 600 | size ~ Zipf: few large hospitals, long tail of day clinics |
| Brokers | 250 | referral share ~ Zipf; commission 5–15% |
| Claims | ~21,700 | the hub population; **each journey yields 1–3 claims** (main procedure + ancillary diagnostics/follow-up) |
| PaymentAccounts | ~2,270 | clinics 1–3, brokers 1–2, plus shells created by the fraud layer |
| Devices | ~12,400 | 1 device each, ~30% a second; honest family sharing |
| Addresses | ~800 | clinics + brokers; some honest co-location |
| Procedures | 116 | catalog across 6 categories; base costs lognormal within category |
| Insurers | 20 | market share ~ Zipf |
| Countries | 15 | 5 treatment + 10 origin |

Total ≈ **51.9k nodes / 191.7k relationships / 7.4 MB** — on the ~50k-node
target and far under the 50 MB budget, measured 2026-07-29.

**Journey model.** A patient picks a category (age/origin-weighted), then a
corridor (gravity), then a clinic (size/quality-weighted within corridor),
gets a doctor of that specialty at that clinic, a procedure from the
category, a price = `base_cost × country_multiplier × lognormal noise`, dates
(procedure, then submission +2–30 days), a payout account of the clinic, and
~65% of journeys an arranging broker. **A journey emits 1–3 claims**: the
main procedure claim plus smaller ancillary claims (5–20% of the main
amount) — this is how ~10k patients produce ~22k claims. Claim narratives
are assembled from templated fragments; the fingerprint is computed from the
assembled text, so honest narratives are similar-but-not-identical.

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

Red-team member: **Pavithra R** (subject to the attestation below).
Amended 2026-07-29 (ADR-016) to tighten isolation.

### Isolation rule (in force from 2026-07-29)

- The red-team member must **not read `docs/DETECTION_SPEC.md`** — nor the
  rule implementations under `detection/` once they exist — at any point
  before the held-out evaluation has been run and its precision/recall
  results committed. At that moment the restriction lifts entirely.
- Scenarios are authored from **PROJECT_BRIEF.md, DATA_MODEL.md, and
  INTERFACES.md only** — the domain, the schema, and the scenario-overlay
  format. She gets no detection logic, thresholds, or typology signatures.
- The restriction covers one document (and its implementations), **not her
  participation**: frontend, console, demo, and pitch work continue
  throughout. Enforcement mechanics live in CONTRIBUTING.md.

### Timeline

1. From 2026-07-29: reading restriction in force.
2. Detection freeze (planned 2026-08-06): DETECTION_SPEC + rules frozen in a
   dedicated commit. From here the red-team member also does no detection
   work of any kind, and the scenario authoring window opens — **outside
   this repo**, as overlay files (schema INTERFACES.md §3).
3. Before evaluation: only `SHA-256(scenario file)` is committed to
   `docs/HELDOUT_COMMITMENT.md`, with the date.
4. Evaluation (planned 2026-08-09): regenerate with the overlays (same base
   seed), run the frozen rules **once**, commit results — including misses —
   to DECISIONS.md and PITCH.md. Then the scenario files are committed.

### Has Pavithra already read DETECTION_SPEC.md?

**Unknown as of 2026-07-29 — and unverifiable from the repository.**
DETECTION_SPEC.md has been in the shared repo since 2026-07-28. Git proves
what was committed when; it cannot prove who has read what. An earlier draft
of this section *assumed* the scenario author would have read the spec and
pre-emptively downgraded the claim — that assumption is withdrawn (ADR-016).
In its place, the protocol starts with a recorded **attestation (OQ #12)**:
at the first team sync after this commit, Pavithra states whether she has
read DETECTION_SPEC.md, and the answer is recorded in DECISIONS.md.

- **She attests she has not read it** → the **strong claim** is available:
  held-out scenarios independently conceived, authored without access to the
  detection logic. Pitch uses the strong language (PITCH.md branch A).
- **She has read it** → the strong claim is gone *for her*. Strongest honest
  alternative: reassign the red-team role to **Vijayalakshmi G**, contingent
  on the same attestation. She is the best-placed substitute — she knows the
  generator and overlay schema more deeply than anyone (more realistic
  scenarios) and her defence area (data generation) does not require the
  detection spec. What she gives up: all detection-rule building, review,
  and threshold-calibration work until 2026-08-09. (Mary Vivitha M is
  excluded as a candidate: detection is her defence area and her build
  assignment — she must read the spec.)
- **No member can attest non-reading** → we own the weaker claim honestly:
  robustness to *unseen parameterizations and structures of known
  typologies*, stated exactly that way in the pitch (PITCH.md branch B). We
  do not manufacture independence that does not exist.

An accidental exposure after attestation (spec content pasted into a channel
the red-team member reads, a review request on a detection PR) does not end
the protocol — it downgrades the claim to branch B and is recorded in
DECISIONS.md. Honesty about a leak beats silence about one.

### What the protocol proves (strong branch)

The scenarios were conceived without access to the detection logic, existed
before evaluation (hash + git dates), the rules were frozen before the
scenarios were hashed, and neither side was tuned against the other. Git
history is the evidence; we can walk a judge through the commits.

### What it does NOT prove — do not overclaim, in either branch

- Not real-world generalization: everything here is synthetic.
- Not generator realism: that defense is separate — honest-noise design (§2)
  and distribution sanity checks.
- Not full independence: the red-team member is one person on the same team,
  and both sides share DATA_MODEL and INTERFACES (the schema itself hints at
  what *could* be detected, even with the spec unread). It is a good-faith
  firewall under hackathon constraints, and we say exactly that.

## 6. Threshold discipline

Rule thresholds and scoring weights are calibrated against the **honest
economy** (false-positive rates on actors with no fraud parameters), not
against planted or emergent fraud labels. This keeps "we tuned until we found
what we hid" off the table.

## 7. Interfaces

Generator CLI, CSV schemas, manifest format, and the scenario overlay schema
are contracts — defined once in [INTERFACES.md](INTERFACES.md) §2–3.

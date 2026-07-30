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
| Devices | ~12,400 | 1 device each, ~30% a second; **every owned device carries a USED_DEVICE window** (claim-usage dates, or a dormant pre-journey registration window — ADR-022); ~560 devices shared by >1 patient at seed 42, overwhelmingly honest family sharing |
| Addresses | ~800 | clinics + brokers; some honest co-location |
| Procedures | 116 | catalog across 6 categories; base costs lognormal within category |
| Insurers | 20 | market share ~ Zipf |
| Countries | 15 | 5 treatment + 10 origin |

Total = **51,990 nodes / 197,251 relationships / 7.6 MB** — on the
~50k-node target and far under the 50 MB budget, measured 2026-07-30 at
the dataset freeze (ADR-031: planted cells + parallel recycling included;
the earlier 51.1k/193.7k dataset is a byte-identical subset).

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
partnerships, and ~10% of brokers holding a *declared* stake in a local
clinic (`OWNS_STAKE_IN` — the honest majority that keeps the edge from
being a fraud label, ADR-023) — the honest world must contain *weak*
versions of every fraud signal, or detection is trivially easy and the
judges will see it.

## 3. EMERGENT fraud (behavioural)

No entity is labeled "fraudulent." Instead, a small fraction of actors get
*incentive parameters* drawn at generation time, and fraud **emerges from
their local decision rules interacting**:

- `overbilling_propensity` (clinics, ~5% get >0): inflates amounts and
  line-item counts by a drawn factor on a drawn fraction of claims.
- `steering_greed` (brokers, ~6% get >0): routing probability skews toward
  clinics that pay a side commission; the side payments materialize as
  `TRANSFERRED` clinic-account → broker-account flows, and about half of
  steering partnerships also carry a *hidden* `OWNS_STAKE_IN` stake in the
  partner clinic (deduped against declared holdings — ADR-023). When a
  greedy broker meets a paying clinic, a kickback ring *emerges* — we never
  place a ring.
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

**Rewritten 2026-07-30 (ADR-027): the project is now built by one person
(J Don Gabriel). Person-separation — a red-team member who never read the
detection spec — is no longer possible. The protocol below replaces it with
TEMPORAL separation, which one person can still execute and git can still
prove.** The earlier person-separation protocol (ADR-012/016, the Pavithra
attestation branches) is retired; its history stays in DECISIONS.md.

### The temporal-separation protocol (executed 2026-07-30)

1. **Scenarios first.** On 2026-07-30 — before a single detection query,
   rule file, or threshold existed anywhere in this repository — the
   implementer authored five held-out fraud scenarios as generator overlay
   files (schema INTERFACES §3), consulting only PROJECT_BRIEF.md,
   DATA_MODEL.md, INTERFACES.md, and GLOSSARY.md during the authoring
   session. DETECTION_SPEC.md was not opened during that session.
2. **Stored outside the repository** (`C:\WorkSpace\Private\medgraph-heldout\`
   on the build machine), so no later commit can quietly revise them.
3. **Hash-committed the same day:** SHA-256 of each file's exact bytes went
   into `docs/HELDOUT_COMMITMENT.md` in its own commit, before any detection
   work started. Any later edit to a scenario file changes its hash and
   voids the commitment.
4. **Not reopened until evaluation.** The files stay closed while detection
   is built (M3), calibrated on the honest economy only (§6), and frozen
   (Aug 6, dedicated commit).
5. **Evaluated once** (planned Aug 9): regenerate with the overlays (same
   base seed) into a separate data dir, run the frozen rules **once**,
   commit precision/recall — including misses — to DECISIONS.md and
   PITCH.md. Only then are the scenario files themselves committed to
   `data/scenarios/heldout/`, where anyone can re-hash them.

### What this proves — and what it does not. Do not overclaim.

**It proves ordering, not independence.** Git history proves: the scenarios
existed (hash + commit date) before any detection query was written; the
rules were frozen before the scenarios were reopened; the scenarios were
evaluated once and not iterated against; the rules were not re-tuned after
seeing held-out results. That kills the specific accusation "you tuned your
rules until they found your test set, or wrote your test set to match your
rules — after the fact."

**It cannot prove the two sides were independently conceived — the same
person conceived both.** The scenario author designed the data model, wrote
DETECTION_SPEC's typology descriptions in the planning phase, and later
wrote the rules. No git mechanism can separate what one brain knew. We do
not pretend otherwise, anywhere, ever.

Also still true (unchanged from the original protocol): this is not
real-world generalization (everything is synthetic), and it is not the
generator-realism defense (that's §2 honest noise + distribution checks).

### The exact pitch wording (use this, not something stronger)

> "I built this alone, so I can't offer you author independence — the same
> person wrote the fraud scenarios and the detection rules. What I can
> offer is provable ordering. On July 30th, before a single detection query
> existed in this repository, I wrote five held-out fraud scenarios, stored
> them outside the repo, and committed their SHA-256 hashes — you can read
> that commit in the history. The rules were written afterwards, calibrated
> only on the honest economy, frozen on August 6th, and run against those
> scenarios exactly once, on August 9th. So the history proves the test set
> wasn't written to match the rules and the rules weren't tuned against the
> test set. What it cannot prove is that one brain didn't unconsciously
> author detectable scenarios — it's a discipline claim, not an
> independence claim. Here are the results, including what we missed."

### Session discipline (replaces the red-team reading rule)

Between 2026-07-30 and the evaluation: do not open, paste, or summarize the
held-out files in any working session, including AI-assisted sessions — a
session that has the scenarios in context while writing detection code
destroys the ordering claim's spirit even though the hashes still hold.
Scenario-overlay *tooling* in the generator is built against the INTERFACES
§3 schema and the committed example scenarios in `data/scenarios/` (non-
held-out fixtures), never against the held-out files themselves.

## 6. Threshold discipline

Rule thresholds and scoring weights are calibrated against the **honest
economy** (false-positive rates on actors with no fraud parameters), not
against planted or emergent fraud labels. This keeps "we tuned until we found
what we hid" off the table.

## 7. Interfaces

Generator CLI, CSV schemas, manifest format, and the scenario overlay schema
are contracts — defined once in [INTERFACES.md](INTERFACES.md) §2–3.

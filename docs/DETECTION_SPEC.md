# Detection Specification

> **Scope status (2026-07-30, ADR-024):** typologies **1, 2, 3 and 5 ship**.
> Typologies **4 and 6 are descoped** — the ADR-017 cut ladder was executed
> when capacity collapsed to one shared machine (~110–130 h). Their sections
> below are kept in full, deliberately: they are the specified,
> FP-mode-documented **"what we would build next"** — a pitch and Day-2
> asset, not a gap. Generator-output consequences:
> `narrative_fingerprint` (claims.csv) is now **unused by any shipping
> typology** — it still ships in the data as the ready substrate for
> typology 4. `OWNS_STAKE_IN` and `TRANSFERRED` remain **in use** by
> shipping typology 3 (shared-infrastructure signature) — descoping 6 does
> not orphan them.

Each typology below: the real-world behaviour, its graph signature, the
detection approach, the inputs it needs, and — critically — the ways it
produces **false positives**. Being able to explain the FP modes is what
separates "we detect fraud" from "we understand fraud detection."

**Freeze protocol:** this document is frozen in its own commit on the date
recorded in DECISIONS.md (planned 2026-08-06). After the freeze, held-out
scenarios are authored against it (see DATA_GENERATION.md §5). Changes after
the freeze require a new ADR and invalidate the held-out evaluation.

## Architecture: rules as a registry

Every typology is a **registry entry**, not a bespoke code path:

- Metadata (`detection/rules/<key>.yaml`, build phase): rule key, name,
  typology number, version, tunable parameters with defaults, severity bands.
- Implementation: either a parameterized Cypher query file or a Python
  function that orchestrates GDS calls. Both consume parameters from the
  metadata and emit alerts conforming to the Alert schema (DATA_MODEL.md).
- A detection *run* executes selected rules and writes `Alert` nodes with
  `IMPLICATES` edges. Runs are idempotent per rule+version (previous alerts
  from the same rule+version are replaced).

This is the Day-2 lever: a seventh typology is a new YAML file plus a query —
no API or frontend change (ADR-008).

Verified against Neo4j GDS 2.13 docs (2026-07-28): Louvain, Betweenness
Centrality, and Weakly Connected Components are production-tier in open-source
GDS (`gds.louvain.*`, `gds.betweenness.*`, `gds.wcc.*`); PageRank likewise.
Exact procedure signatures are re-checked against the pinned GDS docs when
each query is written — do not write GDS calls from memory.

## Scoring

Each rule computes a raw score from its features, normalized to 0–100.
Severity bands: `high` ≥ 80, `medium` ≥ 50, else `low`. Normalization and
threshold calibration method is OPEN_QUESTIONS #4 — thresholds get tuned on
the base economy (not on planted fraud) to keep the circularity defense clean.

---

## 1. Ghost clinic

**Real-world behaviour.** A clinic that exists on paper — registration,
address, bank account — bills insurers for procedures never performed.
Patients are recruited or invented by a cooperating broker; payouts
concentrate into one account.

**Graph signature.**
- High claim volume relative to physical footprint (`bed_count` 0 or tiny,
  short `registration_date` history).
- Address shared with many other entities (registered-office farms).
- Inflow dominance: a single broker arranges ≥ ~80% of the clinic's claims.
- Outflow dominance: ≥ ~90% of payouts land in a single `PaymentAccount`.
- Few distinct doctors relative to claim volume; patients rarely file again.

**Approach.** Cypher feature extraction per clinic → weighted score. Louvain
community detection (GDS, on the claim-participation projection) provides ring
context: ghost clinics cluster with their feeder brokers and accounts, and the
community ID is attached as evidence. This rule is *scored*, not binary.

**Inputs.** Claims with `AT_CLINIC`, `ARRANGED_BY`, `PAID_TO`; clinic
properties; `LOCATED_AT`/`OPERATES_FROM` address sharing; Louvain community
assignments.

**False-positive modes.**
- A legitimate new single-specialty day clinic (bed_count 0) with an exclusive
  referral partnership — structurally similar inflow dominance.
- Small clinics genuinely using one corporate bank account.
- Registered-office sharing is common for legal domicile in some countries.
Mitigation: score is multi-feature; single-feature hits stay below `medium`.

---

## 2. Credential laundering

**Real-world behaviour.** A revoked or fabricated licence keeps earning: one
real licence number is reused across multiple practitioner identities or
jurisdictions, or a doctor continues billing after revocation.

**Graph signature.**
- One `license_no` value on Credential nodes held by >1 distinct Doctor.
- Claims `PERFORMED_BY` a doctor whose credential has
  `status = 'revoked'` and `procedure_date > revocation_date`.
- Credential `ISSUED_IN` a country where the doctor has no practice, while
  claims occur in 2+ other countries (jurisdiction shopping).

**Approach.** Targeted Cypher (three sub-queries, one rule). Exact matches,
near-binary confidence — post-revocation billing starts at `high`.

**Inputs.** `HOLDS`, `ISSUED_IN`, `PERFORMED_BY`, credential status/dates,
the non-unique `cred_license_no` index.

**False-positive modes.**
- Licence-number format collisions across *different* issuing bodies (two
  countries can both issue "MC-4471"). Guard: same-number hits require the
  same `issuing_body` or same issuing country.
- Administrative re-registration: the same real doctor re-registered under a
  corrected name spelling (entity-resolution gap, very real in production).
- Revocation-date data entry lag: claim legitimately performed days before
  revocation but recorded after.

---

## 3. Kickback ring

**Real-world behaviour.** A broker steers disproportionate patient volume to
clinics that pay for referrals — hidden ownership or shared banking closes
the loop. Patients may receive real (possibly unnecessary) treatment, which
is why per-claim review never flags it.

**Graph signature.**
- Mutual concentration: broker→clinic share of the clinic's claims high AND
  clinic share of the broker's referrals high (both directions matter — a big
  broker dominating a tiny clinic is normal one way, suspicious both ways).
- Shared infrastructure: `OWNS_STAKE_IN`, common `OWNED_BY` accounts,
  `TRANSFERRED` flows broker↔clinic accounts, shared addresses.
- Dense Louvain communities of broker+clinics+accounts provide ring context.
- *(Amended 2026-07-30, ADR-028: PageRank/betweenness hub-ranking was
  benchmarked against emergent ground truth and dropped — steering is a
  concentration pattern, not a bridging one; global centrality ranked the
  true steering brokers WORSE than a one-line concentration share, at up to
  10⁶× the compute. Measurements:
  `detection/benchmarks/typology3_centrality.md`.)*

**Approach.** Cypher concentration features per broker–clinic pair
(top-clinic share and both mutual-concentration directions) gate the
candidates; shared-infrastructure evidence (stake, common accounts,
transfers, shared address) and Louvain community context complete the
score. Score combines concentration, infrastructure overlap, and community
density — no global centrality term (ADR-028).

**Inputs.** `ARRANGED_BY`, `AT_CLINIC`, `OWNS_STAKE_IN`, `OWNED_BY`,
`TRANSFERRED`, addresses; GDS projections.

**False-positive modes.**
- Legitimate exclusive partnerships: a hospital group with an in-house
  facilitation arm looks exactly like mutual concentration + shared ownership
  — except the ownership is declared. `accreditation_status` and declared
  stake soften the score.
- Geographic monopolies: the only broker and only clinic in a small corridor
  concentrate on each other with no wrongdoing.

---

## 4. Template cloning — DESCOPED (ADR-024; not built)

*Descoped 2026-07-30: highest algorithmic risk (fingerprint-distance tuning,
OQ #3) and the most calibration time, against a collapsed hour budget. Kept
specified as the first thing we would build next — the data
(`narrative_fingerprint` on every claim) already supports it.*

**Real-world behaviour.** A claim mill perfects one claim package — narrative,
line items, cost breakdown — and resubmits it across many patients, sometimes
across insurers, with names swapped.

**Graph signature.**
- Claims from *unrelated* patients with near-identical
  `narrative_fingerprint` (small Hamming distance), same `line_item_count`,
  amounts within a tight band, same procedure.
- Cloned claims often share submission devices (`USED_DEVICE`) or brokers.

**Approach.** Candidate blocking in Cypher (same procedure + line_item_count,
amount band, fingerprint index), then pairwise fingerprint distance in the
Python rule implementation; clusters of ≥3 mutually-similar claims become one
alert implicating all claims in the cluster. GDS Node Similarity (Jaccard) is
the fallback approach if fingerprint clustering proves weak — decision is
OPEN_QUESTIONS #3.

**Inputs.** Claim fingerprints/amounts, `FOR_PROCEDURE`, `FOR_PATIENT`,
`USED_DEVICE`, `ARRANGED_BY`.

**False-positive modes.**
- **Legitimately standardized packages** — the big one. LASIK, standard
  dental implants, routine health-check packages produce genuinely
  near-identical narratives and prices across unrelated patients. Guard:
  cross-*insurer* cloning and shared devices raise the score; same-clinic
  standardized packages alone cap at `low`.
- Templated hospital billing software producing similar narratives.

---

## 5. Impossible travel

**Real-world behaviour.** One identity is billed for treatment in two
countries within a window shorter than physical travel allows — or one
passport number backs multiple patient identities across insurers.

**Graph signature.**
- Same Patient (or Patients sharing `passport_no`) with claims whose
  `procedure_date`s in different treatment countries are closer than the
  minimum corridor travel time (static lookup table, in hours, checked into
  the generator config and shared with this rule).
- Multi-day procedures (surgery + recovery) tighten the bound: you cannot be
  discharged in Chennai and on the table in Istanbul the same afternoon.

**Approach.** Targeted Cypher: per patient/passport, order claims by date,
compare consecutive pairs across countries against the travel-time table.
Held out or not, this rule was designed from the spec only — see
DATA_GENERATION §5.

**Inputs.** `FOR_PATIENT`, claims dates, clinic country (via
`AT_CLINIC`→`LOCATED_AT`→`IN_COUNTRY`), `patient_passport` index, travel-time
table.

**False-positive modes.**
- Date-granularity artifacts: we store dates, not times; same-day claims in
  two nearby countries (Dubai→Singapore is ~7h) may be physically possible.
  Guard: the table works in whole days and flags only clearly impossible
  pairs.
- Family members using one passport field through data-entry error —
  common in the real world, indistinguishable in-graph from identity reuse
  (honest answer: this rule *finds* the record problem either way; an
  investigator decides).
- Pre-booked package dates recorded as procedure dates.

---

## 6. Circular payment — DESCOPED (ADR-024; not built)

*Descoped 2026-07-30: bounded Cypher work, but the least demo-critical of the
six against a collapsed hour budget. Kept specified as next-build — the data
(`TRANSFERRED` flows, shell accounts) already supports it, and typology 3
still uses those same edges.*

**Real-world behaviour.** Money leaves a clinic's account and returns to it
(or its broker's) through one or more shell accounts — laundering kickbacks
or recycling payouts to simulate legitimate turnover.

**Graph signature.**
- A directed cycle in `TRANSFERRED` edges of length 2–5 that starts and ends
  at accounts owned by the same clinic/broker cluster, within a ~90-day
  window, with 5–20% amount attrition per hop.
- Intermediate hops through **shell accounts** (no `OWNED_BY` edge).

**Approach.** Bounded variable-length Cypher path query over `TRANSFERRED`
(length ≤ 5), filtered on date monotonicity and amount attrition; cycles
scored by length, shell count, and total value. Cycle *candidates* are cheap
at our scale; the filters do the work.

**Inputs.** `TRANSFERRED` (amount, date), `OWNED_BY`, shell-account absence.

**False-positive modes.**
- Refunds and settlements: clinic refunds a broker commission, broker later
  pays the clinic for a new referral — a legitimate 2-cycle. Guard: 2-cycles
  need amount similarity + short window to score above `low`.
- Corporate treasury sweeps inside one honestly-owned group.
- Netting arrangements between frequent counterparties.

---

## Evaluation

Detection quality is reported as precision/recall against (a) planted-fraud
ground truth and (b) the held-out scenarios, exactly once, after the freeze —
protocol and honest limits in DATA_GENERATION.md §5–6. Numbers, including
misses, go into PITCH.md and DECISIONS.md. The evaluation covers the four
shipping typologies only (ADR-024).

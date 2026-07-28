# Held-Out Scenario Commitment

Cryptographic commitment record for the held-out evaluation protocol
(DATA_GENERATION §5, ADR-012). This file is intentionally created *before*
any scenario exists, so its own git history shows the protocol preceded the
scenarios.

## Protocol summary

0. From 2026-07-29 (ADR-016), the red-team member — **Pavithra R**, pending
   the OQ #12 attestation — does not read DETECTION_SPEC.md or the
   `detection/` rule implementations. Scenarios are authored from
   PROJECT_BRIEF.md, DATA_MODEL.md, and INTERFACES.md only. The restriction
   lifts when the evaluation results are committed.
1. DETECTION_SPEC.md freezes in a dedicated commit (planned 2026-08-06).
2. From that commit until evaluation, the red-team member additionally does
   no detection work of any kind. She authors held-out fraud scenarios as
   generator overlay files (schema: INTERFACES.md §3) **outside this
   repository**.
3. For each scenario file she computes `SHA-256` of the exact file bytes and
   appends a row below, in its own commit, before evaluation.
4. Evaluation (planned 2026-08-09) runs the frozen rules once against a
   regeneration that includes the overlays. Results go to DECISIONS.md and
   PITCH.md, including misses.
5. Only after the evaluation run are the scenario files themselves committed
   to `data/scenarios/heldout/`, where anyone can re-hash them against the
   rows below.

To verify (PowerShell): `Get-FileHash -Algorithm SHA256 <file>` — compare
against the committed hash and the commit dates.

## Commitments

| date committed | scenario name | SHA-256 (file bytes) |
|---|---|---|
| _(none yet — window opens at the detection freeze)_ | | |

## What this does and does not prove

Proves: the scenarios existed before the evaluation ran, and the detection
queries were frozen before the scenarios were written — neither side was
tuned against the other after the fact. If the OQ #12 attestation succeeded,
it additionally supports the claim that the scenarios were conceived without
access to the detection logic. Does **not** prove: real-world
generalization, generator realism, or full independence (one team, shared
schema docs). The claim branch actually available — strong vs.
unseen-parameterizations — is determined by the recorded attestation; full
honesty notes and branch logic: DATA_GENERATION §5. Say the limits in the
pitch before the jury asks.

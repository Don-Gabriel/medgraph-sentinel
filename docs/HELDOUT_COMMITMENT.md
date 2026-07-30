# Held-Out Scenario Commitment

Cryptographic commitment record for the held-out evaluation protocol
(DATA_GENERATION §5, ADR-027). This file was created *before* any scenario
existed, so its own git history shows the protocol preceded the scenarios.

**Protocol basis changed 2026-07-30 (ADR-027):** the project is built by one
person, so the original person-separation protocol (a red-team member who
never read the detection spec — ADR-012/016) is impossible. The protocol is
now **temporal separation**: the same implementer authored the scenarios
*before any detection query existed*, hash-committed them, and does not
reopen them until the one-shot evaluation.

## Protocol summary

1. 2026-07-30: five held-out scenarios authored as generator overlay files
   (schema INTERFACES §3), consulting only PROJECT_BRIEF.md, DATA_MODEL.md,
   INTERFACES.md, and GLOSSARY.md during the authoring session —
   DETECTION_SPEC.md not opened, no detection query yet in existence
   anywhere in the repository (verifiable: `detection/` contains only
   scaffolding at the commit that adds the hashes below).
2. The scenario files live **outside this repository** on the build machine
   and are not opened again until evaluation.
3. SHA-256 of each file's exact bytes is committed below, in its own
   commit, before any detection work starts.
4. Detection is then built, calibrated on the honest economy only
   (DATA_GENERATION §6), and frozen (planned 2026-08-06, dedicated commit).
5. Evaluation (planned 2026-08-09): regenerate with the overlays into a
   separate data dir, run the frozen rules **once**, commit results —
   including misses — to DECISIONS.md and PITCH.md.
6. Only after the evaluation are the scenario files committed to
   `data/scenarios/heldout/`, where anyone can re-hash them against the
   rows below.

To verify (PowerShell): `Get-FileHash -Algorithm SHA256 <file>` — compare
against the committed hash and the commit dates.

## Commitments

| date committed | scenario name | SHA-256 (file bytes) |
|---|---|---|
| 2026-07-30 | heldout_S1_ghost_satellite.yaml | `24fb689de10b7e9bb1ea27d7907693c52c52860074e3ebc275816b0e1ce1dc07` |
| 2026-07-30 | heldout_S2_license_shadow.yaml | `3db0333afbc878a4191706c54763986a843ce0b0c00b0cf14e1f21dcadf00bde` |
| 2026-07-30 | heldout_S3_quiet_kickback.yaml | `fe9df9dfb33f6aabd8dd90cc623afd673e4e12a69fcc8dd38205c7ac78a28850` |
| 2026-07-30 | heldout_S4_split_ledger.yaml | `eab10c37d0be1b43b3ecc59433302055502242efdc88c0fb199a93d2469af339` |
| 2026-07-30 | heldout_S5_confluence.yaml | `828e5d64c56d6274db5b0840249045ca8c9f551bb4797a8772cf41ec698b3d0c` |

## Pre-registration (2026-07-30, before the evaluation ran)

Committed and pushed BEFORE the sealed scenarios were injected or any
held-out detection run occurred, replacing the calendar guard (the
planned Aug 9 date) with a stronger, permanent one:

1. **No detection rule, threshold, parameter, or generator setting will
   change based on the held-out results.** The rules as of this commit
   are final for the evaluation and for the demo.
2. **Results are reported exactly as they land, including misses**, in
   DECISIONS.md, PITCH.md and the README. A missed scenario is explained
   structurally, never patched.
3. The evaluation runs **once**, into a separate data directory; the
   frozen demo artifacts (`data/`, ADR-031) are never touched.
4. The scenario files are committed to `data/scenarios/heldout/`
   immediately after the run, so anyone can re-hash them against the
   table above and re-run the evaluation themselves.

Rationale: the hash rows + git history already fix the ORDERING claim
permanently (scenarios predate every detection query — commit `290101e`
vs the detection tree). The Aug 9 date only ever guarded against tuning
after seeing results; this pre-registration guards that directly and
verifiably, and the calendar date is retired.

## Evaluation record (2026-07-30)

Executed the same evening as the pre-registration above, in order:
hashes re-verified (all five match the table) → injected into a separate
data dir → frozen rules run once → results committed verbatim (ADR-034:
leg recall 5/8, two structural misses explained in PITCH.md) → scenario
files committed to `data/scenarios/heldout/`, where `Get-FileHash
-Algorithm SHA256` reproduces the rows above.

## What this does and does not prove

**Proves ordering:** the scenarios existed before any detection query was
written (this file's hash-row commit predates all detection commits), the
rules were frozen before the scenarios were reopened, and neither side was
revised against the other afterwards — the hashes pin the exact bytes.

**Does not prove independence:** the same person conceived the scenarios,
the data model, and (later) the detection rules. No hash can separate what
one brain knew. It also does not prove real-world generalization or
generator realism — those are separate defenses (DATA_GENERATION §2).
The pitch states these limits unprompted; the exact wording lives in
DATA_GENERATION §5.

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
| _(hash rows are added in their own dedicated commit)_ | | |

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

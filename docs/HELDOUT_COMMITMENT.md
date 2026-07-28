# Held-Out Scenario Commitment

Cryptographic commitment record for the held-out evaluation protocol
(DATA_GENERATION §5, ADR-012). This file is intentionally created *before*
any scenario exists, so its own git history shows the protocol preceded the
scenarios.

## Protocol summary

1. DETECTION_SPEC.md freezes in a dedicated commit (planned 2026-08-06).
2. From that commit until evaluation, **Pavithra R** does no detection-query
   work. She authors held-out fraud scenarios as generator overlay files
   (schema: INTERFACES.md §3) **outside this repository**.
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
tuned against the other after the fact. Does **not** prove: real-world
generalization, generator realism, or independence of the scenario author
from the detection spec (she read it; the test measures robustness to unseen
parameterizations of known typologies). Full honesty notes:
DATA_GENERATION §5. Say the limits in the pitch before the jury asks.

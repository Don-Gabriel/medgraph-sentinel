# detection/

> ⛔ **Held-out discipline (ADR-027):** everything in this directory
> postdates the held-out hash commit in docs/HELDOUT_COMMITMENT.md
> (2026-07-30) — that ordering is the circularity defense. Sessions
> working here must never open the off-repo held-out scenario files
> before the one-shot evaluation.

The rule registry and batch runner. Each typology is a registry entry:
`rules/<key>.yaml` (metadata, params, severity bands) plus a Cypher query
file or Python module. `python -m detection.run` executes selected rules and
writes `Alert` nodes + `IMPLICATES` edges into the graph, idempotently per
rule+version. `python -m detection.export` writes the resulting alerts to
committed CSVs for the demo build (ADR-029) — compose-up loads alerts, it
never computes them.

Contracts: [docs/INTERFACES.md](../docs/INTERFACES.md) §5,
[docs/DETECTION_SPEC.md](../docs/DETECTION_SPEC.md) (freezes Aug 6).
Thresholds are calibrated on the honest economy only — never on fraud
labels, and nothing here may read `data/ground_truth/`.

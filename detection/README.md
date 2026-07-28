# detection/

> ⛔ **Red-team member: do not read anything in this directory** (currently
> Pavithra R — ADR-016, CLAUDE.md session protocol step 7). The restriction
> lifts when the held-out evaluation results are committed.

The rule registry and batch runner. Each typology is a registry entry:
`rules/<key>.yaml` (metadata, params, severity bands) plus a Cypher query
file or Python module. `python -m detection.run` executes selected rules and
writes `Alert` nodes + `IMPLICATES` edges into the graph, idempotently per
rule+version.

Contracts: [docs/INTERFACES.md](../docs/INTERFACES.md) §5,
[docs/DETECTION_SPEC.md](../docs/DETECTION_SPEC.md) (freezes Aug 6).
Currently: runner stub that reports zero rules (M3 builds the six rules).
Thresholds are calibrated on the honest economy only — never on fraud
labels, and nothing here may read `data/ground_truth/`.

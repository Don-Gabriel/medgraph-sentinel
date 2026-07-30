# detection/rules/

One YAML per typology (registry entry) + its implementation. Registry
format: docs/INTERFACES.md §5. Frozen Aug 6.

```yaml
key: ghost_clinic          # must equal the filename stem
name: Ghost clinic
typology: 1
version: "1.0"             # quoted string; bumping it replaces prior alerts
kind: python               # python | cypher
impl: detection.rules.impl.ghost_clinic   # module path (python)
                           # or a .cypher path relative to this directory
params: { ... }            # every tunable threshold lives HERE, not in code
severity_bands: { high: 80, medium: 50 }  # score >= high/medium, else low
```

Implementations return **alert drafts** — the runner owns deletion, ID
assignment, the 200-entity implicated cap, severity banding, and writes:

- `kind: python` — module with `run(session, params) -> list[draft]`.
- `kind: cypher` — a parameterized query returning one row per alert with
  columns `anchor_id`, `score`, `summary_params` (map), `implicated`
  (list of `{id, role}` maps). The path is exercised by a live smoke test
  and unit tests; all four shipping rules are Python for explainability.

Draft shape: `{"anchor_id": str, "score": float 0-100, "summary_params":
dict, "implicated": [{"id": entity_id, "role": str}, ...]}`.

`IMPLICATES.role` values used by the shipping rules (DATA_MODEL examples):
`ghost_clinic`, `feeder_broker`, `hub_account`, `shared_address`,
`suspect_claim` · `shared_license`, `license_holder`, `suspect_doctor`,
`revoked_credential`, `post_revocation_claim`, `shopped_credential`,
`cross_border_claim` · `kickback_broker`, `partner_clinic`,
`shared_account`, `ring_account`, `shell_account`, `steered_claim` ·
`recycled_identity`, `traveling_patient`, `conflicting_claim`.

Thresholds are calibrated on the honest economy only (DATA_GENERATION §6);
the measured calibration record is in ../README.md. `impl/common.py` holds
the shared `scale()` ramp and the deterministic Louvain helper (GDS calls
verified live against 2.13.11 via `gds.list` on 2026-07-30).

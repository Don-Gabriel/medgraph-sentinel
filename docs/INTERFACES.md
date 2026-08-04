# Interfaces — The Module Contracts

**This is the most important file in the repository.** Roles are fluid: any of
the five of us may touch any module on any evening. These contracts are what
let that happen without collisions. Work *behind* a contract freely; change a
*contract* only via the change protocol at the bottom.

Modules and data flow:

```
generator ──CSV──▶ loader ──▶ Neo4j ◀── detection runner (writes Alerts)
                               ▲  ▲
                               │  └── narration builder (reads Alerts, writes cache)
                               │
                             FastAPI ──JSON──▶ React console
```

Ports (defaults, overridable via .env): Neo4j 7474 (HTTP) / 7687 (Bolt),
API 8000, frontend 5173.

---

## 1. Environment variables

Single source of truth: `.env` (never committed) documented by `.env.example`.

| variable | consumer | meaning |
|---|---|---|
| `NEO4J_PASSWORD` | neo4j, loader, detection, api | required, no default |
| `NEO4J_URI` | loader, detection, api | default `bolt://localhost:7687` (inside compose: `bolt://neo4j:7687`) |
| `NEO4J_USER` | same | default `neo4j` |
| `NEO4J_HEAP_SIZE` | neo4j container | `2G` (8 GB profile) / `4G` (16 GB+ profile) |
| `NEO4J_PAGECACHE_SIZE` | neo4j container | `1G` / `2G` per profile |
| `GENERATOR_SEED` | generator | default `42`; committed dataset is generated with 42 |
| ~~`ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`~~ | — | **retired (ADR-032):** narration is pre-generated committed data; no API calls exist anywhere |
| `NARRATION_LIVE` | api | **ADR-037 (branch):** default unset/false = frozen behaviour (zero network). `true` + a key = opt-in live Gemini tier ahead of the cache |
| `GEMINI_API_KEY` | api | **ADR-037 (branch):** Google AI Studio key for the live tier; only ever in `.env` |
| `GEMINI_MODEL` | api | **ADR-037 (branch):** optional override of the default model in `api/narration/live.py` |
| `API_PORT`, `FRONTEND_PORT` | compose | defaults 8000 / 5173 |
| `VITE_API_BASE_URL` | frontend build | default `http://localhost:8000` |

Memory profiles (Q2): 8 GB machine → 2G heap / 1G pagecache. 16 GB+ machine →
4G / 2G. Check your RAM: `wmic ComputerSystem get TotalPhysicalMemory`
(Windows) or `free -h` (Linux/WSL). The 8 GB profile must always work.

---

## 2. Generator → data files

Output directory: `data/csv/` (committed) + `data/manifest.json`.
CLI (build phase): `python -m generator --seed 42 --out data/ [--scenario file.yaml ...]`

**Determinism contract:** same seed + config + scenario set ⇒ byte-identical
output. No timestamps or unseeded randomness in any generated file.

**CSV conventions:** UTF-8, header row, `\n` line endings, RFC 4180 quoting.
Empty string = null. Dates `YYYY-MM-DD`. Floats with `.` decimal, max 2dp for
money.

### Node files — one per label

| file | columns (in order) |
|---|---|
| `patients.csv` | id, full_name, dob, gender, passport_no |
| `doctors.csv` | id, full_name, specialty |
| `clinics.csv` | id, name, bed_count, registration_date, accreditation_status |
| `brokers.csv` | id, name, agency_name |
| `claims.csv` | id, amount_usd, procedure_date, submission_date, status, line_item_count, narrative_fingerprint |
| `credentials.csv` | id, license_no, issuing_body, issue_date, status, revocation_date |
| `payment_accounts.csv` | id, account_ref, bank_name, opened_date |
| `devices.csv` | id, device_hash, device_type |
| `addresses.csv` | id, street, city, postcode |
| `procedures.csv` | id, code, category, name, base_cost_usd |
| `insurers.csv` | id, name |
| `countries.csv` | code, name, role, cost_multiplier |

### Relationship files — one per type, named `rel_<type>.csv`

All have `source_id,target_id` first, then edge properties in the order shown
(matching DATA_MODEL.md):

| file | extra columns |
|---|---|
| `rel_resides_in.csv` | — |
| `rel_used_device.csv` | first_seen, last_seen |
| `rel_for_patient.csv` | — |
| `rel_at_clinic.csv` | — |
| `rel_performed_by.csv` | — |
| `rel_for_procedure.csv` | — |
| `rel_billed_to.csv` | — |
| `rel_arranged_by.csv` | commission_pct |
| `rel_paid_to.csv` | — |
| `rel_holds.csv` | — |
| `rel_issued_in.csv` | — |
| `rel_practises_at.csv` | since |
| `rel_located_at.csv` | — |
| `rel_operates_from.csv` | — |
| `rel_in_country.csv` | — |
| `rel_owned_by.csv` | — |
| `rel_owns_stake_in.csv` | pct |
| `rel_transferred.csv` | amount_usd, date |
| `rel_based_in.csv` | — |

### `data/manifest.json`

```json
{
  "generator_version": "1.0.0",
  "seed": 42,
  "config_sha256": "<hash of generator/config.yaml>",
  "scenarios_applied": [],
  "counts": {"patients": 10008, "claims": 21622, "rel_for_patient": 21622}
}
```
`counts` has one entry per CSV file (basename without extension). No
timestamp field, by design.

*Two files in `data/csv/` are NOT generator output:* `alerts.csv` and
`rel_implicates.csv` are written by the detection export (§5, ADR-029)
during the demo build; the export adds their counts to the manifest and
the loader loads them like any other file when the manifest lists them.
Regenerating the dataset rewrites the manifest without those entries —
which is correct: alerts for the old graph are meaningless against a new
one, and the ADR-018 chain re-runs from the top.

### `data/ground_truth/` (committed; read by evaluation ONLY)

- `actor_params.csv`: `actor_id, param_name, value` — emergent-fraud
  incentive parameters (empty value rows are not written; absence = honest).
- `planted.csv`: `entity_id, cell_id, typology` — planted-cell membership.

**Contract: no code under `detection/`, `api/`, or `frontend/` may read
`data/ground_truth/`.** Only the evaluation script may. PR reviewers enforce.

---

## 3. Scenario overlay schema (held-out + planted injection)

YAML consumed by the generator's `--scenario` flag. This schema is what makes
held-out injection possible without code changes — it must be expressive
enough *before* the freeze.

```yaml
scenario: string            # unique name, e.g. "heldout_A"
description: string
actors:                     # new actors to create (IDs auto-assigned with
  - kind: clinic            #   a scenario-reserved ID range)
    ref: c1                 # local reference within this file
    props: {bed_count: 0, accreditation_status: none,
            country: TH}    # optional country pin (ISO code): generator
                            #   materializes address + IN_COUNTRY/OPERATES_FROM
  - kind: broker
    ref: b1
    params: {steering_greed: 0.9}     # may set emergent incentive params
  - kind: doctor            # doctor/credential kinds: needed to express
    ref: d1                 #   credential-typology scenarios (2026-07-30)
    props: {specialty: dental}
  - kind: credential
    ref: cr1
    props: {license_no: "MC-TR-88231", issuing_body: "Medical Council of X",
            issue_date: 2016-03-12, status: revoked,
            revocation_date: 2025-12-15}
  - kind: patients          # a named pool of `count` patient identities,
    ref: pool1              #   reusable across journeys (identity-collision
    count: 8                #   scenarios) — same Patient nodes each use
edges:                      # any DATA_MODEL relationship type between refs
  - type: OWNS_STAKE_IN     #   and/or existing IDs (country codes are IDs)
    from: b1
    to: c1
    props: {pct: 40}
  - type: HOLDS
    from: d1
    to: cr1
journeys:                   # claims routed through the journey model
  - count: 120
    clinic: c1
    broker: b1              # optional
    doctor: d1              # optional pin: route these claims through this
                            #   doctor (else journey model assigns one)
    patients: invented      # invented | recycled:<n> | pool:<ref>
    category: dental
    date_range: [2026-01-01, 2026-06-30]
transfers:                  # explicit money movements (shells auto-created)
  - path: [c1.account, shell, shell, b1.account]
    amount_usd: 40000
    count: 1                # optional: number of transfers spread over
    attrition_pct: 8        #   date_range (default 1)
    date_range: [2026-02-01, 2026-04-30]
```

*Schema extended 2026-07-30 (ADR-027, before any detection query existed):
added `doctor`/`credential`/`patients`-pool actor kinds, `country` pin,
journey `doctor` pin, `pool:<ref>` patient source, and `transfers.count` —
the original schema could not express credential-typology or
identity-collision scenarios at all.*

*Extended again 2026-08-05 (ADR-037, branch): journeys accept
`clone_pack: true` — the spec's claims become a claim mill (typology-4
substrate): one claim per journey, one procedure/narrative/price/line-item
template per spec with per-claim jitter (±2% amount, 30% closing-sentence
edits), two shared submission devices. Default false = the untouched
journey model; the base economy is byte-identical either way (verified).*

Ground truth for a scenario (which entities it created/affected) is emitted to
`data/ground_truth/scenario_<name>.csv` with the same shape as `planted.csv`.

---

## 4. Loader contract

Runs as the one-shot `seed` service in docker compose (and standalone:
`python -m loader`). Never runs the generator (ADR-005).

1. Wait for Neo4j to accept Bolt connections (retry ≤ 120 s).
2. Apply `graph/schema.cypher` (constraints + indexes; idempotent —
   `IF NOT EXISTS`).
3. **Wipe-and-load:** delete all nodes/edges, then load every CSV from
   `data/csv/`. Deterministic dataset ⇒ deterministic graph.
4. Validate: node/edge counts must equal `manifest.json` counts. Mismatch ⇒
   exit non-zero with a diff — never a silent partial load.
5. Exit 0. Compose marks seeding complete; the API healthcheck depends on it.

Load mechanism (`LOAD CSV` vs `neo4j-admin database import`) is an internal
choice benchmark-decided by whoever builds it (OPEN_QUESTIONS #1) — the
contract above doesn't change either way.

## 5. Detection runner contract

`python -m detection.run [--rules ghost_clinic,circular_payment] [--dry-run]`

**Detection is a build-phase step, never a boot step (ADR-029).** The
compose `seed` service does NOT run detection; it loads committed alert
CSVs like any other data (§4). Workflow:

- Development / Day 2: run `python -m detection.run` on demand against the
  loaded graph.
- Demo build (ADR-018 chain): after the one-time detection run,
  `python -m detection.export` writes `data/csv/alerts.csv` (Alert node
  columns: id, typology, rule_version, score, severity, status, note,
  summary_params, created_at) and `data/csv/rel_implicates.csv`
  (source_id, target_id, role), sorted by id (byte-stable re-export), and
  adds `alerts` / `rel_implicates` counts to `data/manifest.json`. These
  files are committed; the loader loads them when the manifest lists them.

- Reads rule registry: `detection/rules/<rule_key>.yaml`:

```yaml
key: ghost_clinic
name: Ghost clinic
typology: 1
version: "1.0"
kind: cypher | python        # implementation type
impl: queries/ghost_clinic.cypher   # or python module path
params: {min_claims: 30, inflow_share: 0.8, payout_share: 0.9}
severity_bands: {high: 80, medium: 50}
```

- For each rule: delete existing `Alert` nodes where
  `typology = key AND rule_version = version`, run the implementation, write
  new `Alert` nodes + `IMPLICATES` edges per the Alert schema (DATA_MODEL.md).
- Prints a JSON summary to stdout: `{"rules_run": [...], "alerts_written":
  {"ghost_clinic": 7}, "duration_s": 12.3}`.
- Exit non-zero if any rule errors; other rules still complete.

## 6. REST API contract (FastAPI)

Base path `/api/v1`. JSON only. No auth (ADR-011). Errors:
`{"detail": "<message>"}` with appropriate HTTP status. All list endpoints:
`limit` (default 50, max 200) and `offset`.

### `GET /api/v1/health`
```json
{"status": "ok", "neo4j": true, "alert_count": 41,
 "narration_cache": {"alerts": 41, "cached": 41, "match": true}}
```
- `neo4j: false` ⇒ status `degraded` (still HTTP 200; the demo must not 500).
- **Narration-cache validation (ADR-018):** on startup the API counts
  `Alert` nodes in the graph and narration files in the committed cache. On
  mismatch it logs an unmissable error (`CRITICAL NARRATION CACHE MISMATCH:
  <cached>/<alerts> — re-run the ADR-018 build chain from the top`) and
  serves `"match": false` with status `degraded`. The check exists so a
  stale cache **fails loudly at boot**, never silently degrades to template
  text mid-demo. (Cache entries additionally self-invalidate per-alert via
  `prompt_sha256`, §8 — the startup check catches wholesale staleness, the
  hash catches per-entry drift.) Behaviour specified here; implemented in
  the build phase.

### `GET /api/v1/stats`
Console header numbers:
```json
{"nodes": 50350, "relationships": 143210,
 "alerts": {"total": 41, "new": 32, "reviewed": 6, "dismissed": 3},
 "by_typology": {"ghost_clinic": 7, "credential_laundering": 9}}
```

### `GET /api/v1/alerts?status=new&typology=ghost_clinic&min_severity=medium`
```json
{"total": 41, "items": [
  {"id": "ALT_000007", "typology": "ghost_clinic", "rule_version": "1.0",
   "score": 91.5, "severity": "high", "status": "new", "note": "",
   "created_at": "2026-08-05T18:22:00Z",
   "title": "Ghost clinic pattern: Elysium Care Clinic",
   "implicated_count": 14}
]}
```
Sorted by score desc. `title` is server-composed from `summary_params`.

### `GET /api/v1/alerts/{id}`
Alert fields (as above) plus:
```json
{"summary_params": {"claim_count": 132, "inflow_share": 0.94},
 "implicated": [
   {"id": "CLI_000217", "type": "Clinic", "label": "Elysium Care Clinic",
    "role": "ghost_clinic"},
   {"id": "ACC_000944", "type": "PaymentAccount", "label": "ACC_000944",
    "role": "hub_account"}
 ]}
```
`label` is the node's human-readable name (name/full_name/code/id fallback).
404 if unknown id.

### `GET /api/v1/alerts/{id}/subgraph?hops=1`
The evidence subgraph: implicated nodes expanded `hops` (1 default, 2 max)
outward, **hard-capped at 300 nodes** (raised from 200 by owner decision
2026-07-30; cap applied by trimming lowest-relevance leaf nodes; response
says if trimmed). Shape is Cytoscape.js elements format, consumed verbatim
by the frontend:
```json
{"truncated": false,
 "elements": {
   "nodes": [{"data": {"id": "CLI_000217", "type": "Clinic",
               "label": "Elysium Care Clinic", "implicated": true,
               "role": "ghost_clinic", "props": {"bed_count": 0}}}],
   "edges": [{"data": {"id": "e0", "source": "CLM_0004410",
               "target": "CLI_000217", "type": "AT_CLINIC"}}]
 }}
```

### `GET /api/v1/alerts/{id}/narration`
```json
{"alert_id": "ALT_000007", "text": "This clinic pattern is suspicious because…",
 "source": "claude-cached"}
```
`source` ∈ `claude-cached` (from committed disk cache) | `gemini-live`
(**ADR-037, branch:** opt-in live tier succeeded) | `fallback`
(deterministic template). *(`claude-live` remains a reserved value from
the retired ADR-010 mechanism; no code path produces it.)*
**Never 404s and never blocks on network**: with `NARRATION_LIVE` unset
(the default and the Theni posture) behaviour is cache-first with template
fallback and zero network. With the flag set, ONE live call runs first
(hard 5 s timeout) and any failure falls through to cache, then template.

### `GET /api/v1/forecast` *(ADR-037, branch)*
Observed monthly claim series plus per-typology flagged exposure with a
next-month least-squares projection. `method` states the mechanism in the
payload; the console repeats it on screen — a projection from observed
trend, never presented as a trained model. Reads only Claim and Alert
nodes (hard rule 5 holds).
```json
{"window": {"start": "2026-01", "end": "2026-06"},
 "method": "least-squares linear projection of observed monthly amounts",
 "overall": {"series": [{"month": "2026-01", "claims": 3100,
                          "amount_usd": 4100000.0}],
             "next_month": {"amount_usd": 4300000.0,
                             "slope_usd_per_month": 200000.0,
                             "direction": "rising"}},
 "flagged": [{"typology": "template_cloning", "series": ["..."],
              "amount_usd_total": 11900.0, "next_month": {"...": "..."}}]}
```

### `PATCH /api/v1/alerts/{id}`
Body: `{"status": "reviewed"}` and/or `{"note": "checked registry, no
footprint"}`. Status must be `new|reviewed|dismissed`; note ≤ 2000 chars.
Returns the updated alert detail. 422 on bad values.

### `GET /api/v1/entities/{id}`
Generic node inspector for drill-down side panel: `{"id", "type", "label",
"props": {...}, "degree": 17}`. 404 if unknown.

## 7. Frontend contract

- Talks only to the API above; base URL from `VITE_API_BASE_URL`.
- Screens (MVP, Q6): alert queue (filter by status/typology/severity) →
  alert view = Cytoscape subgraph + evidence panel (implicated list +
  summary_params) + narration panel + status/note controls. Stats in header.
- Renders `elements` verbatim; styling keyed off `data.type`,
  `data.implicated`, `data.role`. Never requests more than the subgraph
  endpoint returns — full-graph rendering is out of scope (ADR-009).
- Report export: out of scope (Q6).

## 8. Narration builder contract *(amended 2026-07-30, ADR-032 — zero API calls)*

`python -m api.narration.build --export-inputs out.jsonl | --import-texts a.json ...`

- **No API calls exist, build-time or runtime.** The builder composes the
  canonical prompt per alert (`compose_prompt`: alert + summary_params +
  implicated entities, NO ground-truth data); a Claude **assistant working
  session** writes every narration from those prompts (uniform template:
  pattern + numbers → why the combination → honest alternative → next
  step); `--import-texts` refuses partial coverage and writes
  `api/narration_cache/<alert_id>.json`:
  `{"alert_id", "text", "model", "prompt_sha256"}` with the honest model
  tag `claude-fable-5 (assistant session, pre-generated)`.
- **The cache directory is committed** — the venue demo works from a fresh
  clone with no network; the UI labels these "pre-generated AI narration",
  never implying live generation.
- The deterministic fallback template per typology (pure function of
  summary_params) is unchanged and serves any cache miss.
- `/health` checks cache completeness **by alert-id set** (ADR-032): a
  same-size cache from a different detection run fails loudly with a
  `missing` count; per-entry `prompt_sha256` still pins what each text was
  written from.

**One-way demo build chain (ADR-018, amended by ADR-029).** The cache is
keyed by alert ID, and alert IDs are assigned per detection run — any
regeneration or detection re-run after the cache is built silently orphans
every entry. Therefore the demo artifacts are built strictly in this order,
and only in this order:

```
freeze dataset → run loader → run detection → export alert CSVs (§5)
             → build narration cache
             → commit (dataset + alert CSVs + cache together) → NO regeneration
```

If regeneration ever becomes unavoidable after the chain has run, the
**entire chain re-runs from the top and is re-committed as one unit** —
never partially, never "just rebuild the cache". Scheduled execution:
Aug 7 (MILESTONES); the held-out evaluation on Aug 9 uses a separate data
directory and never touches the committed demo artifacts (DAY2_PLAYBOOK
Shape C has the same rule for scale tests).

## 9. Docker compose contract

Services: `neo4j` (our `medgraph-neo4j:demo`: pinned `neo4j:5.26-community`
base with GDS 2.13 baked in at build time — ADR-004/ADR-026), `seed`
(one-shot loader, §4), `api`, `frontend`.
`docker compose up` from a fresh clone with a filled `.env` must reach a
browsable console at `http://localhost:5173` in ≤ 3 minutes *after images are
pulled* (ADR-005). **The repo ships with alerts already computed
(ADR-029):** detection ran once at demo-build time, its Alert nodes and
IMPLICATES edges were exported to committed CSVs (§5), and the `seed`
service runs the loader **only** — a fresh clone shows alerts because they
are data, and every judge's clone pays load cost, never detection cost.
Detection and narration remain runnable on demand via documented
one-liners for development and Day 2.

---

## Change protocol

1. Changing anything in this file = a **contract change**. Announce in the
   team group *before* opening the PR; PR title prefixed `contract:`.
2. The PR must update, in the same commit: this file, the affected code on
   both sides of the seam, and DECISIONS.md if the change reverses an ADR.
3. One approval required, and it must not be the author.
4. After merge, everyone rebases their branches the same day.

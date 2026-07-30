# Decision Log (ADRs)

Append-only. Every significant choice: context, decision, alternatives, why.
This file is our answer sheet for jury questions — write entries so any team
member can defend them aloud. Format: newest at the bottom, never edit old
entries (append a superseding ADR instead).

---

## ADR-001 — Graph database: Neo4j Community + Cypher + GDS (2026-07-28)

**Decision (fixed pre-planning):** Neo4j Community Edition with the Graph
Data Science library; Cypher for all queries.

**Rationale to defend:** the fraud we target is relational — signals are
shared endpoints and cycles, i.e. traversals and community structure.
- *vs PostgreSQL + recursive CTEs:* possible, but multi-hop
  variable-length traversal and community detection are exactly what SQL is
  worst at; Cypher pattern syntax also reads aloud well to a jury.
- *vs ArangoDB/Memgraph:* viable; Neo4j has the most mature algorithm
  library (GDS), best docs, and the largest hiring-signal value.
- *vs TigerGraph/JanusGraph:* operational weight unjustified at 50k nodes.
- Community-edition limits (single DB, no RBAC, no clustering) are
  acceptable for a prototype and are named honestly in PROJECT_BRIEF.

## ADR-002 — Environment baseline: detected hardware facts (2026-07-28)

Detected on the primary dev machine (J Don Gabriel's laptop), per owner
instruction to measure rather than assume:

- **RAM 23.7 GB, AMD Ryzen 7 7435HS (8C/16T), Windows 11 Home build 26200.**
- git 2.54.0 present; GitHub CLI 2.95.0 authenticated as `Don-Gabriel`.
- **Docker: NOT INSTALLED** on this machine at planning time.

**Consequences:** (1) Docker Desktop (WSL2 backend) install is a day-one
setup task for every machine — tracked in MILESTONES M1; nothing in the
stack can be integration-tested until then. (2) This machine takes the 16 GB
memory profile (4G heap / 2G pagecache). (3) Other four machines' specs
unknown — each member records theirs when installing Docker; the 8 GB profile
remains the floor that must always work (owner decision Q2).

## ADR-003 — Python 3.11 + FastAPI + Pydantic for API and tooling (2026-07-28)

**Decision (fixed):** one language for generator, loader, detection, API.
**Rationale:** one runtime for four modules keeps five fluid contributors on
common ground; FastAPI gives typed request/response models (Pydantic) that
mirror INTERFACES.md and auto-generated OpenAPI docs — a free artifact to
show judges. *Alternatives:* Flask (no typed contracts), Node/Express
(splits the team across two backend languages for no gain).

## ADR-004 — Pin Neo4j 5.26 LTS + GDS 2.13 (2026-07-28)

**Decision:** `neo4j:5.26-community` Docker image with GDS **2.13**.
**Why:** 5.26 is the LTS line; the GDS supported-versions matrix (checked
against GDS 2.13 docs on 2026-07-28 via Context7 mirror of
`installation/supported-neo4j-versions`) pairs Neo4j 5.26 ↔ GDS 2.13. Louvain,
PageRank, Betweenness Centrality, WCC confirmed production-tier in open-source
GDS. *Alternative:* Neo4j 2025.x calendar releases — newer but no LTS
guarantee and no benefit to us. **Verification still owed:** exact GDS plugin
install syntax in the Docker image (`NEO4J_PLUGINS` env var) and heap/pagecache
env-var names, to be confirmed against the operations manual when
`docker-compose.yml` is written (OPEN_QUESTIONS #2). We do not write those
lines from memory.

## ADR-005 — Committed dataset; seeding never generates (2026-07-28)

**Decision (owner-ratified Q7):** the generator runs at *development* time
with a fixed seed; its CSV output is committed (< 50 MB budget). The compose
`seed` service only loads committed CSVs, then runs detection.
**Why:** determinism (every clone shows the same graph, so the demo script
can reference specific entities), fast boot (the 3-minute target is
load-time, not simulation-time), and a clean held-out story (evaluation
regenerates with overlays; the demo dataset never changes under us).
*Alternative rejected:* generate-on-boot — slow, nondeterministic per clone,
and it couples demo stability to generator changes. **Corollary:** the
3-minute target is measured *after* `docker compose pull`; venue mitigation
(pre-pulled images, `docker save` tarballs on USB) lives in DEMO_RUNBOOK.

## ADR-006 — Determinism contract: no timestamps in generated artifacts (2026-07-28)

Manifest carries seed + config hash + counts, no generation time. Same
inputs ⇒ byte-identical outputs, so `git diff` on `data/` is a meaningful
review signal and "regenerate to verify" is possible for judges.

## ADR-007 — Frontend: React + Vite + Tailwind + Cytoscape.js (2026-07-28)

**Decision (fixed).** Cytoscape.js because the console renders *small
evidence subgraphs* (≤ 200 nodes) with interaction, which is its sweet spot.
*vs D3:* lower-level, more build time for the same result. *vs sigma.js:*
optimized for huge graphs we deliberately never render. *vs vis-network:*
weaker layout ecosystem. Layout algorithm choice: OPEN_QUESTIONS #6.

## ADR-008 — Detection = batch rule registry writing Alert nodes (2026-07-28)

**Decision:** rules are registry entries (YAML metadata + Cypher/Python
impl); a batch runner writes `Alert` nodes + `IMPLICATES` edges into the
graph; the API only reads/updates alerts.
**Why:** (a) Day-2 extensibility — a new typology is a new registry entry,
no API/frontend change; (b) demo safety — alerts are precomputed, so the
console never waits on an algorithm; (c) alerts-as-nodes makes evidence
expansion a plain traversal. *Alternative rejected:* on-demand detection per
API request — live-demo latency risk and no persistence for statuses/notes.

## ADR-009 — Alert-then-drill-down UI; never render the full graph (2026-07-28)

50k nodes on screen is noise and reads as amateur (owner constraint). The
console shows a queue of scored alerts; a click renders only the evidence
subgraph (hard cap 200 nodes, enforced server-side in the subgraph endpoint).

## ADR-010 — Narration: one cached Claude call per alert, offline-first (2026-07-28)

**Decision (fixed, shaped by Q3):** a build-time script makes one API call
per top alert (`claude-opus-5` via the official `anthropic` Python SDK),
caches JSON to disk, **cache committed to the repo**. At request time:
cache → deterministic template fallback; opportunistic live call only if
explicitly enabled, 5 s timeout. The venue is assumed fully offline.
**Why one call and not an "AI feature":** narration is the one place an LLM
genuinely helps (explaining a subgraph to a non-graph person); anything more
would be scope theater. Cost: ~40 calls, immaterial.

## ADR-011 — No auth on the console (2026-07-28)

Demo tool on localhost; login adds zero judging value and a demo-day failure
mode. Named in PROJECT_BRIEF as a production gap (Enterprise RBAC story).

## ADR-012 — Held-out protocol: time-boxed abstention + hash commitment (2026-07-28)

**Decision (owner-ratified Q4):** see DATA_GENERATION §5 for the full
protocol; Pavithra R is the author; DETECTION_SPEC freeze planned
2026-08-06; evaluation 2026-08-09, run once. **Honest limits are documented
in DATA_GENERATION §5 and must be stated in the pitch** — this is a
good-faith firewall, not an independent red team.

## ADR-013 — No published rubric; Day-2 prep targets three constraint shapes (2026-07-28)

The organisers published only the track title ("International Medical Fraud
Intelligence Graph — graph database to map/prevent medical scams"); no
judging rubric exists. Rather than guess organiser intent, DAY2_PLAYBOOK
prepares rehearsed extension paths for the three most likely constraint
shapes: new node/edge type, new external API integration, stress test.

## ADR-014 — Fluid roles + defence areas instead of module ownership (2026-07-28)

**Decision (owner-ratified Q1):** no module-to-person ownership; all five
work across the codebase. Coordination load moves to INTERFACES.md (the
contract layer) and CONTRIBUTING.md (claim-before-work protocol). Individual
evaluation is handled by DEFENCE_AREAS.md: each member is the designated
first answerer for one area in jury Q&A. **Consequence:** contract discipline
is not optional; an undocumented seam change breaks four other people.

## ADR-015 — Real countries, fictional entities (2026-07-28)

**Decision (owner-ratified Q5):** real corridor countries (IN, TH, TR, AE,
SG) and real procedure *categories*; every person, clinic, broker, insurer,
code, and identifier is invented. **Why:** corridor realism makes the pitch
land; fictional entities make "is this real patient data?" a one-word answer.
The README carries an explicit synthetic-data notice.

## ADR-016 — Held-out isolation tightened: red-team member does not read the detection spec (2026-07-29)

**Context:** ADR-012's protocol let the red-team member (Pavithra R) read
DETECTION_SPEC.md — the original DATA_GENERATION §5 even *assumed* she would
— which capped the evaluation's claim at "robustness to unseen
parameterizations of known typologies." That forfeits the materially
stronger claim (detection of independently-conceived fraud) for no benefit:
she never needed the spec, only the schema and overlay format.

**Decision (owner-directed):** from 2026-07-29 the red-team member does not
read DETECTION_SPEC.md or `detection/` rule implementations until the
held-out evaluation results are committed; scenarios are authored from
PROJECT_BRIEF, DATA_MODEL, and INTERFACES only; her other participation
(frontend, console, demo, pitch) is unrestricted. Enforcement in
CONTRIBUTING.md; accidental exposure downgrades the claim and is recorded
here, not hidden.

**The honest complication:** whether Pavithra has *already* read the spec
(in-repo since Jul 28) is unverifiable from git — it is a fact only she can
attest. Resolution mechanism: recorded attestation at the Jul 29 sync
(OQ #12). Branches: she attests non-reading → strong claim available; she
has read it → role passes to Vijayalakshmi G contingent on the same
attestation (best substitute: deepest generator/overlay knowledge, and her
defence area doesn't need the spec; cost: she exits all detection work until
Aug 9); nobody can attest → we keep the weaker claim and say so in the
pitch. **Record the attestation outcome as a dated note under this ADR.**

> *Attestation outcome (append at the Jul 29 sync):* **mooted 2026-07-30
> (ADR-027)** — the team collapsed to a single implementer before any
> attestation was recorded; the red-team role no longer exists. The
> held-out protocol is now temporal separation (DATA_GENERATION §5).

## ADR-017 — Schedule re-planned to 14 days; scope is the shock absorber (2026-07-29)

**Context:** planning consumed Jul 28 and spilled into Jul 29; the build
window is now 14 days (~445–475 person-hours). All anchored dates are
immovable: freezes Aug 6/8, rehearsal Aug 10, event Aug 12–13.

**Decision:** absorb the loss inside existing windows — M1 compresses to
~1.5 days (its scaffold work parallelizes worst anyway, gated on Docker
installs); M2's weekend is the shock absorber. **Assessment: the schedule
still fits, with zero slack.** Any further loss triggers the pre-agreed cut
order — scope, never dates: (1) typology 4 (template cloning — carries the
only real algorithmic risk, fingerprint tuning per OQ #3), (2) typology 6
(circular payment — contained but less demo-critical than the algorithmic
differentiators 1–3 and the cheap, vivid 5), (3) console conveniences.
Never cut: freezes, dress rehearsal, cold-start test, held-out evaluation,
narration fallback, typologies 1–3 and 5. This agrees with the owner's
stated preference (drop 4 and 6 first) and adds the ordering *between* them:
4 before 6, because 4's risk is algorithmic while 6 is bounded Cypher.

## ADR-018 — One-way demo build chain; stale narration cache fails loudly (2026-07-29)

**Context:** the narration cache is keyed by alert ID, and alert IDs are
assigned per detection run. Regenerating data or re-running detection after
the cache is built orphans every entry — and the API's per-entry fallback
would mask it as quietly-degraded template text mid-demo.

**Decision:** strict one-way build sequence for demo artifacts — freeze
dataset → load → detect → build narration cache → commit as one unit → no
regeneration. Any unavoidable regeneration re-runs the entire chain from the
top; never partially. Guard rail: on startup the API compares cached
narration count to alert count; mismatch logs a CRITICAL error and surfaces
`narration_cache.match: false` at `/health` (status `degraded`) — loud at
boot, never silent at demo time. Contracts: INTERFACES §6/§8; procedure:
DEMO_RUNBOOK. Behaviour specified now, implemented in the build phase.

## ADR-019 — Offline image distribution + cold-start acceptance test (2026-07-29)

**Context:** image pull/build at the venue is the single largest offline
risk — larger than the Claude API, which the committed cache already covers.
A machine that has been online holds warm Docker caches, so "it worked on my
laptop" proves nothing about a cold venue start.

**Decision:** all three images (pinned Neo4j, API, frontend) are built in
advance and carried as one `docker save` tarball plus a full git bundle on
two identical USB sticks (manifest in DEMO_RUNBOOK). Acceptance is a
ten-step cold-start test — network adapter disabled, no pre-existing project
images, `docker load` → compose up → alert queue with `claude-cached`
narrations — which **only counts when passed on the actual demo laptop at
the Aug 10 dress rehearsal from a cold start**. Compose must pin exact image
names/tags so the runbook commands stay copy-pasteable.

## ADR-020 — Compose authored; Neo4j env syntax part-verified, plugin line flagged (2026-07-29)

**Context:** OQ #2 required verifying Docker-image syntax before writing
`docker-compose.yml`; neo4j.com blocks automated fetching.

**Verified** (against Neo4j's official `llms-full.txt` docs mirror,
2026-07-29): `NEO4J_AUTH: neo4j/<password>`; config-to-env conversion with
the double-underscore rule, by literal example
(`NEO4J_server_memory_heap_initial__size`, `NEO4J_server_memory_heap_max__size`);
`NEO4J_server_memory_pagecache_size` follows the same verified rule.
`dbms.security.procedures.unrestricted=gds.*` setting name verified against
Neo4j GDS/Bloom docs.

**Unverified, flagged in-file:** the `NEO4J_PLUGINS: '["graph-data-science"]'`
install line — no reachable authoritative snippet confirmed it, so it is
marked UNVERIFIED in docker-compose.yml with a mandatory M1 gate:
`RETURN gds.version()` must report 2.13.x on first boot. Also unconfirmed
until first boot: `wget` availability in the image for the healthcheck
(curl fallback noted in-file). OQ #2 updated to track only this remainder.

**Also decided:** compose image names pinned (`medgraph-api:demo`,
`medgraph-frontend:demo`) so DEMO_RUNBOOK's `docker save` commands are
copy-pasteable; api and seed share one image (same code, different command).

## ADR-021 — Generator v1 landed; population table corrected to arithmetic reality (2026-07-29)

**Context:** the first full generator run produced 63.5k nodes against the
~50k target and exposed that DATA_GENERATION's original population table was
internally impossible (12k patients × 1–2 devices each cannot yield 6k
devices; 12k one-claim journeys cannot yield 25k claims). The inconsistency
was an unnamed planning assumption — exactly the failure mode the working
rules now exist for.

**Decision:** journeys explicitly yield 1–3 claims (main + ancillary);
populations tuned to 10k patients / 1.5k doctors / ~30% second-device rate.
Measured seed-42 output: **51,871 nodes, 191,739 relationships, 7.4 MB,
10.6 s** — on target and far under the 50 MB budget. DATA_GENERATION §2
updated with the corrected table and measured totals. Determinism verified
by test (same seed ⇒ byte-identical tree; different seed ⇒ different).

**Also:** SimHash (64-bit, word 3-gram shingles) implemented as the
fingerprint per OQ #3's SimHash-first plan — OQ #3 stays open until the
clone-vs-honest separation test at M3. Scenario overlays and planted cells
deliberately not implemented yet (OQ #12 / M3 respectively).

## ADR-022 — USED_DEVICE emission fixed: ownership implies an edge (2026-07-29)

**Context (bug, found in seed-42 verification):** journeys only tracked the
one device used for a claim, so second devices became edge-less orphan nodes
(~2.3k of 12.4k) and the 6% family-sharing rate effectively vanished from
the edge table — device sharing is the primary graph substrate for
typology 5, so the signal barely existed.

**Decision:** every owned device now produces a `USED_DEVICE` edge — claim
journeys keep their real usage windows; devices unused on any journey get a
deterministic dormant window (portal registration/browsing 2–13 weeks
before the patient's first treatment). Enforced by test
(`test_every_device_edged_and_sharing_present`).

**Measured, seed 42 post-fix:** 12,975 USED_DEVICE edges over 12,383
devices, **0 unedged**; **560 devices shared by >1 patient — 555 honest
family shares vs 5 recycled-identity shares** (classification: shared
non-empty passport ⇒ recycled; clones of passportless patients (~5% of
clones) count as family, so 5 is a floor). Honest noise is ample — the
fraud signal is a genuine needle in a haystack. **Flag, not fixed here:**
5 recycled cases is *thin* for demoing typology 5 on the emergent layer
alone; recycling volume is revisited during M3 fraud-layer calibration
alongside planted cells, not silently tuned today.

## ADR-023 — OWNS_STAKE_IN generated, with honest majority (2026-07-29)

**Context (gap, found in seed-42 verification):** DETECTION_SPEC's
kickback-ring signature includes broker equity in clinics, but the
generator emitted zero `OWNS_STAKE_IN` edges — a detection rule pointing at
an edge type that never exists.

**Decision: generate the edges, don't cut the signature clause.** The
ownership leg is core to typology 3's story (and DATA_MODEL/Day-2 build on
it). Two layers: **honest** — ~10% of brokers hold a *declared* stake
(5–35%) in a size-weighted local clinic (hospital groups with in-house
facilitation, exactly the FP mode DETECTION_SPEC already names); **hidden**
— steering brokers acquire stakes (10–40%) in each partner clinic with
probability 0.5, deduped against declared holdings, recorded in ground
truth as `hidden_stake`. **Measured, seed 42: 35 stake edges — 25 honest,
10 hidden.** Edge presence alone is therefore ~71% innocent: the edge is a
feature, not a label, and the circularity defense holds. DETECTION_SPEC
needs no change — its signature and FP modes now both exist in data.

## ADR-024 — Capacity collapse to one laptop; ADR-017 cut ladder executed (2026-07-30)

**Context (owner-reported):** the team no longer works in parallel — all
five members share **one laptop**, with J Don Gabriel driving nearly all
implementation. Real capacity is **~110–130 total hours**, not the ~475
person-hours MILESTONES assumed. ADR-017 said any further loss triggers the
pre-agreed cut order; this is that loss, at maximum size.

**Decisions:**

1. **Cut ladder steps 1–2 executed now**, not held as contingency:
   typology 4 (template cloning) and typology 6 (circular payment) are
   descoped. We ship typologies **1, 2, 3, 5**. Both descoped sections stay
   fully specified in DETECTION_SPEC as the deliberate "what we would build
   next" — a pitch asset (roadmap with documented FP modes), not a gap.
2. **Generator-output consequences, stated precisely:**
   `narrative_fingerprint` is now consumed by no shipping typology (it
   still ships in claims.csv as typology-4 substrate; the
   `claim_fingerprint` index was removed from schema.cypher/DATA_MODEL so
   that every index maps to a shipping query). **`OWNS_STAKE_IN` and
   `TRANSFERRED` are NOT orphaned** — shipping typology 3's
   shared-infrastructure signature uses both (the tasking's assumption that
   OWNS_STAKE_IN falls unused was checked against DETECTION_SPEC §3 and is
   incorrect; flagged rather than silently adopted, per working rule 1).
3. **MILESTONES rewritten** for 13 days / one implementer / ~125 h planned
   (fits 110–130 with zero slack). All anchored dates hold: detection
   freeze Aug 6, integration freeze Aug 8, dress rehearsal Aug 10, Day 1
   Aug 12. Extended cut ladder recorded there (next: console conveniences →
   subgraph hops=2 → live-narration path → typology 3 centrality term).
4. **Non-code work reassigned** so git history shows five real
   contributors and each person owns a defensible deliverable: Pavithra
   (held-out scenarios, demo rehearsal, screenshots), Vijayalakshmi
   (PITCH, GLOSSARY), Mary (DEMO_RUNBOOK, cold-start execution),
   Poonkundran (DAY2_PLAYBOOK, fresh-clone verification). Each commits
   under their own git identity from the shared laptop — CONTRIBUTING
   "Shared-machine identity" documents the switch procedure.
5. **DEFENCE_AREAS updated for the harder truth:** four people defend code
   they did not write. Per area it now lists what must be explainable
   regardless of authorship; MILESTONES adds aloud-rehearsal rounds
   (Aug 9, Aug 10) plus the Aug 11 question roulette. Authorship is never
   pretended — "Don drove the implementation; this area is mine to know."
6. **CONTRIBUTING's parallel-work/collision protocol retired** (it assumed
   five machines). INTERFACES.md remains the contract, including its change
   protocol. New standing risk: the laptop is a single point of failure —
   push at the end of every session.
7. **PITCH demo beat 6 swapped** from `circular_payment` to
   `impossible_travel` (the vivid one-sentence contrast that survives the
   cut).

**Alternatives considered:** keeping six typologies with shallower
implementations (rejected: five solid beat six shaky was already ADR-017's
logic — four solid beats six shaky harder); moving a freeze (rejected: the
freezes protect the held-out protocol and the demo, which are the pitch).

## ADR-025 — Loader mechanism: LOAD CSV over neo4j-admin import (2026-07-30, resolves OQ #1)

**Context:** INTERFACES §4 left the bulk-load mechanism to a benchmark on
the real dataset (51,144 nodes / 193,694 relationships, seed 42).

**Measured on the lead machine (Docker Desktop/WSL2, 2G heap / 1G pagecache
floor profile), full scale, both mechanisms loading identical data:**

| mechanism | time | notes |
|---|---|---|
| `LOAD CSV` (batched `CALL (row) {...} IN TRANSACTIONS OF 5000`) | **15.3 s** (schema + wipe + load + count validation) | runs against the live server; per-file breakdown in the seed log |
| `neo4j-admin database import full` | **3.8 s** import (7.5 s container wall), peak 547.7 MiB | requires a non-existent/empty database — cannot run against the live server the seed service waits for |

**Decision: LOAD CSV.** Both are far inside the 2-minute seed budget; the
12-second saving from admin import would cost the compose architecture —
admin import must run with the database offline, which inverts the
"neo4j healthy → seed loads" orchestration and complicates re-seeding.
Wipe-and-load semantics stay exactly as contracted. Details that made it
work: CSVs are mounted read-write into the server's import dir (the image
entrypoint chowns it — a `:ro` mount kills the container); statements are
comment-stripped before splitting on `;` (a semicolon inside a `//` comment
was executed as Cypher on the first run); the modern `CALL (row) {...}`
scope syntax replaces the 5.26-deprecated `CALL { WITH row ...}` form.

## ADR-026 — GDS baked into our own image; NEO4J_PLUGINS rejected for offline demo (2026-07-30, closes OQ #2 and OQ #11)

**Context:** ADR-020 flagged the `NEO4J_PLUGINS: '["graph-data-science"]'`
line UNVERIFIED. The M1 run verified it is **syntactically correct and
functional** — and revealed it **downloads the GDS jar from
graphdatascience.ninja at every container creation** (observed live: the
resolver fetched versions.json and pulled
`neo4j-graph-data-science-2.13.11.jar`, ~1 min on tonight's network, and
the neo4j healthcheck window expired mid-download). That mechanism can
never work at the offline venue: ADR-019's tarball carries images, and the
plugin was not *in* the image.

**Decision:** build our own pinned image `medgraph-neo4j:demo`
(`graph/neo4j.Dockerfile`): `FROM neo4j:5.26-community` + the exact jar the
official resolver selected (GDS **2.13.11**) downloaded at **build** time
into `/var/lib/neo4j/plugins/`. `NEO4J_PLUGINS` is not used;
`NEO4J_dbms_security_procedures_unrestricted=gds.*` stays explicit (the
installer would otherwise have set it). The docker-save tarball now carries
GDS by construction. INTERFACES §9 and DEMO_RUNBOOK updated to the three
`*:demo` image names.

**M1 gate results (fresh volume, floor profile 2G heap / 1G pagecache):**
- `RETURN gds.version()` → **2.13.11** ✓ (OQ #2 closed)
- `docker compose up -d` → all services healthy in **48 s** (≤ 3 min ✓)
- Louvain (`gds.louvain.stats`, undirected claim-participation projection,
  34,078 nodes / 189,972 rels): **2.4 s** compute, 747 communities,
  modularity 0.597
- PageRank (`gds.pageRank.stats`, natural orientation): **0.23 s**, 20
  iterations (default cap; convergence tuning is rule work, M3)
- Betweenness (`gds.betweenness.stats`, exact): **122.5 s** compute — the
  expensive one, exactly as DATA_MODEL's scale notes predict; at our scale
  it fits a batch detection run, and sampling is the ready fallback if M3
  finds it too slow in the seed path
- Memory: projections 14–16 MiB each; container peak ~3.3 GiB total under
  the floor profile, no OOM ⇒ **OQ #11 resolved: default profiles
  suffice; no explicit projection sizing needed at this scale.**

## ADR-027 — Team collapse to ONE person; held-out protocol becomes temporal separation (2026-07-30)

**Context (owner-reported):** no other member is contributing at all — no
Pavithra, no Vijayalakshmi, no Mary, no Poonkundran. ADR-024's "one laptop,
one implementer, four supporting contributors" model is dead: J Don Gabriel
writes all code and docs, gives the pitch alone, and does Day 2 alone.
Capacity is one person's 13 days (~95–110 h realistically — see MILESTONES),
and ~25–30 h of non-code deliverables previously assigned to others (pitch,
glossary, runbook execution, screenshots, fresh-clone verification, Day-2
rehearsal) return to the implementer as scheduled hours.

**Decisions:**

1. **Held-out protocol: person-separation → temporal separation.** A
   red-team author who never read the detection spec is impossible with one
   person. Replacement, executed same day: five held-out scenarios authored
   2026-07-30 **before any detection query existed in the repo** (the
   `detection/` tree contains only scaffolding at the hash commit),
   consulting only PROJECT_BRIEF / DATA_MODEL / INTERFACES / GLOSSARY in
   the authoring session; stored outside the repository; SHA-256 hashes
   committed alone (HELDOUT_COMMITMENT.md); files stay closed until the
   one-shot evaluation. **The claim this supports is ordering, not
   independence** — the same person conceived both sides. Pitch wording
   fixed in DATA_GENERATION §5; PITCH.md carries it verbatim. ADR-012's
   evaluation mechanics (frozen rules, run once, report misses) are
   unchanged; ADR-016's attestation branches are mooted (OQ #12 closed).
2. **Overlay schema extended first** (`contract:` commit, same day, before
   the hashes): doctor/credential/patients-pool actor kinds, country pins,
   journey doctor pin, `pool:<ref>`, `transfers.count` — the schema could
   not previously express typology-2 or typology-5 scenarios, and it had
   to be expressive *before* the freeze for the protocol to work.
3. **Team scaffolding stripped:** DEFENCE_AREAS becomes a solo jury-prep
   question bank (every area is mine now); CONTRIBUTING drops
   identity-switching and multi-contributor process (Conventional Commits
   and the INTERFACES change protocol stay); MILESTONES rewritten for one
   person with the returned non-code hours scheduled explicitly;
   DAY2_PLAYBOOK rewritten for a solo sprint (rehearse, don't parallelize).
4. **Anchored dates hold:** detection freeze Aug 6, integration freeze
   Aug 8, dress rehearsal Aug 10, Day 1 Aug 12. Scope remains the shock
   absorber (cut ladder in MILESTONES).

**Alternatives considered:** keeping the ADR-024 docs and quietly working
alone (rejected — the docs would then lie about who does what, and the
jury reads the repo); dropping the held-out evaluation entirely (rejected —
temporal separation is weaker than person-separation but still kills the
"tuned after the fact" accusation, and it is cheap).

## ADR-028 — Typology 3 drops betweenness: measured out, not assumed away (2026-07-30)

*(Number reserved while its benchmark ran; landed the same day as ADR-029,
which references it. Full measurements:
`detection/benchmarks/typology3_centrality.md`.)*

**Context:** DETECTION_SPEC §3 planned "PageRank + betweenness to rank hub
brokers." Exact betweenness measured **122.5–131.6 s** on the 34k-node
claim-participation projection (ADR-026 + re-run today) — it is O(n·m), so
10× data ≈ 100× work: **hours**, breaking the boot budget (ADR-029), the
Day-2 stress-test shape, and the 10M-node story. Before optimizing it, we
asked whether typology 3 needs it at all.

**Benchmark (seed 42, GDS 2.13.11, 2G/1G floor; K = 13 emergent steering
brokers out of 250):**

| broker ranking signal | hits@13 | precision@13 | median rank of true steerers |
|---|---:|---:|---:|
| betweenness on referral projection (exact, 73 ms) | 1 | 0.077 | 131 |
| PageRank, unweighted (85–106 ms) | 1 | 0.077 | 129 |
| PageRank, referral-weighted | 2 | 0.154 | 86 |
| weighted degree ≡ raw referral count (2 ms) | 2 | 0.154 | 117 |
| **top-clinic concentration share, ≥ 20 referrals (one Cypher line)** | **5** | **0.385** | **66** |

Weighted degree and naive claim count agreed on all 250 brokers — the GDS
call adds overhead to a feature one Cypher aggregation already computes.
Sampled betweenness (Brandes `samplingSize`, verified against the live
2.13 install): 512 → 1.79 s, Spearman ρ 0.894, top-50 overlap 80%;
2048 → 7.09 s, ρ 0.946, overlap 94% — vs 131.6 s exact.

**Decision:** the shipped typology 3 uses **no global centrality ranking**:
mutual concentration (both directions, incl. top-clinic share) + shared
infrastructure (stakes, common accounts, transfers, addresses) + Louvain
community context. PageRank/betweenness leave the rule; sampled
betweenness (samplingSize 2048) is the documented fallback if a future
rule genuinely needs bridging structure.

**Why (the finding, not just the timing):** steering is a *concentration*
pattern, not a *bridging* pattern. 8 of 13 emergent steering brokers sit at
or below the economy's median referral volume (≤ 10 referrals) — invisible
to every volume- or topology-based score by construction; the five visible
ones were ranked 1, 2, 3, 4 and 7 by the concentration feature alone.

**The 10-million-node jury answer (say it like this):** "We measured
instead of assuming. Exact betweenness took 132 seconds on 51 thousand
nodes; it is O(n·m), so at ten million nodes that's hours — and our
benchmark showed it was also the *worst* discriminator for kickback
brokers, because steering is a concentration pattern, not a bridging
pattern. So the shipped rule uses index-backed one-to-two-hop concentration
and shared-infrastructure queries that scale linearly, and community
detection for context. If a pattern ever truly needs betweenness, GDS's
Brandes sampling reproduced 94% of the exact top-50 at 5% of the cost — in
a batch window, never at boot."

## ADR-029 — Alerts are committed data; compose-up never runs detection (2026-07-30)

**Context:** the compose `seed` service ran `loader && detection.run`,
meaning every fresh clone (every judge) would pay full detection cost at
boot — and a detection re-run at boot re-assigns alert IDs, which is
exactly the regeneration the ADR-018 one-way chain forbids once the
narration cache exists. Centrality-based rules make boot-time detection
strictly worse as data grows (ADR-028).

**Decision:** detection runs **once**, at demo-build time, on the build
machine. `python -m detection.export` then writes the resulting `Alert`
nodes and `IMPLICATES` edges to `data/csv/alerts.csv` and
`data/csv/rel_implicates.csv` (sorted by id — byte-stable re-export) and
adds their counts to `data/manifest.json`. The loader treats them as
**optional stems**: loaded and count-validated when the manifest lists
them, skipped when it doesn't (a freshly regenerated dataset has no alert
entries until the chain reaches the detect+export step). `IMPLICATES`
targets any entity label, so the loader routes rows to indexed per-label
MATCHes by ID prefix (generalizing the OWNED_BY two-pass trick).
`docker compose up` therefore loads a graph that already contains alerts;
detection stays runnable on demand (`python -m detection.run`) for
development and Day 2.

**Consequences:** (a) judge clones boot in load time (~15 s seed) at any
detection cost; (b) `down -v` re-seeds graph *and* alerts
deterministically; (c) the ADR-018 chain gains an explicit export step:
freeze → load → detect → **export** → narrate → commit as one unit;
(d) `Alert.created_at` is pinned by the build-phase run (runner flag), so
re-exporting an unchanged graph is byte-identical.

**Alternative rejected:** keeping detection in the seed path ("alerts are
always fresh") — freshness is precisely the failure mode: the demo needs
*frozen* alerts matching the frozen narration cache, and recomputing what
is already committed spends every judge's first three minutes proving
nothing.

## ADR-030 — Detection layer built and calibrated on the honest economy; measured determinism boundary (2026-07-30)

**Context:** M3 pulled forward. The four shipping rules (ADR-024 scope) are
implemented as registry entries (ADR-008) with a real runner replacing the
no-op: idempotent per rule+version, `--dry-run`, `--rules` filter,
`--created-at` pinning (ADR-029), deterministic alert numbering by
(rule key, score desc, anchor id), 200-entity implicated cap (claims
dropped first), and both `python` and `cypher` implementation kinds
(cypher path live-smoke-tested; all four shipping rules are Python for
explainability). All GDS calls were verified against the live 2.13.11
install via `CALL gds.list(...)` before use.

**Calibration (DATA_GENERATION §6, executed):** thresholds tuned solely on
a seed-42 generation with every `fraud:` gate at 0.0, to zero medium+
honest alerts per rule. Final honest counts (= documented FP rates):
ghost_clinic 5 low · credential_laundering 62 low · kickback_ring 0 ·
impossible_travel 6 low. Full measured record in detection/README.md.

**Decisions forced by measurement, not taste:**

1. **Post-revocation billing severity is volume-tiered**, not flat-high.
   The honest economy keeps revoked doctors on rosters (27 honest
   post-revocation billers, 1–29 claims, gaps from 18 days), so
   DETECTION_SPEC's "starts at high" is implemented as: always emitted,
   `high` only beyond the honest volume ceiling (ramp 30→60 claims).
   Generator-side fix parked as OQ #14.
2. **Travel table (OQ #5):** `travel_time_days` in generator/config.yaml,
   mirrored in the rule YAML, unit-test-enforced sync. All corridor pairs
   1 whole day (longest flight TR–SG ≈ 11 h ⇒ next-day treatment is
   possible everywhere; only same-day cross-country is clearly
   impossible — the spec's own conservative-whole-days guard).
3. **Typology 3 per ADR-028:** concentration gate (top-clinic share ≥ 0.30
   at ≥ 5 pair claims) + shared-infrastructure evidence (stake softened by
   accreditation as the declared-ness proxy the spec suggests — the graph
   carries no declared/hidden flag; clinic→broker transfers beyond the
   commission_pct-computable expectation; shell-hop paths; shared
   addresses; co-owned accounts) + small same-community bonus. No
   centrality. Dev-set result: 6 alerts, all on true steering brokers
   (precision 1.0, broker recall 6/13 — the infrastructure terms recovered
   two sub-10-referral steerers the benchmark's concentration feature
   alone could not see).
4. **Louvain determinism boundary (measured):** single-threaded projection
   + Louvain with canonical community labels is byte-stable within one
   loaded store; across wipe-and-reloads Neo4j's id freelist reorders the
   store and Louvain tie-breaks drift on a few borderline nodes — scores,
   severities, IDs, edges and alert sets stayed byte-identical across two
   independent load→detect→export cycles; only the two community *context*
   fields moved. Acceptable because the demo artifacts come from exactly
   one detection run (ADR-018); boundary documented in detection/README.md.
5. **Alerts-as-data round trip proven (ADR-029):** detect → export → wipe →
   load (alert CSVs included, 33/33 manifest counts) → re-export was
   byte-identical (alerts.csv, rel_implicates.csv, manifest.json); seed
   with alerts ≈ 7–9 s on the throwaway container. Dev-set evaluation
   (new `evaluation/` — the only code allowed to read ground truth):
   kickback precision 1.0 / recall 6/13; impossible_travel 0/5 recycled
   groups — their tightest cross-country gaps are 6–76 days, so the dev
   set contains NO temporally impossible recycled case and typology 5 is
   not statistically evaluable until the held-out scenarios; typologies
   1/2 not evaluable until planted cells land (Jul 31).

**Alternatives rejected:** flat-high post-revocation severity (27 honest
highs — calibration mandate wins); per-pair travel-day guesses above 1 day
(nothing in the corridor set justifies them); forcing cross-reload Louvain
stability via legacy Cypher projections (undocumented ordering guarantee,
opaque — violates hard rule 1).

## ADR-031 — Dataset FROZEN; planted + impossible cases landed; dev-set numbers recorded (2026-07-30)

**Context:** last generator work before freeze (owner-directed order):
scenario overlays (INTERFACES §3, full schema, fixture-tested), planted
cells for typologies 1/2, and `identity_recycling.parallel_share` (0.5) —
colluding-clinic same-day billing, the fix for the measured "seed 42 has
zero temporally impossible recycled cases" finding.

**The frozen dataset (seed 42):** **51,990 nodes / 197,251 relationships /
7.6 MB** (+846 nodes, +3,557 rels vs the previous commit — provably
additive: every prior row is byte-identical in the new files). Double
regeneration byte-identical. Planted: 3 ghost cells (56 claims each,
feeder share 0.94, payout concentration 0.95) + 3 credential cells (one
licence across 3–4 identities; one biller with 57 post-revocation claims
vs the 29-claim honest ceiling); labels in `data/ground_truth/planted.csv`
(523 rows). Impossible travel: 3 same-day cross-country passport groups;
2 feasible-reuse groups kept as designed negatives.

**Dev-set evaluation (frozen rules, untouched since ADR-030 — nothing
tuned to the new cases):**

| typology | alerts (l/m/h) | TP | FP | precision | recall |
|---|---|---|---|---|---|
| ghost_clinic | 6 (3/0/3) | 3 | 3 | 0.50 | planted cells **3/3** |
| credential_laundering | 61 (56/0/5) | 4 | 57 | 0.066 | planted cells **3/3** |
| kickback_ring | 9 (5/4/0) | 6 | 3 | 0.667 | steering brokers 6/13 |
| impossible_travel | 5 (2/0/3) | 3 | 2 | 0.60 | impossible groups **3/3**; feasible reuse 0/2 by design |

Honest readings of those numbers, for the jury: every planted cell and
every impossible group is caught **at high severity**; the low-severity
tail is the documented honest-noise floor (56 of credential's 57 FPs are
`low` — post-revocation/shared-number honest modes the rule deliberately
surfaces at low). Two findings worth saying out loud: (1) credential's one
high FP is an honest revoked-but-rostered doctor whose volume was inflated
by an *emergent steering broker* — fraud-adjacent volume, mislabeled only
by typology; (2) kickback's three medium "FPs" are the three planted ghost
cells caught cross-typology (feeder concentration + shared address trip
the kickback gate) — reported as FP for typology-3 precision, separately
tagged `fp_cross_typology_planted` by the evaluator. The 7 missed
sub-median-volume steering brokers are unchanged from ADR-030.

**Honest-economy re-verification:** zero medium+ alerts on every rule
still holds (the calibration property). Low-count baseline shifted
slightly (ghost 5→7, credential 62→63); reproduced with pre-session
generator code byte-identically, so the drift is a baseline-measurement
discrepancy, not a behaviour change — annotated in the evaluator, not
tuned.

**FREEZE + unfreeze cost:** `data/` (including the exported
`alerts.csv` — 81 alerts, 2,098 IMPLICATES, pinned
`created_at 2026-07-30T00:00:00Z`) is frozen. The ADR-018 chain is
committed in two stages: dataset + alerts now, narration cache when built
(planned Aug 3), with **no regeneration permitted between or after** —
unfreezing means the full chain from the top (regenerate → load → detect →
export → rebuild narration cache → recommit as one unit) and costs a
rehearsal day. After the Aug 8 integration freeze it is a demo-blocker
emergency, nothing less.

## ADR-032 — Narration is committed data: pre-generated by an assistant session, zero API calls (2026-07-30)

**Context (owner decision, final):** zero budget — no `ANTHROPIC_API_KEY`,
no build-time or runtime API calls, ever. ADR-010's mechanism (one live
API call per alert at build time) is unimplementable as specified.

**Decision:** apply the ADR-029 pattern to narration. The canonical prompt
template lives in `api/narration/build.py` (`compose_prompt` — alert +
summary_params + implicated entities, never ground truth); a Claude
assistant working session read the composed prompt for **all 81 alerts**
and wrote each narration following that template's structure (pattern +
numbers → why the combination → honest alternative → next step); the
texts were imported through the same builder, which refuses partial
coverage and stamps each cache entry with `prompt_sha256` of the canonical
prompt and the honest model tag `claude-fable-5 (assistant session,
pre-generated)`. The cache is committed; the demo serves files. The UI
labels these **"pre-generated AI narration"** — never implying live
generation — and the deterministic template fallback path is unchanged.

**Guard tightened:** `/health` now checks cache **completeness by alert
id set**, not by count — a same-size cache from a different detection run
fails loudly (`missing` count surfaced; tested in
tests/test_narration_cache.py). ADR-018's chain stage 2 is hereby
complete: dataset + alerts + narration cache all committed; any
regeneration re-runs the whole chain including a full re-narration pass.

**Why this is defensible to a jury:** offline venue (nothing generates at
demo time — same argument as ADR-029), zero marginal cost, reproducible
artifact (prompt hashes pin exactly what each text was written from), and
honest labeling end to end. The texts were reviewed as part of the build.
What is genuinely lost vs ADR-010: the "live API integration" talking
point — replaced by the stronger one, that the entire demo is committed,
verifiable data. Closes OQ #8 (all 81 narrated, N is moot).

## ADR-033 — Single-machine event; no backup laptop (2026-07-30, closes OQ #13, confirms OQ #9)

**Owner decision, final:** the current PC is the only machine for the
whole event — build, rehearsal, Day 1 demo, Day 2 sprint. No dedicated
backup machine exists; hardware contingency is the owner's responsibility,
outside project scope. Consequences: DEMO_RUNBOOK's backup-laptop drill is
retired; the Docker-failure fallback chain is USB-restore on the same
machine → screenshot deck → screen recording. The USB sticks and the git
bundle remain mandatory (they also protect against disk failure of the
project itself). The demo laptop identity question (OQ #9) is resolved by
the same fact.

## ADR-034 — Held-out one-shot run under pre-registration; results recorded verbatim (2026-07-30)

**Protocol executed:** pre-registration committed and pushed first
(`c02ed40`, 22:34 IST: no rule/threshold/parameter/generator changes based
on results; misses reported as they land) → sealed file hashes re-verified
against the 290101e commitment (all five match) → scenarios injected via
`--scenario` into a separate data dir (53,576 nodes / 204,079 rels, loader
16.8 s) → frozen rules run **once** (8.5 s, 97 alerts) → scored by
`evaluation/heldout.py` (written before the run; blind name→typology map)
→ scenario files committed to `data/scenarios/heldout/` (hashes re-match).

**Stability proof:** 97 total alerts − 16 touching scenario entities =
exactly the 81 dev alerts — injection perturbed nothing upstream.

**Results — exact counts (5 scenarios · 8 legs expected · **5 detected** ·
**3 missed** · **2 distinct root causes**; 5 of 5 scenarios raised at
least one alert). The three missed legs are S2 credential, S5 credential,
S5 travel — the first two share one root cause.**

| scenario | expected | outcome |
|---|---|---|
| S1 ghost_satellite | ghost_clinic | caught low 42.7 (veneer suppressed footprint, as probed) + kickback/credential cross-hits |
| S2 license_shadow | credential_laundering | **MISSED** — the rule's same-body-or-country guard nulls a cross-jurisdiction licence share, and its other-active-credential guard nulls the revoked biller. Both guards are individually justified; composed, they leave a gap |
| S3 quiet_kickback | kickback_ring | caught medium 54.6 + low 40.8 (both pairs); clinics drew ghost mediums 66.9/65.8 |
| S4 split_ledger | impossible_travel | caught low 42.0 (same-day pair fired; severity floor because every escalation signal was deliberately absent) |
| S5 confluence | all four | ghost medium 56.9/52.4 + kickback low 45.2/44.7 caught; **credential and travel legs MISSED** — same credential guard-composition gap as S2, and the travel rule does not flag the scenario's 2–26 day gaps because they are physically feasible |

Every scenario was touched by at least one rule (5/5) — cross-typology
redundancy is real — but the three missed legs are systematic, not noise:
**FP guards compose into blind spots** (credential) and **conservatism
excludes feasible-but-suspicious** (travel). Both fixes specified as
next-build; neither applied (pre-registration). Precision is not scored on
the held-out world (it adds only fraudulent structure — pre-declared in
the scorer); precision remains the dev-set property (ADR-031). Pitch
wording + prepared miss answers: PITCH.md. The Aug 9 calendar slot is
retired; freezes Aug 6/8 stand as formalities protecting the demo.

## ADR-035 — Projector review of the console; four fixes and a click-path reorder (2026-07-30)

**Context:** the console worked but had never been assessed as a *demo
surface* — a hostile viewer, three metres from a washed-out projector.

**Findings, honestly:**

1. **Severity was legible but not scannable.** Score colour alone carried
   it; the queue read as a uniform list rather than a hot-to-cold zone.
2. **The subgraph was functional, not striking, above ~100 nodes.** The
   ghost-clinic view renders 117 nodes; every non-implicated Patient and
   Doctor was labelled, so thirty irrelevant names competed with the four
   that carry the story. The 19-node impossible-travel view, by contrast,
   is genuinely striking — two ember-haloed identities, two conflicting
   claims, two countries, readable at a glance.
3. **The evidence panel dumped fields.** It opened with raw keys and
   snake_case enum values (`shared_license`, `post_revocation_billing`).
4. Node/edge weights were tuned for a laptop, not a projector.

**Fixes applied (surgical, not a redesign):** severity edge-bars plus a
tinted row background for high/medium and tighter right-hand columns;
heavier edges, larger minimum nodes, thicker ember halos and larger
always-on implicated labels; a value dictionary rendering enums as
English plus a composed opening sentence stating what fired ("5 of 6
ghost-clinic indicators fired strongly: too few doctors for the claim
volume; no physical footprint; …"); and the dense-label threshold lowered
from 150 to 60 nodes so dense views keep only implicated labels while
small views keep their useful context.

**Click-path reorder (the highest-leverage change, zero code):** the demo
now **opens with `impossible_travel`** and goes deep on `ghost_clinic`
second. The travel alert lands in one sentence and one glance; the ghost
alert needs narration to decode. Leading with the legible one buys
attention for the complex one. PITCH.md carries the final path.

**Not done, deliberately:** no redesign, no new views, no colour-system
change. The palette discipline (heat ramp for severity, teal reserved for
interaction, drama reserved for implicated nodes) is unchanged.

---

*Append new ADRs below. Number sequentially. Date every entry.*

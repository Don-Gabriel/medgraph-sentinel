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

> *Attestation outcome (append at the Jul 29 sync):* ______

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

---

*Append new ADRs below. Number sequentially. Date every entry.*

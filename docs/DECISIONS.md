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

---

*Append new ADRs below. Number sequentially. Date every entry.*

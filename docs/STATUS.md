# STATUS — snapshot, not a log

**Updated:** 2026-07-30 (re-plan + M1 session, J Don Gabriel) · **Days to
Day 1 (Aug 12): 13**

## Current milestone: ✅ M1 PASSED (Jul 30) → M2 opens Jul 31

M1 exit test, all green on this machine (floor profile 2G/1G):
- `docker compose up -d` from clean → **all services healthy in 48 s**
- `RETURN gds.version()` → **2.13.11** (OQ #2 closed, ADR-026)
- Seed: loader 15.3 s, **all 31 counts match manifest** (51,144 nodes /
  193,694 rels); detection runner no-op OK
- `/api/v1/health` → `ok`, neo4j true, narration-cache match true
- Browser console renders live stats (after a CORS fix found by this test)
- GDS on the real graph: Louvain 2.4 s · PageRank 0.23 s · exact
  betweenness 122.5 s · projections 14–16 MiB · no OOM (OQ #11 closed)

## Standing context (changed 2026-07-30 — read ADR-024)

- **One shared laptop; J Don Gabriel implements nearly everything.**
  Capacity ~110–130 h total. MILESTONES fully rewritten; anchored dates
  hold (freezes Aug 6/8, rehearsal Aug 10).
- **Typologies 4 and 6 descoped** (cut ladder executed). We ship 1, 2, 3, 5.
  `narrative_fingerprint` ships but is consumed by no shipping rule.
- Non-code deliverables reassigned (DEFENCE_AREAS): Pavithra held-out +
  demo + screenshots · Vijayalakshmi PITCH + GLOSSARY · Mary DEMO_RUNBOOK +
  cold-start execution · Poonkundran DAY2_PLAYBOOK + fresh-clone
  verification. Everyone commits under their own identity (CONTRIBUTING
  "Shared-machine identity").

## DONE (this session)

- Re-plan docs committed (ADR-024): MILESTONES, DEFENCE_AREAS,
  CONTRIBUTING, DETECTION_SPEC descopes + propagation
- Seed-42 dataset committed (ADR-005): 51,144 nodes / 193,694 rels, 7.6 MB
- Loader per INTERFACES §4: LOAD CSV in batched transactions, wipe-and-load,
  manifest validation with loud diff (ADR-025 benchmark: LOAD CSV 15.3 s vs
  admin-import 3.8 s — LOAD CSV chosen; OQ #1 closed)
- `medgraph-neo4j:demo` image with GDS 2.13.11 baked at build time
  (ADR-026 — NEO4J_PLUGINS downloads at every container start; unusable
  offline). DEMO_RUNBOOK tarball commands updated
- API CORS middleware (console origin :5173 → API :8000)
- Docker Desktop fix on the lead machine: `EnableDockerAI` off in
  settings-store.json — the bundled Model Runner crashes the backend on
  this machine (apostrophe in the Windows profile path breaks its unix
  socket). If Docker won't start, check that flag first

## BLOCKED

- **OQ #12 attestation (Pavithra)** — still unrecorded under ADR-016;
  blocks scenario-overlay tooling design and the PITCH claim branch

## NEXT 3 (priority order — MILESTONES Jul 31)

1. Scenario overlay schema (INTERFACES §3) + planted-cell support in the
   generator — must exist before the Aug 6 freeze (Jul 31, ~8 h)
2. API alert endpoints against fixture alerts (Aug 1)
3. Console alert queue + Cytoscape drill-down on fixtures (Aug 2; M2 exit)

## Decisions awaiting a human

- OQ #12: Pavithra's attestation — record under ADR-016 at the next sync
- Four GitHub handles in README.md
- OQ #7: adopt minimal CI? (team decision; costs ~1 h of the new budget)

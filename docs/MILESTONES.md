# Milestones — 15 Days

Capacity model (owner [ASSUMED], Q1): 5 people × ~5–6 h weekdays, ~10 h
weekend days → roughly **470 person-hours** total. The schedule below fits
that with one deliberate buffer day. The two immovable dates are the
**detection freeze (Aug 6)** and the **integration freeze (Aug 8)** — every
overrun gets absorbed by cutting scope, never by moving a freeze.

| date | day | target |
|---|---|---|
| Jul 28 Tue | ✅ | Planning docs written, repo initialized, first commit |
| Jul 29–30 Wed–Thu | **M1: walking skeleton** | Docker Desktop installed on all 5 machines (blocker — ADR-002); repo scaffold (module dirs, lint, `.env` flow); `docker-compose.yml` with pinned Neo4j 5.26 + GDS 2.13; `graph/schema.cypher` applied; generator emits a *tiny* valid dataset (2 node types); loader loads it; FastAPI `/health`; Vite app renders stats. **Exit test: fresh clone → compose up → browser shows node counts.** |
| Jul 31–Aug 2 Fri–Sun | **M2: honest economy** | Generator v1 full honest economy (~50k nodes, all distributions); loader full CSV set + manifest validation; alert endpoints serving fixture data; console alert queue + drill-down against fixtures; scenario overlay schema implemented (needed *before* freeze). **Exit test: real dataset loads, console browses fixtures.** |
| Aug 3–5 Mon–Wed | **M3: detection end-to-end** | Emergent + planted fraud layers in generator; all six rules v1 writing real Alerts; subgraph + narration-fallback endpoints live; console on real data; thresholds calibrated on honest economy (OQ #4, #5 resolved). **Exit test: compose up → real alerts → drill-down → template narration.** |
| Aug 6 Thu | **DETECTION FREEZE** | DETECTION_SPEC.md + rule queries frozen in a dedicated commit; ADR appended with the date. Pavithra's abstention window opens: she authors held-out scenarios off-repo (hash → HELDOUT_COMMITMENT.md) and works frontend/demo only. Others: bug fixes, evidence-panel polish. |
| Aug 7 Fri | polish | Narration cache built and committed (OQ #8); statuses/notes; stats header; README screenshots; PITCH.md v2 with real click path. |
| Aug 8 Sat | **INTEGRATION FREEZE (evening)** | Main is demo-grade. After tonight: bug fixes and docs only — no features, no schema changes, no new rules. Full compose test from fresh clone on two machines. |
| Aug 9 Sun | **held-out evaluation** | Regenerate with Pavithra's overlays, run frozen rules **once**, record precision/recall (incl. misses) in DECISIONS + PITCH; commit scenario files; build the results slide. Remaining hours: bug fixes. |
| Aug 10 Mon | **dress rehearsal** | Full offline run of DEMO_RUNBOOK on the actual demo laptop (wifi off, projector if available): timed pitch + demo + failure drills. Output: ranked fix list. Day-2 drill rehearsal #1 (one of the three playbook drills, timed). |
| Aug 11 Tue | **final prep** | Fix list burn-down (demo blockers only); pitch rehearsal ×3 timed with Q&A practice (DEFENCE_AREAS roulette: random questions to the named answerer); USB fallbacks prepared (repo bundle + `docker save` images); **repo goes public in the evening**; Day-2 drill rehearsal #2. |
| Aug 12 Wed | **Day 1** | Arrive with laptop pre-booted (compose already up). 10-minute pitch per PITCH.md. |
| Aug 13 Thu | **Day 2** | Surprise-constraint sprint per DAY2_PLAYBOOK.md. |

## What this schedule cannot absorb (flagged per Q1)

- **A second full weekend commitment miss.** The two weekends carry ~200 of
  the 470 hours. If either weekend collapses, cut typologies 4 and 6 (keep
  1, 2, 3, 5) rather than slipping the freezes — four solid typologies beat
  six shaky ones.
- **Docker/WSL2 install problems past Jul 30.** That's why it's the very
  first task on every machine, not a when-needed task.
- **Generator realism rabbit-holes.** The honest economy gets tuned until
  M2's exit test, then it's good enough; realism polish after Aug 2 only if
  detection is ahead of schedule.
- **Late contract churn.** INTERFACES.md changes after Aug 5 need a genuinely
  blocking reason (the change protocol's announce-first rule is the brake).

## Standing cadence

Daily 15-minute sync (evening): what landed, what's claimed next (per
CONTRIBUTING.md claim protocol), any contract-change announcements, blockers.
Keep it to 15 minutes; anything longer becomes a pair session.

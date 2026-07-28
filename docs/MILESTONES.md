# Milestones — 14 Days

Re-planned 2026-07-29 (ADR-017): the planning phase consumed Jul 28 and spilled
into Jul 29, so the build window is **Jul 29 (partial) – Aug 11 = 14 days**.
Capacity (owner [ASSUMED], Q1): 5 people × ~5–6 h weekdays (10 remaining),
~10 h weekend days (4) → **~445–475 person-hours**. The original plan's slack
day is spent; this schedule has **zero buffer**.

Anchored to the calendar and immovable: pitch **Aug 12**, live sprint
**Aug 13**, detection freeze **Aug 6**, integration freeze **Aug 8**, dress
rehearsal **Aug 10**. Overruns are absorbed by cutting scope in the
pre-agreed order (bottom of this file) — never by moving a freeze or
shrinking a rehearsal.

| date | day | target |
|---|---|---|
| Jul 28 Tue | ✅ | Planning docs, repo initialized, first commit |
| Jul 29 Wed | **M1 opens (half-day)** | Docs corrections committed (this commit); OQ #12 attestation at the evening sync; **Docker Desktop install starts on all 5 machines** (the M1 gate — ADR-002); repo scaffold begun (module dirs, lint config, `.env` flow) |
| Jul 30 Thu | **M1: walking skeleton** | `docker-compose.yml` with pinned Neo4j 5.26 + GDS 2.13; `graph/schema.cypher` applied; generator emits a *tiny* valid dataset (2 node types); loader loads it; FastAPI `/health`; Vite app renders stats. **Exit test: fresh clone → compose up → browser shows node counts.** M1 was 2 days, now ~1.5 — if it slips, it may borrow Jul 31 morning and nothing else |
| Jul 31–Aug 2 Fri–Sun | **M2: honest economy** | Generator v1 full honest economy (~50k nodes, all distributions); loader full CSV set + manifest validation; alert endpoints serving fixture data; console alert queue + drill-down against fixtures; scenario overlay schema implemented (needed *before* the freeze). **Exit test: real dataset loads, console browses fixtures.** This window gains the weekend and absorbs any M1 slip |
| Aug 3–5 Mon–Wed | **M3: detection end-to-end** | Emergent + planted fraud layers; all six rules v1 writing real Alerts (cut order below if behind); subgraph + narration-fallback endpoints; console on real data; thresholds calibrated on the honest economy (OQ #4, #5 resolved). **Exit test: compose up → real alerts → drill-down → template narration.** |
| Aug 6 Thu | **DETECTION FREEZE** | Spec + rule queries frozen in a dedicated commit; ADR appended. Red-team scenario-authoring window opens (off-repo, hash → HELDOUT_COMMITMENT). Others: bug fixes, evidence-panel polish |
| Aug 7 Fri | polish | **Demo build chain executed in order (ADR-018): freeze dataset → load → detect → build narration cache → commit.** Statuses/notes; stats header; README screenshots; PITCH v2 with real click path |
| Aug 8 Sat | **INTEGRATION FREEZE (evening)** | Main is demo-grade. After tonight: bug fixes and docs only. Full compose test from fresh clone on two machines; any post-freeze fix that touches data/detection re-runs the ADR-018 chain from the top |
| Aug 9 Sun | **held-out evaluation** | Regenerate with red-team overlays, run frozen rules **once**, record precision/recall (incl. misses) in DECISIONS + PITCH; commit scenario files; build the results slide; resolve PITCH claim branch (delete the inapplicable one). Remaining hours: bug fixes |
| Aug 10 Mon | **dress rehearsal** | Full offline run of DEMO_RUNBOOK on the actual demo laptop, **including the cold-start acceptance test (ADR-019): network adapter disabled, images from the USB tarball, cached narrations verified.** Timed pitch + failure drills. Output: ranked fix list. Day-2 drill rehearsal #1 |
| Aug 11 Tue | **final prep** | Fix-list burn-down (demo blockers only); pitch rehearsal ×3 timed with DEFENCE_AREAS question roulette; both USB sticks finalized per the runbook manifest; **repo public in the evening**; Day-2 drill rehearsal #2 |
| Aug 12 Wed | **Day 1** | Laptop pre-booted (compose already up). 10-minute pitch per PITCH.md |
| Aug 13 Thu | **Day 2** | Surprise-constraint sprint per DAY2_PLAYBOOK.md |

## Does 14 days still fit?

**Yes — with zero slack.** The lost time (~25–30 person-hours) comes out of
the walking-skeleton window, which parallelizes worst anyway (scaffold tasks
serialize behind Docker installs); M2's weekend is the shock absorber. But
any *second* loss — a weekend miss, a Docker install that fights past
Jul 30, a generator rabbit-hole — triggers the cut list immediately rather
than compressing a freeze.

## Pre-agreed cut order (ADR-017 — cut scope, never dates)

1. **Typology 4, template cloning** — first out. It carries the only real
   algorithmic risk (fingerprint tuning, OQ #3) and needs the most
   calibration time; five solid typologies beat six with one shaky.
2. **Typology 6, circular payment** — second out. Contained Cypher work, but
   less demo-critical than 1–3 (algorithmic differentiators) and 5 (cheap,
   vivid, single query).
3. **Console conveniences** — stats header detail, filter combinations —
   before anything demo-path-critical.
4. Never cut: freezes, the dress rehearsal, the cold-start test, the
   held-out evaluation, narration fallback, typologies 1–3 and 5.

## What this schedule cannot absorb (updated)

- **Either weekend collapsing.** The two weekends carry ~200 of ~460 hours.
  First weekend lost → cuts 1–2 fire during M3. Second weekend lost → the
  evaluation still runs (it's small) but polish and the results slide get
  minimal versions.
- **Docker/WSL2 problems past Jul 30** — hence installs start today.
- **Generator realism rabbit-holes** — tuned until M2's exit test, then it's
  good enough.
- **Late contract churn** — INTERFACES changes after Aug 5 need a genuinely
  blocking reason.

## Standing cadence

Daily 15-minute sync (evening): what landed, tomorrow's claims
(CONTRIBUTING claim protocol), contract-change announcements, blockers.
Tonight's sync additionally records the OQ #12 attestation in DECISIONS.md.

# Milestones — 13 Days, One Implementer

Re-planned **2026-07-30 (ADR-024)**: all five members now share **one
laptop**, with J Don Gabriel driving nearly all implementation. Capacity is
**~110–130 total hours** (Don ~85–95 h of build time; the other four ~30–40 h
combined of docs, rehearsal, and verification work in scheduled laptop
slots) — not the ~475 person-hours the previous plan assumed. The ADR-017
cut ladder has been **executed, not held in reserve**: typologies 4
(template cloning) and 6 (circular payment) are descoped (see
DETECTION_SPEC header); we ship typologies **1, 2, 3, 5**.

Anchored to the calendar and immovable: pitch **Aug 12**, live sprint
**Aug 13**, detection freeze **Aug 6**, integration freeze **Aug 8**, dress
rehearsal **Aug 10**. Overruns are absorbed by the cut ladder at the bottom
of this file — never by moving a freeze or shrinking a rehearsal.

## One-laptop working model

- Don implements on the laptop most of each day.
- Each non-code contributor gets a **daily 30–60 min laptop slot** (evening,
  around the sync) to write and commit **their own work under their own git
  identity** — see CONTRIBUTING "Shared-machine identity". Git history must
  show five people doing real work, because it does.
- Rehearsal, question drilling, and scenario authoring (Pavithra, off-repo)
  happen away from the laptop and cost no build hours.

## Schedule

| date | day | target |
|---|---|---|
| Jul 30 Thu | **M1: walking skeleton** | Loader per INTERFACES §4 (wipe-and-load, manifest validation); OQ #1 benchmark decided by measurement; seed-42 dataset committed (ADR-005); **M1 exit test end-to-end: fresh compose up → `gds.version()` 2.13.x (closes OQ #2) → seed → `/health` → browser counts → Louvain/PageRank/betweenness run on the real graph** (~7 h Don) |
| Jul 31 Fri | **M2 opens** | Scenario overlay schema (INTERFACES §3) + planted-cell support in the generator — must exist **before** the freeze or the held-out protocol dies (~8 h Don). Slots: Vijayalakshmi starts PITCH v2 rework; Poonkundran reads loader/schema for defence |
| Aug 1 Sat | M2 | API alert endpoints against fixture alerts: list/detail/subgraph/narration-fallback/PATCH/entities (~10 h Don). Slot: Mary drafts DEMO_RUNBOOK updates |
| Aug 2 Sun | **M2 exit** | Console: alert queue + Cytoscape drill-down + evidence panel + status/note controls, on fixtures (~10 h Don). **Exit test: real dataset loads; console browses fixture alerts end-to-end.** Slot: Poonkundran drafts DAY2_PLAYBOOK updates |
| Aug 3 Mon | **M3 opens** | Fraud layers: planted cells for typologies 1/2/3/5 + device-recycling volume calibration (ADR-022 watch item); regenerate dev dataset (~9 h Don). Slot: Vijayalakshmi GLOSSARY pass |
| Aug 4 Tue | M3 | Rules v1: **typology 2 (credential laundering)** + **typology 5 (impossible travel)** incl. the travel-time table (OQ #5) (~9 h Don) |
| Aug 5 Wed | M3 | Rules v1: **typology 1 (ghost clinic + Louvain context)** + **typology 3 (kickback ring + GDS centrality)**; calibration on the honest economy begins (OQ #4) (~10 h Don) |
| Aug 6 Thu | **DETECTION FREEZE** | Calibration finished; thresholds documented per rule; spec + queries frozen in a dedicated commit + ADR. **Exit test: compose up → real alerts for all four typologies → drill-down → template narration.** Red-team window opens: Pavithra authors held-out scenarios off-repo (hash → HELDOUT_COMMITMENT) (~8 h Don) |
| Aug 7 Fri | demo build | **ADR-018 chain, in order: freeze dataset → load → detect → build narration cache → commit as one unit.** Statuses/notes polish; stats header (~8 h Don). Slots: Vijayalakshmi PITCH v2 with real click path; Mary RUNBOOK against the real demo |
| Aug 8 Sat | **INTEGRATION FREEZE (evening)** | Main is demo-grade. **Poonkundran executes the fresh-clone verification** (clone → .env → compose up → console, on this laptop from a clean Docker state) and commits the result to the RUNBOOK. After tonight: bug fixes and docs only (~8 h Don) |
| Aug 9 Sun | **held-out evaluation** | Regenerate with Pavithra's overlays into a separate data dir, run frozen rules **once**, record precision/recall incl. misses (DECISIONS + PITCH); commit scenario files; results slide; resolve the PITCH claim branch. **Aloud-rehearsal round 1 (evening): each member explains their defence area to the room, out loud, no notes — Don answers gaps, docs get fixed where answers failed** (~6 h Don + all, off-laptop) |
| Aug 10 Mon | **dress rehearsal** | Full offline DEMO_RUNBOOK on the demo laptop — **Mary executes the cold-start test (ADR-019: adapter off, images from USB tarball, cached narrations)**. Pavithra drives the demo and exports the screenshot deck. Timed pitch + failure drills; ranked fix list. **Aloud-rehearsal round 2.** Day-2 drill #1 (Poonkundran runs the playbook) |
| Aug 11 Tue | **final prep** | Fix-list burn-down (demo blockers only); pitch ×3 timed with DEFENCE_AREAS **question roulette** (any question to any person); both USB sticks finalized; **repo public in the evening**; Day-2 drill #2 |
| Aug 12 Wed | **Day 1** | Laptop pre-booted (compose already up). 10-minute pitch per PITCH.md |
| Aug 13 Thu | **Day 2** | Surprise-constraint sprint per DAY2_PLAYBOOK.md |

## Does it fit?

**Yes, at the top of the range — and with zero slack.** The schedule above
sums to ~90 h for Don and ~35 h for the other four ≈ **125 h**, inside
110–130 only because typologies 4 and 6 are already out and M3 packs four
rules into three days. Honest risks: the two 10-hour days (Aug 2, Aug 5) and
the Aug 6 calibration finishing on freeze day itself. **Any slip triggers
the next cut immediately** — never a moved freeze, never a shortened
rehearsal.

## Cut ladder (ADR-017 executed steps 1–2; ADR-024)

1. ~~Typology 4, template cloning~~ — **CUT 2026-07-30** (highest algorithmic
   risk, most calibration time).
2. ~~Typology 6, circular payment~~ — **CUT 2026-07-30** (bounded work, least
   demo-critical).
3. **Console conveniences** — filter combinations, stats-header detail. First
   to go if M2/M3 slips (~3–4 h back).
4. **Subgraph `hops=2`** — ship fixed `hops=1`; skip the 2-hop expansion +
   trim logic (~2–3 h back). *Contract change: needs the INTERFACES §6
   protocol (`contract:` PR).*
5. **Opportunistic live-narration path** — ship committed cache + template
   fallback only (~2 h back). The demo never needed the live path.
6. **Typology 3 centrality enrichment** — ship mutual concentration + shared
   infrastructure + Louvain; drop the PageRank/betweenness percentile term
   (~3–4 h back). Last resort: it weakens the algorithmic-differentiator
   story, so it goes only if the alternative is missing the freeze.

Never cut: freezes, dress rehearsal, cold-start test, held-out evaluation,
narration fallback, typologies 1–3 and 5, the aloud rehearsals.

## What this schedule cannot absorb

- **The laptop dying.** It is now a single point of failure for five
  people's hackathon. Mitigation: push to GitHub at every stop-point (at
  minimum end of each session), and the Aug 8 USB git-bundle also serves as
  a workable checkout.
- **Either weekend collapsing** — Aug 1–2 carries the whole API+console
  build; Aug 8–9 carries the freeze and the evaluation.
- **A second capacity loss** (illness, laptop contention, generator
  rabbit-hole) — fires cut 3 immediately, then 4–6 in order.
- **Late contract churn** — INTERFACES changes after Aug 5 need a genuinely
  blocking reason.

## Standing cadence

Daily 15-minute evening sync at the laptop: what landed, tomorrow's plan,
blockers — then the non-code laptop slots in sequence. Aloud-rehearsal
rounds Aug 9 and Aug 10 evenings, question roulette Aug 11 (see
DEFENCE_AREAS "Defending code you did not write").

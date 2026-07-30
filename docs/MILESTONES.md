# Milestones — 13 Days, One Person, ~95–110 Hours

Re-planned **2026-07-30 (ADR-027)**: J Don Gabriel builds, documents,
pitches, and runs Day 2 **alone**. No other contributor exists. The
~25–30 h of non-code deliverables previously assigned to four other people
(pitch, glossary, runbook execution, screenshots, fresh-clone verification,
Day-2 rehearsal) are **scheduled below as real hours**, not assumed
background work.

Anchored and immovable: detection freeze **Aug 6**, integration freeze
**Aug 8**, dress rehearsal **Aug 10**, pitch **Aug 12**, sprint **Aug 13**.
Overruns are absorbed by the cut ladder — never by moving a freeze,
shrinking the rehearsal, or assuming 14-hour days.

## Does it fit? — the honest answer first

**Yes, at ~93–100 scheduled hours — but only because of three things,
and with zero slack:**

1. Typologies 4 and 6 are already cut (ADR-024) — the ladder's first two
   rungs are spent.
2. The detection layer, centrality decision, and alert-precompute pipeline
   land **Jul 30** (AI-assisted build session), days ahead of the old M3
   window. If that work had landed on the old Aug 4–6 dates, this plan
   would NOT fit one person and cuts 3–6 would fire today.
3. Rehearsal and demo-prep hours are protected as scheduled work below.
   They are the pitch; they cannot be "found later."

Average load: **7–8 h/day** with two 9-hour days (Aug 1, Aug 2 — the
API+console block). That is sustainable for two weeks; 14-hour days are
not planned and not assumed anywhere. **One lost day (illness, laptop,
rabbit hole) fires cut 3 immediately; two lost days fire cuts 4–6.**

## Schedule (hours are budgets, not aspirations)

| date | day | target |
|---|---|---|
| Jul 30 Thu | **solo re-plan + detection architecture** (~9 h) | Team scaffolding stripped from all docs; **held-out scenarios authored + hash-committed BEFORE any detection query** (ADR-027 — done in this order deliberately); centrality decision measured + ADR-028; alert-precompute pipeline (ADR-029); detection rules v1 for typologies 1/2/3/5, calibrated on the honest economy, dev-set evaluation recorded. Explain-aloud review pass over everything landed. |
| Jul 31 Fri | **generator: overlays + planted cells** (~8 h) | Scenario overlay support per INTERFACES §3 (incl. the 2026-07-30 extensions) — **must exist before Aug 9 or the held-out evaluation dies**; planted cells for typologies 1/2; typology-5 recycling volume calibration (ADR-022 watch item); travel-time table finalized (OQ #5); regenerate dev dataset; re-run detection + eval, record deltas. |
| Aug 1 Sat | **API** (~9 h) | All INTERFACES §6 endpoints against real alerts: health (incl. narration-cache check), stats, list/detail/subgraph (cap + trim), narration (cache→fallback), PATCH, entities. Tests per endpoint. |
| Aug 2 Sun | **console — M2 exit** (~9 h) | Alert queue (filters) + Cytoscape drill-down + evidence panel + status/note controls. **Exit test: real dataset, real alerts, browse end-to-end.** |
| Aug 3 Mon | **console polish + narration builder** (~8 h) | Stats header; styling by type/role; narration builder + deterministic template fallback per typology; score normalization documented per rule (OQ #4). |
| Aug 4 Tue | **calibration + pitch v2** (~8 h: 5.5 code + 2.5 docs) | Honest-economy FP-rate review per rule; verify each documented FP mode actually appears and scores below `medium`; **PITCH v2 with the real click path (2 h); GLOSSARY pass (0.5 h)**. |
| Aug 5 Wed | **buffer + chain dry-run** (~8 h: incl. 1 h runbook) | Finish anything bleeding; dry-run the full ADR-018 chain on dev data (rehearses Aug 7); **DEMO_RUNBOOK update pass (1 h)**. If this buffer is consumed by earlier slippage, cut 3 has already fired. |
| Aug 6 Thu | **DETECTION FREEZE** (~7 h) | Calibration finished; thresholds documented per rule YAML; spec + queries frozen in a dedicated commit + ADR. **Exit test: compose up → real alerts for all four typologies → drill-down → template narration.** After tonight: no detection-query changes. |
| Aug 7 Fri | **demo build — ADR-018 chain** (~8 h: incl. 1 h screenshots) | In order, as one unit: freeze dataset → load → detect → **export alert CSVs (ADR-029)** → build narration cache (needs `ANTHROPIC_API_KEY`; if unavailable, fallback templates are the shipped mode — decide today, don't burn tomorrow) → commit together. **First screenshot batch (1 h).** |
| Aug 8 Sat | **INTEGRATION FREEZE (evening)** (~7 h: 4 code + 3 verification) | Main is demo-grade by evening. **Fresh-clone verification, executed personally from a clean Docker state, results committed to the RUNBOOK (2 h). USB tarball + git bundle built (1 h).** After tonight: bug fixes and docs only. |
| Aug 9 Sun | **HELD-OUT EVALUATION + rehearsal 1** (~7 h: 4 eval + 3 rehearsal) | Regenerate with the five overlays into a separate data dir; run frozen rules **once**; record precision/recall **including misses** (DECISIONS + PITCH + results slide); commit scenario files to `data/scenarios/heldout/`. **Evening: rehearsal round 1 — every DEFENCE_AREAS question answered aloud, recorded, stumbles fixed same evening (2–3 h).** |
| Aug 10 Mon | **DRESS REHEARSAL** (~7 h, mostly non-code) | Full offline DEMO_RUNBOOK on the demo laptop: **cold-start test executed personally (ADR-019: adapter off, images from USB, cached narrations, all ten steps)**; screenshot deck exported; full demo screen-recorded; timed pitch ×1 + failure drills; **Day-2 drill #1 (Shape A, timed)**; rehearsal round 2 on stumble cards. |
| Aug 11 Tue | **final prep** (~6 h, non-code) | Fix-list burn-down (demo blockers only); pitch ×3 timed; **question roulette (90 s/answer, full DEFENCE_AREAS pass)**; both USB sticks finalized per RUNBOOK manifest; **repo public in the evening**; **Day-2 drill #2 (Shape C, timed) — first thing cut if the day runs hot**. |
| Aug 12 Wed | **Day 1** | Laptop pre-booted (compose already up, click path warmed). 10-minute pitch per PITCH.md. |
| Aug 13 Thu | **Day 2** | Surprise-constraint sprint per DAY2_PLAYBOOK.md (solo protocol). |

Total: **~93 h scheduled** (≈ 69 h build/code + ≈ 24 h pitch/demo/rehearsal
work), inside the 95–110 h envelope with ~10 h of implicit contingency
spread across the buffers. There is no second buffer behind Aug 5.

## Cut ladder (extended for solo — fire in order, immediately, no debate)

1. ~~Typology 4, template cloning~~ — **CUT 2026-07-30** (ADR-024).
2. ~~Typology 6, circular payment~~ — **CUT 2026-07-30** (ADR-024).
3. **Console conveniences** — filter combinations, stats-header detail
   (~3–4 h back).
4. **Subgraph `hops=2`** — ship fixed `hops=1` (~2–3 h back; `contract:`
   PR per INTERFACES §6).
5. **Opportunistic live-narration path** — committed cache + template only
   (~2 h back).
6. **Typology 3 centrality enrichment** — ship concentration + shared
   infrastructure + Louvain; drop the centrality percentile term (~3–4 h
   back). Weakens the algorithm story; only if the alternative is missing
   the freeze.
7. **Day-2 drill #2** — keep drill #1 (~2 h back).
8. **Screenshot deck scope** — shrink to the seven click-path beats only
   (~1 h back).

Never cut: the freezes, the dress rehearsal + cold-start test, the
held-out evaluation, the narration fallback, typologies 1/2/3/5, at least
one full aloud rehearsal, and at least one Day-2 drill.

## What this schedule cannot absorb

- **The laptop dying.** Sole machine, sole person. Push to GitHub at every
  stop-point; the Aug 8 USB bundle is a workable checkout from any machine.
- **An illness day.** Fires cut 3 the same day, cuts 4–6 the second day.
- **The Aug 1–2 weekend collapsing** — it carries the whole API + console
  build, solo. Nothing else fits there.
- **A narration-cache rabbit hole on Aug 7** — the committed fallback
  templates are an acceptable shipped mode; decide by end of Aug 7, never
  spend Aug 8 on it.
- **Late contract churn** — INTERFACES changes after Aug 5 need a genuinely
  blocking reason.

## Standing cadence (solo)

End of every working session: STATUS.md updated in the final commit, work
pushed. End of every day: tomorrow's first task written down (decision
fatigue is the solo failure mode — never boot the laptop without knowing
the first hour's work). Rehearsals are calendar events, not intentions:
Aug 9 evening, Aug 10 evening, Aug 11.

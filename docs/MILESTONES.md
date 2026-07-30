# Milestones — Build Done, Rehearsal Remaining (re-planned 2026-07-30, third pass)

Timeline compressed by owner direction: everything movable was pulled out
of the calendar and into Jul 30. As of tonight the following are DONE and
merged: detection (4 typologies, calibrated, ADR-030), frozen dataset +
committed alerts (ADR-031), pre-generated narration cache with green
health (ADR-032), full API (§6), the console with its projector-legibility
fix pass, **the held-out one-shot under pre-registration (ADR-034 — leg
recall 5/8, misses explained in PITCH)**, screenshot deck + demo
recording, judge-facing README, turnkey Day-2 drill cards, offline bundle
staged (476 MB tar + bundle at `C:\WorkSpace\Private\medgraph-demo-usb\`).

## What code work genuinely remains — the honest answer

**Almost none.** Exactly three things, none of them features:

1. Whatever the **cold-start discovery run (Aug 4–5)** finds — the last
   unknown in the project. Budget: unknown until it runs; historically
   this class of test finds path/env issues worth hours, not days.
2. Whatever **rehearsal breaks** — a wrong number in a doc, a console
   nit that reads badly aloud. Bug-fix scale.
3. The **freezes themselves** (Aug 6, Aug 8) — each a dedicated commit +
   one-paragraph ADR stating nothing changed since Jul 30, which is the
   point.

No new scope will be invented to fill the days. Everything else below is
rehearsal, drills, and the physical steps only the owner can do.

## Schedule (fixed dates unchanged: freezes Aug 6/8, dress Aug 10, Day 1 Aug 12)

| date | focus (h) | content |
|---|---|---|
| Jul 31 Thu | rehearsal 1 (~5) | Timed pitch ×2 against the real console with the ADR-034 numbers; first full aloud pass of the DEFENCE_AREAS bank (record, listen back, fix stumble docs). **Fresh-clone verification pulled forward** (clone → .env → compose up → 81 alerts; ~30 min, record in RUNBOOK). |
| Aug 1 Fri | drill A (~5) | DAY2 DRILL A executed cold, timed against the 90-min target; result + timing into the drill card. Pitch ×1. |
| Aug 2 Sat | drill B + C (~5) | DRILL B (60 min) and DRILL C (90 min — capture the ×10 numbers table for the jury). Question-bank pass 2 on stumble cards. |
| Aug 3 Sun | contingency (~4) | Deliberately unscheduled. If nothing is broken: rest + pitch ×1. Do not invent scope. |
| Aug 4–5 Mon–Tue | **COLD START (owner-physical)** (~4) | docs/COLD_START.md end-to-end: USB copy, airplane mode, restore, boot, verify 81 alerts + pre-generated narrations, timing recorded. Fix list (if any) burns down Aug 5. |
| Aug 6 Wed | **DETECTION FREEZE** (~3) | Formality commit + ADR: no detection change since Jul 30 — say so. Pitch ×2 timed. |
| Aug 7 Thu | USB final (~4) | Both USB sticks written and verified item-by-item per RUNBOOK manifest (deck + recording now ride inside the repo). Question roulette round 1. |
| Aug 8 Fri | **INTEGRATION FREEZE** (~3) | Formality commit + ADR. After tonight: docs and demo-blocker fixes only. Pitch ×2. |
| Aug 9 Sat | mock day (~5) | Full dress-rehearsal dry run at home: boot sequence, 10-min pitch to a timer, roulette round 2, failure drills (deck switch under 30 s). *(The held-out evaluation formerly here ran Jul 30 under pre-registration — ADR-034.)* |
| Aug 10 Sun | **DRESS REHEARSAL** (~4) | Cold-start CONFIRMATION run on this machine; timed pitch ×2; remaining fix list must be empty of demo blockers tonight. |
| Aug 11 Mon | final (~3) | Pitch ×3; **repo public in the evening**; sticks re-verified; early night. |
| Aug 12 Tue | **Day 1** | Boot sequence per RUNBOOK; pitch. |
| Aug 13 Wed | **Day 2** | Constraint sprint per DAY2_PLAYBOOK drill discipline. |

Roughly **45 scheduled hours**, ~80% rehearsal/drills/verification. The
build phase is over; from here the deliverable is delivery.

## Cut ladder (what's left of it)

Nothing meaningful remains to cut — the ladder's remaining rungs
(console conveniences, hops=2, drill #2, deck scope) are all shipped and
cheap to keep. If a day collapses, the cut is a rehearsal repetition,
never a freeze, never a cold-start run.

## What this schedule cannot absorb

- **The machine dying** (ADR-033: no backup laptop, owner-owned risk).
  Mitigation unchanged: everything pushed; USB bundle restores anywhere
  Docker runs; deck + recording deliver the pitch with zero live software.
- **Unfreezing the dataset** — full ADR-018 chain re-run including
  re-narration (ADR-031/032). Demo-blocker emergencies only.

## Standing cadence

End of session: STATUS + push. Every rehearsal is a calendar event with a
timer, not an intention. The question bank (DEFENCE_AREAS) is the syllabus.

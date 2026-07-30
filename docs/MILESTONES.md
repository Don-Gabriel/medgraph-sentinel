# Milestones — Solo, Rehearsal-Weighted (re-planned 2026-07-30 evening)

Second re-plan of 2026-07-30: the detection layer landed **seven days ahead
of the old M3 dates** (ADR-028/029/030), buying ~5 days. Owner decision:
that slack goes to **the console and rehearsal, not more detection
features**. Agreed without reservation — the jury sees the console and the
delivery; a fifth typology would be invisible next to either. The one
addition to the owner's framing already incorporated below: the cold-start
test moves forward a full five days (Aug 4–5), because it is the single
riskiest unknown left and slack only helps if the discovery happens early.

Anchored and immovable: detection freeze **Aug 6**, integration freeze
**Aug 8**, dress rehearsal **Aug 10**, Day 1 **Aug 12**, Day 2 **Aug 13**.

## Order of work (owner-directed, 2026-07-30)

1. Generator: finish (overlays, planted cells, impossible-travel cases) →
   re-evaluate all four typologies → **dataset FROZEN**.
2. API alert endpoints per INTERFACES §6 (300-node subgraph cap).
3. **The console — the highest-priority remaining item.** Treated as the
   deliverable, not the wrapper.
4. Narration build (needs `ANTHROPIC_API_KEY` — owner input; template
   fallback ships either way).
5. **Early cold-start rehearsal** (Aug 4–5, not Aug 10).
6. Everything after that is rehearsal, drills, and polish.

## Schedule

| date | day | target |
|---|---|---|
| Jul 30 Thu (evening) | **generator freeze + API** | Overlay support per INTERFACES §3; planted cells (typologies 1/2); tight-window impossible recycled identities (fixes the 0-of-5 finding); full regen + re-evaluation, real numbers per typology; **dataset declared FROZEN** (unfreeze cost documented in STATUS); alert CSVs exported + committed (ADR-029). API endpoints per §6 with tests. |
| Jul 31 Fri | **console day 1** (~8 h) | Design pass first (frontend-design skill — the console must read as designed, not default-bootstrap); alert queue: risk-sorted, severity colour-coded, typology/status filters, counts at a glance; app shell + data layer against the live API. |
| Aug 1 Sat | **console day 2 — the hero view** (~8 h) | Cytoscape subgraph drill-down: implicated nodes visually distinct, force-directed layout, hover detail, click-to-expand one hop, never the full graph; evidence panel (rule, triggering features, specific values from summary_params). |
| Aug 2 Sun | **console day 3 + M2 exit** (~8 h) | Status/note controls wired to PATCH; polish; **visual verification at 1440/768 px minimum**; screenshot batch 1; CI decision (OQ #7). **Exit test: queue → drill-down → evidence → status change, on the frozen dataset, end-to-end.** |
| Aug 3 Mon | **contingency + pitch v3** (~6 h) | *(Narration landed Jul 30 — ADR-032 pre-generated cache, zero API calls; this slot converts to what the owner directed: rehearsal and contingency, not scope.)* Fix anything bleeding; PITCH v3 against the real console; first full pass of the DEFENCE_AREAS question bank aloud. |
| Aug 4 Tue | **EARLY COLD-START — discovery run** (~5 h, mostly owner-physical) | Bundle + COLD_START.md already prepared Jul 30. Owner runs the physical sequence: copy to USB → **network adapter disabled** → restore → clean compose up → 81 alerts with pre-generated narrations. Report exactly what failed. |
| Aug 5 Wed | **fix + drill** (~7 h) | Cold-start fix list burn-down; **Day-2 drill #1** (Shape A: Accreditor end-to-end, timed, target 90 min); PITCH v3 against the real console click path. |
| Aug 6 Thu | **DETECTION FREEZE** (~6 h) | Dedicated freeze commit + ADR (a formality — no detection change since Jul 30, and that is the point; say so in the ADR). Timed pitch ×2. Rehearsal cards from stumbles. |
| Aug 7 Fri | **demo assets** (~6 h) | Screenshot deck (all click-path beats) + full demo screen recording; USB sticks v1 per RUNBOOK manifest; **Day-2 drill #2** (Shape C: ×10 scale run, timed, numbers recorded). |
| Aug 8 Sat | **INTEGRATION FREEZE (evening)** (~6 h) | Fresh-clone verification from clean Docker state, result committed to RUNBOOK; USB sticks final; git bundle. **Aloud rehearsal round 1** (every DEFENCE_AREAS question, recorded, stumbles fixed same evening). After tonight: bug fixes and docs only. |
| Aug 9 Sun | **HELD-OUT EVALUATION** (~6 h) | The one-shot: regenerate with the five sealed overlays into a separate data dir, run frozen rules ONCE, commit precision/recall including misses (DECISIONS + PITCH + slide); commit scenario files. **Aloud rehearsal round 2.** |
| Aug 10 Mon | **DRESS REHEARSAL — confirmation, not discovery** (~6 h) | Cold-start re-run on the demo laptop from USB (should confirm Aug 4's result); timed pitch ×2 with failure drills; remaining fix list must be empty of demo blockers by tonight. |
| Aug 11 Tue | **final prep** (~5 h) | Question roulette (90 s/answer, full pass); pitch ×3 timed; **repo public in the evening**; both USBs re-verified item-by-item; early night. |
| Aug 12 Wed | **Day 1** | Laptop pre-booted, compose up, click path warmed. 10-minute pitch. |
| Aug 13 Thu | **Day 2** | Surprise-constraint sprint per DAY2_PLAYBOOK (solo protocol). |

Total scheduled: **~85 h** at 5–8 h/day — genuinely lighter than the
previous plan because the build back-half became rehearsal. Roughly 40% of
remaining hours are rehearsal/drill/demo-prep, which is the point: the
build is ahead; the delivery is not, yet.

## Cut ladder (unchanged rungs that still exist)

1–2. ~~Typologies 4/6~~ — cut (ADR-024). 3. Console conveniences (~3–4 h).
4. Subgraph hops=2 (~2–3 h, `contract:`). 5. Live-narration path (~2 h).
6. ~~Typology 3 centrality~~ — retired on evidence (ADR-028).
7. Day-2 drill #2 (~2 h). 8. Screenshot-deck scope (~1 h).

Never cut: freezes, both cold-start runs, held-out evaluation, narration
fallback, typologies 1/2/3/5, aloud rehearsals, at least one Day-2 drill.

## What this schedule cannot absorb

- **The laptop dying** — push at every stop-point; USB bundle from Aug 7.
- **Unfreezing the dataset after Aug 3** — the full chain re-runs
  (regenerate → load → detect → export → narration cache rebuild → recommit
  as one unit) and eats a rehearsal day. After Aug 8 it is a demo-blocker
  emergency, nothing less.
- ~~An API key arriving late~~ — moot (ADR-032): narration is committed
  pre-generated data; there is no key and nothing to wait for.

## Standing cadence (solo)

End of session: STATUS + push. End of day: tomorrow's first task written
down. Rehearsals are calendar events: Aug 8, 9, 10, 11.

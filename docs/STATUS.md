# STATUS — snapshot, not a log

**Updated:** 2026-08-03, consistency sweep · **Days to Day 1 (Aug 12): 9**

---

# ⛔ CODE IS FROZEN (2026-07-30)

**The build is done. From this moment, changes are permitted for exactly
three reasons:**

1. **Cold-start findings** — whatever the Aug 4–5 offline drill breaks.
2. **Rehearsal breakage** — something that reads wrong or fails when said
   aloud, or a demo-path defect found while practising.
3. **Factual corrections** — a wrong number or stale claim in a doc.

**Everything else is out of scope, including "just polishing".** No new
features, no refactors, no visual tweaks, no extra typologies, no
"while I'm in here". If you find yourself editing code for any reason not
on that list of three, stop — the remaining risk in this project is
delivery, not software.

Unfreezing the dataset is a separate, harder rule (ADR-031/032): any
regeneration re-runs the whole ADR-018 chain including re-narration, and
after Aug 8 it is a demo-blocker emergency only.

---

## What exists (all merged to main, all verified running)

| layer | state |
|---|---|
| Generator | Frozen seed-42 economy + overlays + planted cells (ADR-031). Byte-identical on re-run. |
| Graph | Neo4j 5.26 + GDS 2.13.11, our own image with GDS baked in (ADR-026). Seeds in ~21 s. |
| Detection | 4 typologies, config-driven registry, calibrated on the honest economy only (ADR-030); centrality benchmarked out (ADR-028). |
| Alerts | **81**, precomputed and committed as CSV data — no clone ever runs detection (ADR-029). |
| Narration | **81/81 pre-generated and committed**, zero API calls ever (ADR-032). `/health` guards completeness by alert-id set. |
| API | Full INTERFACES §6 surface, 300-node subgraph cap. |
| Console | Queue + Cytoscape evidence view + case file + disposition; projector-legibility pass done (ADR-035). |
| Demo backup | `screenshot-deck/` (7 beats, 1920×1080) + `demo-recording.webm` (53.7 s, 5.9 MB), both committed. |
| Offline bundle | Staged at `C:\WorkSpace\Private\medgraph-demo-usb\`; drill script `docs/COLD_START.md`. |
| Tests | **70 passing.** |

## Evaluation results (final — do not restate from memory, read them)

- **Honest economy:** zero medium-or-high alerts on every rule.
- **Dev set:** planted cells 3/3 (ghost) and 3/3 (credential), all `high`;
  impossible-travel groups 3/3 `high`; kickback precision 1.0, broker
  recall 6/13.
- **Held-out (one shot, pre-registered):** 5 scenarios · 8 legs expected ·
  **5 detected · 3 missed · 2 root causes**; all 5 scenarios raised at
  least one alert. Identical numbers in PITCH.md, README.md and
  HELDOUT_COMMITMENT.md — change one, change all three.

## What remains — rehearsal, not building

1. **Rehearsal.** The pitch has never been said out loud. This is now the
   single largest risk in the project. Kit is ready: PITCH.md is a runnable
   script with cumulative timestamps, a self-scoring rubric, 15 ranked
   questions, and 60-second / 3-minute versions.
2. **Cold start (Aug 4–5, owner-physical).** docs/COLD_START.md, phases
   1–6. Only the USB walk and the network adapter are human steps.
3. **Day-2 drills.** Three turnkey cards in DAY2_PLAYBOOK.md.
4. **Two freeze-formality commits** (Aug 6 detection, Aug 8 integration),
   each recording that nothing changed — which is the point.
5. **Repo public**, Aug 11 evening.

## Decisions awaiting a human

- **OQ #7 — CI (ruff + pytest + frontend build):** resolve-by Aug 2 has
  passed with no workflow adopted and no decision recorded. Owner yes/no
  needed before the repo goes public Aug 11; the OQ's own bar was
  "runtime < 5 min and setup < 1 h".
